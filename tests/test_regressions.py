import copy
import io
import json
import math
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ha-reporting' / 'app'))
from reporting_stats.engine import MetricStatisticsEngine
from analysis.device import DeviceAnalysisEngine
from providers.base import ProviderCapabilities, ProviderStatus, ProviderError
from providers.victoriametrics import VictoriaMetricsProvider as VM
from periods.engine import PeriodEngine
from comparisons.engine import ComparisonEngine
from rendering.html_report import render_report_html
from analysis.ai_report import compact_report_context, _extract_service_response, analyze_report_with_ai
import main

SOURCE = {'entity_id': 'sensor.runtime', 'metric': 'runtime', 'unit': 'h'}

def rollup(**changes):
    values = dict(count=3, first=0., last=1., first_ts=1000., last_ts=4600.,
                  resets=0., decreases=0., increase=1., descent=0., min=0., present_duration=3600.)
    values.update(changes)
    return {'values': values}

class FakeProvider:
    capabilities = ProviderCapabilities(report_rollup=True, raw_series=True)
    def __init__(self, values=None, points=None):
        self.rollup = values or rollup(resets=1, decreases=1, increase=2, count=3 if points is None else max(1,len(points)))
        self.points = [(1000., 0.), (2800., .5), (4600., 1.)] if points is None else points
        self.raw_calls = []
    def health_check(self):
        return ProviderStatus('victoria_metrics', True, True, 'OK')
    def get_report_statistics(self, source, *args, **kwargs):
        return copy.deepcopy(rollup() if source['entity_id']=='sensor.healthy' else self.rollup)
    def get_raw_series(self, source, start, end):
        self.raw_calls.append((source['entity_id'], start, end))
        return self.points
    def get_series(self, *args):
        raise AssertionError('Sampled query must not validate a suspect runtime')

def analyze_device(provider, sensors=None):
    return DeviceAnalysisEngine(lambda _: provider).analyze(
        catalog_id='c', catalog_name='C', device_id='d',
        device={'sensors': sensors or {'runtime': SOURCE}}, default_provider='victoria_metrics',
        start=0, end=365*86400, step=300, retrieval_mode='provider_rollup')

