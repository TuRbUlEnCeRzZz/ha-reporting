"""Render synthetic before/after reports and record local resource observations."""
import sys, subprocess, importlib.util, json, time, resource
from pathlib import Path
repo = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(repo/'tests'), str(repo/'ha-reporting/app')]
from test_energy_insights import scenario
from analysis.insights import mobile_summary
from analysis.ai_report import _fact_ledger_context_v11, _fallback_selection, _render_selection_analysis, build_budgeted_ai_context
from rendering.html_report import render_report_html
from weasyprint import HTML
root = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/ha-energy-insights')
root.mkdir(parents=True, exist_ok=True)
result = scenario()
context = _fact_ledger_context_v11(result)
result['ai_analysis'] = {'enabled': True, 'status': 'completed', 'text': _render_selection_analysis(context, _fallback_selection(context), 'fr')}
(root/'notification.txt').write_text(mobile_summary(result))
(root/'analysis.txt').write_text(result['ai_analysis']['text'])
baseline = subprocess.check_output(['git', 'show', 'f2833f6054fb7dd21f6b5290ff3de13696a50def:ha-reporting/app/rendering/html_report.py'], text=True, cwd=repo)
(root/'baseline_renderer.py').write_text(baseline)
spec = importlib.util.spec_from_file_location('baseline_renderer', root/'baseline_renderer.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
metrics = {}
for name, render in [('before', module.render_report_html), ('after', render_report_html)]:
    start = time.perf_counter()
    cpu_start = time.process_time()
    html = render(result)
    (root/f'{name}.html').write_text(html)
    doc = HTML(string=html).render()
    doc.write_pdf(root/f'{name}.pdf')
    metrics[name] = {'seconds': round(time.perf_counter()-start, 3), 'pages': len(doc.pages), 'cpu_seconds': round(time.process_time()-cpu_start,3)}
# Stress the complete renderer, not just the digest.
for n in range(60):
    import copy
    other = copy.deepcopy(result['catalogs'][0]['devices'][1])
    other['device'] = {'id': f'd{n}', 'name': f'Appareil {n}'}
    for s in other['sources']:
        s['entity_id'] += str(n)
    result['catalogs'][0]['devices'].append(other)
start = time.perf_counter()
cpu_start = time.process_time()
doc = HTML(string=render_report_html(result)).render()
doc.write_pdf(root/'many-devices.pdf')
metrics['many_devices'] = {'seconds': round(time.perf_counter()-start,3), 'pages': len(doc.pages), 'cpu_seconds': round(time.process_time()-cpu_start,3)}
metrics['peak_rss_kib_process'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
metrics['notification_chars'] = len(mobile_summary(result))
metrics['context_chars'] = len(build_budgeted_ai_context(result)[0])
(root/'metrics.json').write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
