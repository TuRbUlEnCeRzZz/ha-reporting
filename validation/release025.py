"""Reproduce 0.2.5 editorial checks against 256f055, without live services.

    python validation/release025.py /tmp/ha-reporting-025

Reference inputs are rounded PDF excerpts/synthetic records, not raw HA history.
"""
import copy
import io
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/ha-reporting-025')
OUT.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'ha-reporting/app')]
from test_release024 import reference
from test_ai_complement025 import sample

notes=sample()
notes['catalogs'][0]['devices'][1]['device']['category']='refrigeration'
samples = {'excerpt': reference(), 'relation': sample(), 'notes':notes}
large = copy.deepcopy(samples['excerpt'])
for n in range(5):
    for device in copy.deepcopy(samples['excerpt']['catalogs'][0]['devices'][1:]):
        device['device']['id'] += str(n)
        device['device']['name'] += str(n)
        for source in device['sources']:
            source['entity_id'] += str(n)
        large['catalogs'][0]['devices'].append(device)
    for device in copy.deepcopy(samples['excerpt']['comparisons']['targets'][0]['catalogs'][0]['devices'][1:]):
        device['id'] += str(n)
        device['name'] += str(n)
        for source in device['sources']:
            source['entity_id'] += str(n)
        large['comparisons']['targets'][0]['catalogs'][0]['devices'].append(device)
samples['expanded'] = large
for name, result in samples.items():
    (OUT/f'{name}.json').write_text(json.dumps(result), encoding='utf-8')
archive = subprocess.check_output(['git','archive','256f055','ha-reporting/app'], cwd=ROOT)
baseline = OUT/'baseline'
baseline.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    tar.extractall(baseline, filter='data')
worker = '''
import json,sys,time,statistics
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from analysis.ai_report import _fact_ledger_context_v11,build_budgeted_ai_context
from analysis.insights import report_digest,mobile_summary
from rendering.html_report import render_report_html
result=json.loads(Path(sys.argv[2]).read_text())
measurements={}
for label,call in [('context',lambda:build_budgeted_ai_context(result)),('html',lambda:render_report_html(result))]:
    batches=[]
    for repeat in range(5):
        start=time.perf_counter()
        for n in range(10):call()
        batches.append((time.perf_counter()-start)/10)
    measurements[label+'_median_s']=statistics.median(batches)
measurements['context_characters']=len(build_budgeted_ai_context(result)[0])
print(json.dumps({'ledger':_fact_ledger_context_v11(result),'digest':report_digest(result),
                 'notification':mobile_summary(result),'measurements':measurements}))
'''
metrics = {}
for version, app in [('before',baseline/'ha-reporting/app'),('after',ROOT/'ha-reporting/app')]:
    metrics[version]={}
    for name in samples:
        output=subprocess.check_output([sys.executable,'-c',worker,str(app),str(OUT/f'{name}.json')],text=True,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        metrics[version][name]=json.loads(output)
for name in samples:
    for key in ('ledger','digest','notification'):
        assert metrics['before'][name][key]==metrics['after'][name][key], (name,key)
    for version in metrics:
        metrics[version][name]=metrics[version][name]['measurements']

from analysis.ai_report import build_budgeted_ai_context,_validate_selection,_complementary_lines,_fallback_selection
from rendering.html_report import render_report_html
from analysis.insights import mobile_summary
from weasyprint import HTML
pdf_metrics={}
for name, result in [('excerpt',samples['excerpt']),('expanded',samples['expanded']),('useful',samples['relation']),('notes',samples['notes']),('no-ai',samples['excerpt'])]:
    result=copy.deepcopy(result)
    context=json.loads(build_budgeted_ai_context(result)[0])
    ids=[c['i'] for c in context['interpretation_candidates']]
    selection,valid=_validate_selection({'interpretations':ids}, context)
    result['ai_analysis']={'enabled':name != 'no-ai','status':'completed','entity_id':'ai_task.simulated',
        'selection':selection,'selection_fallback':not valid}
    for theme in (('dark','light') if name=='excerpt' else ('dark',)):
        html=render_report_html(result,theme)
        (OUT/f'{name}-{theme}.html').write_text(html,encoding='utf-8')
        start=time.perf_counter()
        document=HTML(string=html).render()
        for page in document.pages:
            for box in page._page_box.descendants():
                if getattr(box,'text',None):
                    assert box.position_x >= 0
                    assert box.position_x+box.width <= page.width+1,(name,box.text)
        document.write_pdf(OUT/f'{name}-{theme}.pdf')
        pdf_metrics[f'{name}-{theme}']={'seconds':time.perf_counter()-start,'pages':len(document.pages)}
    (OUT/f'{name}-notification.txt').write_text(mobile_summary(result),encoding='utf-8')
    (OUT/f'{name}-interpretation.txt').write_text('\n'.join(_complementary_lines(context,selection,'fr')),encoding='utf-8')
(OUT/'metrics.json').write_text(json.dumps({'before_after':metrics,'pdf':pdf_metrics},indent=2),encoding='utf-8')
print(json.dumps({'deterministic_outputs_equal':True,'before_after':metrics,'pdf':pdf_metrics},indent=2))