class RuntimeTests(unittest.TestCase):
    def setUp(self): self.engine = MetricStatisticsEngine()
    def stats(self, pts, end=100000):
        return self.engine.analyze('runtime', pts, 0, end, 300, 'h')
    def test_strict_half_open_sort_dedup_and_finite(self):
        a = self.engine.analyze('power', [(600,99),(300,2),(0,1),(300,3),(-1,10),(5,float('nan'))],0,600,300,'W')
        self.assertEqual(a['quality']['received_points'],2)
        self.assertEqual(a['statistics']['mean'],2)
        self.assertEqual(a['quality']['expected_points'],2)
    def test_month_has_8928_positions(self):
        self.assertEqual(self.engine.analyze('power',[],0,31*86400,300)['quality']['expected_points'],8928)
    def test_monotonic_runtime(self):
        self.assertAlmostEqual(self.stats([(0,0),(3600,1),(7200,2)])['statistics']['delta'],2)
    def test_real_reset_survives(self):
        a=self.stats([(0,10),(3600,11),(3660,0),(7260,1)])
        self.assertEqual(a['statistics']['resets_detected'],1)
        self.assertEqual(a['statistics']['delta'],2)
    def test_tiny_reset_is_not_forgiven_as_rounding(self):
        a=self.stats([(0,.0004),(1,0),(3601,1)])
        self.assertEqual(a['statistics']['resets_detected'],1)
        self.assertEqual(a['statistics']['transition_diagnostics']['rounding_compatible_transitions'],0)
        self.assertEqual(a['statistics']['transition_diagnostics']['reset_candidate_transitions'],1)
        self.assertFalse(a['statistics']['transition_diagnostics']['benign_corrections_only'])
    def test_rounding_is_diagnostic_not_new_tolerance(self):
        a=self.stats([(0,1),(3600,1.169444444444),(3608,1.169),(7200,2)])
        self.assertEqual(a['statistics']['transition_diagnostics']['rounding_compatible_transitions'],1)
        self.assertEqual(a['statistics']['anomalies_ignored'],1)
        self.assertEqual(a['statistics']['resets_detected'],0)
        self.assertAlmostEqual(a['statistics']['delta'],1)
    def test_61_seconds_is_not_rounding(self):
        a=self.stats([(0,8),(3600,8.359),(3679,8.342),(7200,9)])
        self.assertEqual(a['statistics']['transition_diagnostics']['rounding_compatible_transitions'],0)
        self.assertEqual(a['statistics']['transition_diagnostics']['minor_correction_transitions'],1)
        self.assertTrue(a['statistics']['transition_diagnostics']['benign_corrections_only'])
        self.assertEqual(a['statistics']['anomalies_ignored'],1)
    def test_impossible_increment_is_rejected(self):
        a=self.stats([(0,0),(1,100),(3600,1)])
        self.assertEqual(a['statistics']['delta'],1)
        self.assertEqual(a['statistics']['anomalies_ignored'],1)
    def test_negative_values_invalid(self):
        self.assertEqual(self.stats([(0,-1),(3600,0)])['status'],'invalid')
    def test_observed_limit_not_year(self):
        a=self.engine.analyze_rollup('runtime',rollup(last=500, increase=500),0,365*86400,300,'h')
        self.assertFalse(a['statistics']['plausible'])
        self.assertEqual(a['status'],'invalid')
        self.assertEqual(a['statistics']['physical_limit_hours'],1)
    def test_detailed_limit_is_observed(self):
        a=self.stats([(100,0),(3700,1)])
        self.assertEqual(a['statistics']['physical_limit_hours'],1)
    def test_event_density_both_modes(self):
        for metric in ['runtime','cycles','energy_total','temperature']:
            with self.subTest(metric=metric):
                for a in [self.engine.analyze(metric,[(0,0),(300,1)],0,600,300),self.engine.analyze_rollup(metric,rollup(),0,5000,300)]:
                    self.assertIsNone(a['quality']['sample_density_percent'])
                    self.assertFalse(a['quality']['density_applicable'])
    def test_power_density_retained(self):
        a=self.engine.analyze_rollup('power',rollup(),0,5000,300)
        self.assertGreater(a['quality']['sample_density_percent'],0)
    def test_energy_reconstruction_unchanged(self):
        a=self.engine.analyze('energy_total',[(0,10),(1,11),(2,0),(3,2)],0,4,1)
        self.assertEqual(a['statistics']['delta'],3)
        self.assertEqual(a['statistics']['mode'],'reconstructed')

