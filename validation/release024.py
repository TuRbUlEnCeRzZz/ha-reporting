"""Compare local presentation cost and render synthetic relevance fixtures.

Run with the project's Python dependencies and Node-independent tests available:
    python validation/insight_relevance.py /tmp/ha-reporting-relevance
Inputs use rounded PDF excerpts with synthetic surrounding records, not raw history. Existing non-derived ledger values are compared exactly against v0.2.3.
"""
import copy, json, os, shutil, statistics, subprocess, sys, time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/ha-reporting-relevance'); out.mkdir(parents=True, exist_ok=True)
sys.path[:0]=[str(root/'tests'),str(root/'ha-reporting/app')]
from test_release024 import reference as weekly_example
sample=weekly_example()
(out/'weekly-synthetic.json').write_text(json.dumps(sample))
large=copy.deepcopy(sample)
for n in range(10):
    for catalog in large['catalogs']:
        for device in copy.deepcopy(sample['catalogs'][0]['devices'][1:]):
            device['device']['id']+=str(n); device['device']['name']+=str(n)
            for source in device['sources']:
                source['entity_id']+=str(n)
            catalog['devices'].append(device)
    for target in large['comparisons']['targets']:
        for device in copy.deepcopy(sample['comparisons']['targets'][0]['catalogs'][0]['devices'][1:]):
            device['id']+=str(n); device['name']+=str(n)
            for source in device['sources']:
                source['entity_id']+=str(n)
            target['catalogs'][0]['devices'].append(device)
(out/'large-synthetic.json').write_text(json.dumps(large))
baseline=out/'baseline-app'
if not baseline.exists():
    shutil.copytree(root/'ha-reporting/app', baseline, ignore=shutil.ignore_patterns('__pycache__'))
for name in ['analysis/ai_report.py','analysis/insights.py','rendering/html_report.py']:
    (baseline/name).write_bytes(subprocess.check_output(['git','show','c5ff5a3:ha-reporting/app/'+name],cwd=root))
worker='''import json, sys, time, statistics
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from analysis.ai_report import build_budgeted_ai_context, _fact_ledger_context_v11
from analysis.insights import mobile_summary
from rendering.html_report import render_report_html
sample=json.loads(Path(sys.argv[2]).read_text())
times=[]
for repeat in range(5):
 start=time.perf_counter()
 for n in range(20):
  build_budgeted_ai_context(sample); mobile_summary(sample); render_report_html(sample)
 times.append((time.perf_counter()-start)/20)
context=build_budgeted_ai_context(sample)[0]
facts=[{k:v for k,v in f.items() if k in {'q','s','c','k','v','b','r','d','p'}} for f in _fact_ledger_context_v11(sample)['facts'] if f['k'] not in {'energy_per_cycle','runtime_per_cycle','energy_per_runtime'}]
print(json.dumps({'median_seconds':statistics.median(times),'context_characters':len(context),'facts':facts}))
'''
metrics={}
for name,path in [('before',baseline),('after',root/'ha-reporting/app')]:
    metrics[name]={}
    for fixture in ['weekly','large']:
        result=subprocess.check_output([sys.executable,'-c',worker,str(path),str(out/(fixture+'-synthetic.json'))],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','XDG_CACHE_HOME':os.environ.get('XDG_CACHE_HOME', str(out/'cache'))},text=True)
        metrics[name][fixture]=json.loads(result)
for fixture in ['weekly','large']:
    assert metrics['before'][fixture]['facts']==metrics['after'][fixture]['facts'],fixture
    for name in metrics: metrics[name][fixture].pop('facts')
(out/'metrics.json').write_text(json.dumps(metrics,indent=2)); print(json.dumps(metrics,indent=2))
from analysis.insights import mobile_summary,report_digest
from analysis.ai_report import _fact_ledger_context_v11,_fallback_selection,_render_selection_analysis
from rendering.html_report import render_report_html
from weasyprint import HTML
context=_fact_ledger_context_v11(sample)
sample['ai_analysis']={'enabled':True,'status':'completed','text':_render_selection_analysis(context,_fallback_selection(context),'fr')}
(out/'notification.txt').write_text(mobile_summary(sample))
(out/'digest.json').write_text(json.dumps(report_digest(sample),ensure_ascii=False,indent=2))
for theme in ['dark','light']:
    html=render_report_html(sample,theme)
    (out/(theme+'.html')).write_text(html)
    document=HTML(string=html).render()
    for page in document.pages:
        for box in page._page_box.descendants():
            if getattr(box,'text',None):
                assert box.position_x>=0
                assert box.position_x+box.width<=page.width+1,(theme,box.text)
    document.write_pdf(out/(theme+'.pdf'))
    print(theme,len(document.pages),'pages; text fits page widths')
print(mobile_summary(sample))
