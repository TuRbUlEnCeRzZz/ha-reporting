"""Structured complementary interpretation; deterministic v0.2.4 facts stay authoritative."""
import copy
import json
import unittest
from unittest.mock import patch
from test_energy_insights import scenario
from analysis.insights import report_digest, mobile_summary
from analysis.ai_report import (_fact_ledger_context_v11, build_budgeted_ai_context,
    _interpretation_candidates, _validate_selection, _complementary_lines)
from rendering.html_report import render_report_html, _ai_analysis


def sample():
    result=scenario()
    runtime=result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][2]['values'][0]
    runtime.update(base=15,reference=14,absolute_change=1,relative_change_percent=(15/14-1)*100)
    stats=result['catalogs'][0]['devices'][1]['sources'][2]['analysis']['statistics']
    stats.update(delta=15,last={'value':15})
    return result


class ComplementTests(unittest.TestCase):
    def test_eligible_relation_uses_existing_same_period_facts(self):
        ctx=_fact_ledger_context_v11(sample())
        candidates=_interpretation_candidates(ctx)
        self.assertEqual(len(candidates),1)
        index={f['i']:f for f in ctx['facts']}
        self.assertEqual({index[f]['k'] for f in candidates[0]['evidence']},{'energy_per_cycle','runtime_per_cycle'})

    def test_real_complement_survives_shared_words_and_has_no_invented_values(self):
        result=sample(); ctx=_fact_ledger_context_v11(result)
        ctx['interpretation_candidates']=_interpretation_candidates(ctx)
        selection,_=_validate_selection({'summary':ctx['selection_policy']['priority_highlights'],
            'interpretations':['I1'],'text':'Washer 9999 kWh fault'},ctx)
        lines=_complementary_lines(ctx,selection,'fr')
        self.assertEqual(len(lines),1)
        self.assertIn('Lave-linge',lines[0])
        self.assertNotIn('9999',lines[0])
        self.assertIn('hypoth',lines[0])
        result['ai_analysis']={'enabled':True,'status':'completed','selection':selection}
        self.assertIn(lines[0],_ai_analysis(result))

    def test_generic_or_repetitive_legacy_output_is_trace_only(self):
        result=sample()
        result['ai_analysis']={'enabled':True,'status':'completed','text': 'Continuer à surveiller. 9999 kWh.', 'duration_seconds':71.1,'entity_id':'ai_task.local'}
        html=_ai_analysis(result)
        self.assertNotIn('9999',html)
        self.assertNotIn('ai-text',html)
        self.assertIn('ai_task.local',html)
        self.assertIn('71.1',html)
        self.assertIn('L’essentiel',render_report_html(result))

    def test_empty_unknown_or_fabricated_interpretation_is_not_displayed(self):
        ctx=_fact_ledger_context_v11(sample());ctx['interpretation_candidates']=_interpretation_candidates(ctx)
        for value in (None,[],['I999'],[{'kind':'fault','value':9999}],'I1'):
            selection,_=_validate_selection({'interpretations':value},ctx)
            self.assertEqual(_complementary_lines(ctx,selection,'fr'),[])

    def test_misaligned_or_missing_duration_has_no_candidate(self):
        ctx=_fact_ledger_context_v11(sample())
        duration=next(f for f in ctx['facts'] if f['k']=='runtime_per_cycle')
        duration['c']='other'
        self.assertEqual(_interpretation_candidates(ctx),[])

    def test_fallback_does_not_masquerade_as_model_interpretation(self):
        result=sample()
        result['ai_analysis']={'enabled':True,'status':'completed','selection':{'interpretations':['I1']},'selection_fallback':True}
        self.assertNotIn('ai-text',_ai_analysis(result))

    def test_context_modes_preserve_priorities_and_necessary_evidence(self):
        result=sample();original=copy.deepcopy(result)
        baseline=_fact_ledger_context_v11(result)
        digest=report_digest(result); message=mobile_summary(result)
        for mode in ('optimized','extended','complete','automatic'):
            ctx=json.loads(build_budgeted_ai_context(result,context_level=mode)[0])
            self.assertEqual(ctx['selection_policy']['priority_highlights'],baseline['selection_policy']['priority_highlights'])
            for candidate in ctx['interpretation_candidates']:
                self.assertTrue(set(candidate['evidence'])<={f['i'] for f in ctx['facts']})
        self.assertEqual(report_digest(result),digest)
        self.assertEqual(mobile_summary(result),message)
        self.assertEqual(result,original)

    def test_errors_keep_deterministic_content_without_technical_leaks(self):
        for status in ('error','timeout'):
            result=sample(); result['ai_analysis']={'enabled':True,'status':status,'error':'Traceback secret internal host'}
            html=render_report_html(result)
            self.assertIn('L’essentiel',html)
            self.assertNotIn('Traceback secret',html)

    def test_negligible_duration_does_not_create_a_causal_sounding_complement(self):
        result=sample()
        result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][2]['values'][0].update(base=10.001,absolute_change=-3.999,relative_change_percent=(10.001/14-1)*100)
        self.assertEqual(_interpretation_candidates(_fact_ledger_context_v11(result)),[])


class TransportComplementTests(unittest.TestCase):
    def run_response(self, data):
        from analysis.ai_report import analyze_report_with_ai
        class WS:
            def __init__(self):
                self.sent=[]
                self.messages=[{'type':'auth_required'},{'type':'auth_ok'},
                    {'id':1,'type':'result','success':True,'result':{'response':{'data':data}}}]
            def recv(self): return json.dumps(self.messages.pop(0))
            def send(self,raw): self.sent.append(json.loads(raw))
            def settimeout(self,value): pass
            def close(self): pass
        ws=WS()
        with patch('analysis.ai_report.websocket.create_connection',return_value=ws):
            output=analyze_report_with_ai(sample(),{'enabled':True,'entity_id':'ai_task.local'},token='test')
        self.assertEqual(sum(m.get('type')=='call_service' for m in ws.sent),1)
        return output

    def test_new_response_is_complementary_and_uses_one_service_call(self):
        output=self.run_response({'interpretations':['I1'],'summary':[], 'prose':'999 kWh fault'})
        self.assertEqual(output['interpretation_status'],'useful')
        self.assertFalse(output['selection_fallback'])
        self.assertNotIn('999',output['text'])
        self.assertNotIn('SYNTHÈSE',output['text'])
        self.assertIn('hypoth',output['text'])

    def test_empty_optional_response_is_valid_without_filler(self):
        output=self.run_response({'interpretations':[]})
        self.assertEqual(output['interpretation_status'],'no_added_value')
        self.assertFalse(output['selection_fallback'])
        self.assertEqual(output['text'],'')

    def test_old_response_shape_remains_compatible(self):
        ctx=_fact_ledger_context_v11(sample())
        output=self.run_response({'summary':ctx['selection_policy']['mandatory_summary']})
        self.assertEqual(output['status'],'completed')
        self.assertFalse(output['selection_fallback'])
        self.assertIn('selection',output)
        self.assertEqual(output['interpretation_status'],'no_added_value')

    def test_bad_response_keeps_legacy_deterministic_fallback_without_ai_credit(self):
        output=self.run_response('Imaginary dishwasher 999 kWh')
        self.assertTrue(output['selection_fallback'])
        self.assertEqual(output['interpretation_status'],'invalid_response')
        result=sample();result['ai_analysis']=output
        self.assertNotIn('999 kWh',render_report_html(result))
        self.assertNotIn('ai-text',_ai_analysis(result))