class FallbackTests(unittest.TestCase):
    def test_targeted_only_and_diagnostic_preserved(self):
        p=FakeProvider()
        r=analyze_device(p, {'bad':SOURCE,'good':dict(SOURCE,entity_id='sensor.healthy')})
        self.assertEqual(len(p.raw_calls),1)
        self.assertEqual(p.raw_calls[0],('sensor.runtime',1000.,4600.001))
        self.assertEqual(r['summary']['sources_fallback'],1)
        self.assertEqual(r['summary']['sources_ok'],2)
        f=r['sources'][0]['fallback']
        self.assertEqual(f['rollup_statistics']['mode'],'provider_reconstructed')
        self.assertEqual(f['sampling'],'raw')
        self.assertEqual(r['sources'][0]['analysis']['statistics']['first']['value'],0)
    def test_healthy_no_export(self):
        p=FakeProvider(rollup()); r=analyze_device(p)
        self.assertEqual(p.raw_calls,[])
        self.assertEqual(r['summary']['sources_fallback'],0)
    def test_drop_without_provider_reset_still_verified(self):
        p=FakeProvider(rollup(decreases=1))
        self.assertEqual(analyze_device(p)['summary']['sources_fallback'],1)
    def test_verified_minor_correction_avoids_fallback(self):
        points=[(1000,0.0),(2000,1.0),(2100,0.983),(4600,1.5)]
        p=FakeProvider(rollup(last=1.5,resets=1,decreases=1,increase=1.517,descent=0.017,count=4),points)
        r=analyze_device(p)
        source=r['sources'][0]
        self.assertEqual(r['summary']['sources_fallback'],0)
        self.assertEqual(r['summary']['sources_runtime_verified'],1)
        self.assertEqual(source['retrieval_mode'],'provider_rollup')
        self.assertEqual(source['verification']['classification'],'minor_corrections')
        self.assertEqual(source['analysis']['statistics']['mode'],'direct_minor_corrections')
        self.assertAlmostEqual(source['analysis']['statistics']['delta'],1.5)
    def test_tiny_return_to_zero_still_falls_back(self):
        points=[(1000,0.0004),(1001,0.0),(4600,1.0)]
        p=FakeProvider(rollup(first=.0004,last=1.0,resets=1,decreases=1,increase=1.0,descent=.0004,count=3),points)
        r=analyze_device(p)
        source=r['sources'][0]
        self.assertEqual(r['summary']['sources_fallback'],1)
        self.assertEqual(source['retrieval_mode'],'series_fallback')
        self.assertEqual(source['fallback']['diagnostic']['reset_candidate_transitions'],1)
    def test_impossible_rollup_triggers_export(self):
        p=FakeProvider(rollup(last=500))
        self.assertEqual(analyze_device(p)['summary']['sources_fallback'],1)
    def test_empty_export_fails_closed(self):
        r=analyze_device(FakeProvider(points=[]))
        self.assertEqual(r['sources'][0]['status'],'error')
        self.assertEqual(r['sources'][0]['verification']['status'],'failed')
        self.assertIn('rollup_statistics',r['sources'][0]['verification'])
    def test_partial_export_fails_closed(self):
        r=analyze_device(FakeProvider(points=[(2800,.5),(4600,1)]))
        self.assertEqual(r['sources'][0]['status'],'error')
    def test_missing_interior_sample_fails_closed(self):
        p=FakeProvider(rollup(resets=1),[(1000,0),(4600,1)])
        self.assertEqual(analyze_device(p)['sources'][0]['status'],'error')

    def test_provider_without_raw_fails_closed(self):
        p=FakeProvider();p.capabilities=ProviderCapabilities(report_rollup=True)
        self.assertEqual(analyze_device(p)['sources'][0]['status'],'error')
    def test_negative_raw_invalid(self):
        p=FakeProvider(points=[(1000,-1),(4600,0)])
        self.assertEqual(analyze_device(p)['sources'][0]['status'],'invalid')
    def test_raw_real_reset_comparison_metadata(self):
        p=FakeProvider(points=[(1000,1),(2800,0),(4600,.5)])
        a=analyze_device(p)['sources'][0]
        self.assertEqual(a['analysis']['statistics']['mode'],'detailed_reconstructed')
        self.assertEqual(ComparisonEngine()._compare_source(a,a)['comparison_status'],'reconstructed')
    def test_source_failure_does_not_abort_other_source(self):
        p=FakeProvider(points=[])
        r=analyze_device(p, {'bad':SOURCE,'good':dict(SOURCE,entity_id='sensor.healthy')})
        self.assertEqual(r['summary']['sources_error'],1)
        self.assertEqual(r['summary']['sources_ok'],1)

class ProviderTests(unittest.TestCase):
    def row(self, points, **labels):
        return json.dumps({'metric':dict(__name__='h_value',**labels),'timestamps':[ts for ts,v in points],'values':[v for ts,v in points]}).encode()+b'\n'
    def test_jsonl_rows_sorted_dedup_halfopen(self):
        data=[self.row([(2000,2),(1000,1)]),self.row([(1000,1),(3000,3)])]
        self.assertEqual(VM._parse_raw_export(data,1000,3000),[(1.,1.),(2.,2.)])
    def test_conflicting_duplicate_rejected(self):
        with self.assertRaises(ProviderError): VM._parse_raw_export([self.row([(1000,1),(1000,2)])],0,3000)
    def test_multiple_label_sets_rejected(self):
        with self.assertRaises(ProviderError): VM._parse_raw_export([self.row([(1000,1)],job='a'),self.row([(2000,2)],job='b')],0,3000)
    def test_nonfinite_rejected(self):
        for value in [float('nan'),float('inf'),float('-inf')]:
            with self.subTest(value=value),self.assertRaises(ProviderError): VM._parse_raw_export([self.row([(1000,value)])],0,3000)
    def test_malformed_export_rejected(self):
        for data in [b'not json', b'{}', b'{"metric":{"__name__":"h_value"},"timestamps":[1],"values":[]}']:
            with self.subTest(data=data),self.assertRaises(ProviderError): VM._parse_raw_export([data],0,3000)
    def test_point_limit_fails_not_truncates(self):
        with patch.object(VM,'RAW_POINT_LIMIT',1),self.assertRaises(ProviderError):
            VM._parse_raw_export([self.row([(1000,1),(2000,2)])],0,3000)
    def test_transport_uses_export_and_exact_end(self):
        p=VM('http://example.invalid')
        with patch('urllib.request.urlopen',return_value=io.BytesIO(self.row([(1001,1),(2000,2)]))) as mock:
            pts=p.get_raw_series(SOURCE,1.0001,2)
        params=parse_qs(urlparse(mock.call_args.args[0].full_url).query)
        self.assertEqual(params['start'],['1.001']);self.assertEqual(params['end'],['1.999'])
        self.assertIn('/api/v1/export?',mock.call_args.args[0].full_url)
        self.assertEqual(pts,[(1.001,1.)])
    def test_line_limit(self):
        p=VM('http://example.invalid')
        with patch.object(p,'RAW_LINE_LIMIT',5),patch('urllib.request.urlopen',return_value=io.BytesIO(b'123456\n')),self.assertRaises(ProviderError):
            p.get_raw_series(SOURCE,1,2)
    def test_exact_fractional_rollup_window(self):
        p=VM('http://example.invalid')
        with patch.object(p,'instant_query',return_value={'data':{'result':[]}}) as mock:
            p.get_report_statistics(SOURCE,1000.0001,1001.692432)
        self.assertIn('[1692ms]',mock.call_args.args[0])
        self.assertEqual(mock.call_args.kwargs['evaluation_time'],'1001.692')
    def test_integer_period_no_end_sample(self):
        p=VM('http://example.invalid')
        with patch.object(p,'instant_query',return_value={'data':{'result':[]}}) as mock:
            p.get_report_statistics(SOURCE,1000,1001)
        self.assertIn('[1000ms]',mock.call_args.args[0])
        self.assertEqual(mock.call_args.kwargs['evaluation_time'],'1000.999')
    def test_submillisecond_empty_no_request(self):
        p=VM('http://example.invalid')
        with patch.object(p,'instant_query') as mock:
            self.assertEqual(p.get_report_statistics(SOURCE,1.0001,1.0002)['values'],{})
            mock.assert_not_called()
    def test_rollup_duplicate_rejected(self):
        row={'metric':{'hr_stat':'first'},'value':[0,'1']}
        with self.assertRaises(ProviderError): VM._parse_rollup_result({'data':{'result':[row,row]}})
    def test_rollup_nonfinite_rejected(self):
        with self.assertRaises(ProviderError): VM._parse_rollup_result({'data':{'result':[{'metric':{'hr_stat':'first'},'value':[0,'NaN']}]}})
    def test_query_has_descent_no_subquery_sampling(self):
        q=VM.report_rollup_expression(SOURCE,1000,5000)
        self.assertIn('descent_over_time(h_value{',q)
        self.assertNotIn(':300',q)
    def test_single_sample_without_increase_is_valid(self):
        p=VM('http://example.invalid')
        v=rollup(count=1,first_ts=1,last_ts=1,first=0,last=0)['values']
        del v['increase']
        payload={'data':{'result':[{'metric':{'hr_stat':k},'value':[1,value]} for k,value in v.items()]}}
        with patch.object(p,'instant_query',return_value=payload):
            r=p.get_report_statistics(SOURCE,1,1.001)
        self.assertEqual(MetricStatisticsEngine().analyze_rollup('runtime',r,1,1.001,300)['statistics']['delta'],0)
    def test_byte_limit(self):
        p=VM('http://example.invalid')
        with patch.object(p,'RAW_BYTE_LIMIT',5),patch('urllib.request.urlopen',return_value=io.BytesIO(b'  \n  \n')),self.assertRaises(ProviderError):
            p.get_raw_series(SOURCE,1,2)

    def test_incomplete_runtime_rollup_rejected(self):
        p=VM('http://example.invalid')
        with patch.object(p,'instant_query',return_value={'data':{'result':[{'metric':{'hr_stat':'count'},'value':[0,1]}]}}),self.assertRaises(ProviderError):
            p.get_report_statistics(SOURCE,0,100)

class PeriodComparisonTests(unittest.TestCase):
    def setUp(self): self.engine=PeriodEngine('Europe/Zurich')
    def test_dst_days(self):
        for date,hours in [('2026-03-29',23),('2026-10-25',25)]:
            start=datetime.fromisoformat(date)
            from datetime import timedelta
            end=start+timedelta(days=1)
            p=self.engine.resolve({'type':'custom','start':str(start),'end':str(end)})
            self.assertEqual(p.as_dict()['duration_seconds'],hours*3600)
    def test_custom_comparison_keeps_elapsed_duration(self):
        p=self.engine.resolve({'type':'custom','start':'2026-03-28T12:00','end':'2026-03-30T12:00'})
        for target in self.engine.comparison_targets(p,{'previous_periods':3}):
            self.assertEqual(target['resolved_period'].as_dict()['duration_seconds'],47*3600)
    def test_explicit_fall_fold_uses_elapsed_order(self):
        p=self.engine.resolve({'type':'custom','start':'2026-10-25T02:30:00+02:00','end':'2026-10-25T02:15:00+01:00'})
        self.assertEqual(p.as_dict()['duration_seconds'],45*60)
    def test_nonexistent_spring_local_time_rejected(self):
        with self.assertRaisesRegex(ValueError,'inexistante'):
            self.engine.resolve({'type':'custom','start':'2026-03-29T02:30','end':'2026-03-29T04:00'})

    def test_year_elapsed(self):
        p=self.engine.resolve({'type':'year','mode':'current'},datetime(2026,9,25,22,21,tzinfo=ZoneInfo('Europe/Zurich')))
        self.assertEqual(p.as_dict()['duration_seconds'],p.end.timestamp()-p.start.timestamp())
    def test_month_and_year_axes(self):
        p=self.engine.resolve({'type':'month','mode':'previous'},datetime(2026,9,25))
        t=self.engine.comparison_targets(p,{'previous_periods':1,'previous_years':1})
        self.assertEqual(t[0]['resolved_period'].start.month,7)
        self.assertEqual(t[1]['resolved_period'].start.year,2025)
    def test_leap_year_clamped(self):
        p=self.engine.resolve({'type':'custom','start':'2024-02-29','end':'2024-03-01'})
        t=self.engine.comparison_targets(p,{'previous_years':1})[0]['resolved_period']
        self.assertEqual(t.start.day,28)
    def source(self,metric='temperature',**stats):
        return {'status':'ok','metric':metric,'unit':'°C','analysis':{'quality':{'period_coverage_percent':100,'sample_density_percent':None},'statistics':dict(mean=25,**stats)}}
    def test_temperature_absolute_only(self):
        e=ComparisonEngine();a=self.source();b=self.source();b['analysis']['statistics']['mean']=20
        c=e._compare_source(a,b)
        self.assertEqual(c['values'][0]['absolute_change'],5)
        self.assertIsNone(c['values'][0]['relative_change_percent'])
    def test_unavailable_reference(self):
        self.assertEqual(ComparisonEngine()._compare_source(self.source(),None)['comparison_status'],'unavailable')
    def test_partial_coverage(self):
        s=self.source();s['analysis']['quality']['period_coverage_percent']=20
        self.assertEqual(ComparisonEngine()._compare_source(s,self.source())['comparison_status'],'partial')
    def test_zero_reference_no_percentage(self):
        a=self.source('runtime',delta=1);b=self.source('runtime',delta=0)
        self.assertIsNone(ComparisonEngine()._compare_source(a,b)['values'][0]['relative_change_percent'])
    def test_metric_aware_power_partial(self):
        a=self.source('power');a['analysis']['quality']['sample_density_percent']=10
        self.assertEqual(ComparisonEngine()._compare_source(a,a)['comparison_status'],'partial')

class ReportTests(unittest.TestCase):
    def test_report_aggregation_and_transfer_metadata(self):
        p=FakeProvider()
        catalog={'devices':{'d':{'sensors':{'runtime':SOURCE,'healthy':dict(SOURCE,entity_id='sensor.healthy')}}}}
        resolved=PeriodEngine('UTC').resolve({'type':'custom','start':'1970-01-01','end':'1971-01-01'})
        with patch.object(main,'resolve_provider',return_value=p),patch.object(main,'load_catalog',return_value=catalog):
            result=main._execute_report_period({'catalogs':['c']},resolved)
        self.assertTrue(result['execution']['raw_series_transferred'])
        self.assertEqual(result['summary']['sources_fallback'],1)
        self.assertEqual(result['summary']['sources_total'],2)
    def test_verified_runtime_counts_as_raw_transfer_without_fallback(self):
        points=[(1000,0.0),(2000,1.0),(2100,0.983),(4600,1.5)]
        p=FakeProvider(rollup(last=1.5,resets=1,decreases=1,increase=1.517,descent=0.017,count=4),points)
        catalog={'devices':{'d':{'sensors':{'runtime':SOURCE}}}}
        resolved=PeriodEngine('UTC').resolve({'type':'custom','start':'1970-01-01','end':'1971-01-01'})
        with patch.object(main,'resolve_provider',return_value=p),patch.object(main,'load_catalog',return_value=catalog):
            result=main._execute_report_period({'catalogs':['c']},resolved)
        self.assertTrue(result['execution']['raw_series_transferred'])
        self.assertEqual(result['summary']['sources_fallback'],0)
        self.assertEqual(result['summary']['sources_runtime_verified'],1)
    def test_real_snapshots(self):
        data=json.loads((ROOT/'tests/fixtures/runtime_snapshots.json').read_text())
        expected={'compressor_a':(20.152,2,1,1),'compressor_b':(58.792,1,0,1),'fan':(22.417,0,0,0)}
        for name,d in data.items():
            with self.subTest(name=name):
                p=FakeProvider(d['rollup'],d['points'])
                r=DeviceAnalysisEngine(lambda _:p).analyze(catalog_id='c',catalog_name='C',device_id='d',device={'sensors':{'x':SOURCE}},default_provider='victoria_metrics',start=1767222000,end=1790367701.692432,step=300,retrieval_mode='provider_rollup')['sources'][0]
                self.assertEqual(r['status'],'ok')
                self.assertAlmostEqual(r['analysis']['statistics']['delta'],expected[name][0])
                self.assertEqual(r['retrieval_mode'],'provider_rollup')
                self.assertNotIn('fallback',r)
                if name!='fan':
                    diag=r['verification']['diagnostic']
                    self.assertEqual(r['verification']['classification'],'minor_corrections')
                    self.assertTrue(diag['benign_corrections_only'])
                    self.assertEqual(diag['negative_transitions'],expected[name][1])
                    self.assertEqual(diag['rounding_compatible_transitions'],expected[name][2])
                    self.assertEqual(diag['minor_correction_transitions'],expected[name][3])
                    self.assertEqual(r['analysis']['statistics']['mode'],'direct_minor_corrections')
                else:
                    self.assertNotIn('verification',r)



class AiAnalysisTests(unittest.TestCase):
    def sample(self):
        return {
            'report': {'name':'Rapport test'},
            'resolved_period': {'label':'Septembre','timezone':'Europe/Zurich'},
            'summary': {'sources_total':1,'sources_ok':1},
            'catalogs': [{'name':'Maison','devices':[{'device':{'name':'Frigo','category':'refrigeration'},'sources':[{
                'sensor_key':'frigo_power','entity_id':'sensor.frigo_power','metric':'power','unit':'W','status':'ok',
                'preview':[{'timestamp':1,'value':999}],
                'analysis': {'quality': {'period_coverage_percent':100,'sample_density_percent':95,'density_applicable':True},
                             'statistics': {'max':{'value':120},'p95':80,'mean':50},
                             'validation': {'warnings': []}}
            }]}]}],
            'comparisons': {'enabled':False,'target_count':0,'targets':[]},
        }

    def test_compact_context_excludes_raw_preview(self):
        context=compact_report_context(self.sample())
        encoded=json.dumps(context)
        self.assertNotIn('preview',encoded)
        self.assertNotIn('999',encoded)
        self.assertEqual(context['catalogs'][0]['devices'][0]['sources'][0]['values']['mean'],50)

    def test_extract_service_response_direct(self):
        data,cid=_extract_service_response({'service_response':{'data':'ok','conversation_id':'c1'}})
        self.assertEqual(data,'ok')
        self.assertEqual(cid,'c1')

    def test_extract_service_response_namespaced(self):
        data,cid=_extract_service_response({'service_response':{'ai_task.local':{'data':'ok2','conversation_id':'c2'}}})
        self.assertEqual((data,cid),('ok2','c2'))

    def test_disabled_ai_does_not_need_token(self):
        result=analyze_report_with_ai(self.sample(),{'enabled':False},token='')
        self.assertEqual(result['status'],'disabled')
        self.assertFalse(result['enabled'])

    def test_ai_task_call_uses_return_response_and_entity(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*_): return False
            def read(self):
                return json.dumps({'service_response':{'data':'SYNTHÈSE\nTout va bien.','conversation_id':'abc'}}).encode()
        captured={}
        def fake_urlopen(request,timeout=None):
            captured['url']=request.full_url
            captured['body']=json.loads(request.data)
            captured['timeout']=timeout
            return Response()
        with patch('analysis.ai_report.urllib.request.urlopen',side_effect=fake_urlopen):
            result=analyze_report_with_ai(self.sample(),{'enabled':True,'entity_id':'ai_task.local'},token='token')
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['conversation_id'],'abc')
        self.assertIn('?return_response',captured['url'])
        self.assertEqual(captured['body']['entity_id'],'ai_task.local')
        self.assertIn('sans afficher de raisonnement interne',captured['body']['instructions'])


class HtmlRendererTests(unittest.TestCase):
    def sample_result(self):
        return {
            'report': {'name':'Rapport <Maison>'},
            'resolved_period': {'label':'Année en cours','timezone':'Europe/Zurich','semantics':'[start, end)'},
            'execution': {'analysis_mode':'provider_rollup','duration_seconds':0.25,'total_duration_seconds':0.5,'finished_at_epoch':1790371460},
            'summary': {'devices_total':1,'sources_total':2,'sources_ok':2,'sources_no_data':0,'sources_error':0,'sources_invalid':0,'sources_runtime_verified':1,'sources_fallback':0},
            'catalogs': [{'name':'Électroménager','devices':[{'device':{'name':'Vinothèque','category':'refrigeration'},'summary':{'sources_ok':2,'sources_total':2},'sources':[
                {'sensor_key':'power<script>','entity_id':'sensor.power','metric':'power','unit':'W','status':'ok','analysis':{'quality':{'period_coverage_percent':100,'density_applicable':True,'sample_density_percent':95},'statistics':{'max':{'value':100},'p95':70,'mean':40}}},
                {'sensor_key':'runtime','entity_id':'sensor.runtime','metric':'runtime','unit':'h','status':'ok','verification':{'classification':'minor_corrections'},'analysis':{'quality':{'period_coverage_percent':10,'density_applicable':False,'sample_density_percent':None},'statistics':{'delta':20.2,'last':{'value':20.2},'resets_detected':0}}}
            ]}]}],
            'comparisons': {'enabled':True,'targets':[{'label':'N-1 an','resolved_period':{'label':'2025'},'summary':{'sources_comparable':1,'sources_partial':0,'sources_reconstructed':0,'sources_unavailable':0},'catalogs':[{'name':'Électroménager','devices':[{'name':'Vinothèque','sources':[{'sensor_key':'power','metric':'power','unit':'W','comparison_status':'comparable','reasons':[],'values':[{'label':'Moyenne','base':40,'reference':50,'absolute_change':-10,'relative_change_percent':-20,'relative_change_applicable':True}]}]}]}]}]},
            'ai_analysis': {'enabled':True,'status':'completed','entity_id':'ai_task.local','duration_seconds':1.2,'text':'SYNTHÈSE\nTout va bien <script>.'}
        }
    def test_html_report_is_self_contained_printable_and_escaped(self):
        html=render_report_html(self.sample_result())
        self.assertTrue(html.startswith('<!doctype html>'))
        self.assertIn('Imprimer / enregistrer en PDF',html)
        self.assertIn('@media print',html)
        self.assertIn('print-color-adjust:exact',html)
        self.assertIn('--paper:#14191f',html)
        self.assertIn('background:var(--paper)!important',html)
        self.assertIn('break-inside:auto',html)
        self.assertNotIn('body{background:#fff',html)
        self.assertIn('Rapport &lt;Maison&gt;',html)
        self.assertIn('power&lt;script&gt;',html)
        self.assertNotIn('power<script>',html)
    def test_html_report_has_comparison_bars_and_runtime_verification(self):
        html=render_report_html(self.sample_result())
        self.assertIn('Comparaisons N / N-x',html)
        self.assertIn('compare-bars',html)
        self.assertIn('runtime vérifié',html)
        self.assertIn('20.2 h',html)

    def test_html_report_contains_escaped_ai_analysis(self):
        html=render_report_html(self.sample_result())
        self.assertIn('Analyse IA',html)
        self.assertIn('AI Task · no-thinking',html)
        self.assertIn('SYNTHÈSE<br>Tout va bien &lt;script&gt;.',html)
        self.assertNotIn('Tout va bien <script>.',html)


class PackageTests(unittest.TestCase):
    def test_yaml_and_installation_layout(self):
        import yaml
        addon=ROOT/'ha-reporting'
        for p in ROOT.rglob('*.yaml'):
            self.assertIsInstance(yaml.safe_load(p.read_text()),dict)
        config=yaml.safe_load((addon/'config.yaml').read_text())
        self.assertEqual(config['version'],'0.1.0-beta.3')
        self.assertIn('aarch64',config['arch'])
        self.assertTrue(config['ingress'])
        for name in ['Dockerfile','run.sh','app/main.py','app/app.js','app/index.html','app/rendering/html_report.py','app/analysis/ai_report.py']:
            self.assertTrue((addon/name).is_file(),name)
        index=(addon/'app/index.html').read_text()
        self.assertIn('reportHtmlButton', index)
        self.assertIn('Rapport HTML / PDF', index)
        self.assertIn('reportAiEnabled', index)
        self.assertIn('Think before responding', index)
    def test_healthy_report_no_raw_transfer(self):
        p=FakeProvider(rollup())
        resolved=PeriodEngine('UTC').resolve({'type':'custom','start':'1970-01-01','end':'1971-01-01'})
        with patch.object(main,'resolve_provider',return_value=p),patch.object(main,'load_catalog',return_value={'devices':{'d':{'sensors':{'x':SOURCE}}}}):
            r=main._execute_report_period({'catalogs':['c']},resolved)
        self.assertFalse(r['execution']['raw_series_transferred'])

if __name__ == '__main__': unittest.main()
