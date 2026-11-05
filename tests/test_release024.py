"""PDF-derived rounded examples; never substitutes for unavailable raw history."""
import copy
import unittest
from test_insight_relevance import weekly_example
from analysis.ai_report import (_fact_ledger_context_v11, _fallback_selection,
    _render_selection_analysis, build_budgeted_ai_context)
from analysis.insights import report_digest, mobile_summary
from rendering.html_report import render_report_html, _energy_overview, _ai_analysis
import json
from pathlib import Path


def reference():
    result = weekly_example()
    fixture=json.loads((Path(__file__).parent/'fixtures/report_023_excerpt.json').read_text())
    # Aggregate header counts are transcribed; individual records are an excerpt.
    result['summary'].update(devices_total=16,sources_total=78,sources_ok=78)
    entries=[(d['id'],*d['energy'],*d['cycles'],*d['energy_coverage']) for d in fixture['devices'] if 'cycles' in d]
    for device_id, base, previous, cycles, old_cycles, bc, rc in entries:
        dev = next(d for d in result['comparisons']['targets'][0]['catalogs'][0]['devices'] if d['id']==device_id)
        current = next(d for d in result['catalogs'][0]['devices'] if d['device']['id']==device_id)
        for src, value in zip(current['sources'], (base,cycles)):
            src['analysis']['statistics']['delta']=value
            src['analysis']['quality']['period_coverage_percent']=bc
        item=next(d for d in fixture['devices'] if d['id']==device_id)
        for src, b, r in zip(dev['sources'], (base,cycles),(previous,old_cycles)):
            src['comparison_status']='partial'
            src['base_quality']['period_coverage_percent']=bc
            src['reference_quality']['period_coverage_percent']=rc
            if src['metric']=='cycles':
                src['base_quality']['period_coverage_percent'],src['reference_quality']['period_coverage_percent']=item['cycle_coverage']
            src['values'][0].update(base=b,reference=r,absolute_change=b-r,
                relative_change_percent=(b/r-1)*100)
    # Reconstructed TV energy remains a separate qualified observation.
    from test_energy_insights import source
    from comparisons.engine import ComparisonEngine
    tv=next(d for d in fixture['devices'] if d['id']=='tv')
    current=source('tv_energy','energy_total',tv['energy'][0],'kWh')
    previous=source('tv_energy','energy_total',tv['energy'][1],'kWh')
    for src,cov in zip((current,previous),tv['energy_coverage']):
        src['analysis']['quality'].update(period_coverage_percent=cov,counter_mode='reconstructed')
        src['analysis']['statistics']['mode']='reconstructed'
    result['catalogs'][0]['devices'].append({'device':{'id':'tv','name':'TV / PC salon','category':'multimedia'},'sources':[current]})
    result['comparisons']['targets'][0]['catalogs'][0]['devices'].append({'id':'tv','name':'TV / PC salon','category':'multimedia','sources':[ComparisonEngine()._compare_source(current,previous)]})
    return result


class Release024Tests(unittest.TestCase):
    def test_partial_ratios_exist_and_are_qualified_on_all_outputs(self):
        result=reference(); context=_fact_ledger_context_v11(result)
        ratios=[f for f in context['facts'] if f['k']=='energy_per_cycle' and f.get('qualified')]
        self.assertEqual(len(ratios),3)
        digest=report_digest(result)
        self.assertIn('Lave-linge', ' '.join(digest['highlights']))
        self.assertIn('partiel', ' '.join(digest['highlights']))
        ai=_render_selection_analysis(context,_fallback_selection(context),'fr')
        for text in digest['highlights']: self.assertIn(text,ai)
        self.assertIn('partiel',mobile_summary(result))
        projection=json.loads(build_budgeted_ai_context(result)[0])
        self.assertEqual(context['selection_policy']['priority_highlights'],projection['selection_policy']['priority_highlights'])

    def test_overview_survives_duplicate_ai_text_without_repeating_it(self):
        result=reference(); context=_fact_ledger_context_v11(result)
        result['ai_analysis']={'enabled':True,'status':'completed','text':_render_selection_analysis(context,_fallback_selection(context),'fr')}
        self.assertIn('L’essentiel',_energy_overview(result))
        text=report_digest(result)['highlights'][0]
        self.assertNotIn(text, _ai_analysis(result))

    def test_partial_does_not_mean_arbitrary_low_quality(self):
        result=reference()
        for src in result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources']:
            src['base_quality']['period_coverage_percent']=40
        context=_fact_ledger_context_v11(result)
        source_ids={s['i'] for s in context['sources'] if s.get('d')=='Lave-linge'}
        self.assertFalse(any(f.get('s') in source_ids and f['k']=='energy_per_cycle' for f in context['facts']))

    def test_inputs_preserved_and_three_is_a_maximum(self):
        result=reference(); original=copy.deepcopy(result)
        self.assertLessEqual(len(report_digest(result)['highlights']),3)
        mobile_summary(result); render_report_html(result)
        self.assertEqual(result,original)

    def test_partial_reconstructed_total_is_qualified_attention(self):
        result=reference()
        src=result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][0]
        src['comparison_status']='reconstructed'
        self.assertIn('reconstr',' '.join(report_digest(result)['attention']))

    def test_energy_per_operating_hour_is_descriptive_and_requires_runtime(self):
        from test_energy_insights import scenario
        result=scenario()
        result['catalogs'][0]['devices'][1]['device']['category']='refrigeration'
        context=_fact_ledger_context_v11(result)
        row=next(f for f in context['facts'] if f['k']=='energy_per_runtime')
        self.assertAlmostEqual(row['b'],3.49/10)
        self.assertAlmostEqual(row['r'],3.10/14)
        result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][2]['values'][0]['reference']=0
        self.assertFalse(any(f['k']=='energy_per_runtime' for f in _fact_ledger_context_v11(result)['facts']))

    def test_no_full_period_claim_or_generic_advice_for_partial_ratios(self):
        from analysis.ai_report import _recommendation_action_supported
        result=reference(); context=_fact_ledger_context_v11(result)
        row=next(f for f in context['facts'] if f['k']=='energy_per_cycle' and f.get('qualified'))
        self.assertIn(row['i'],context['selection_policy']['priority_highlights'])
        self.assertFalse(_recommendation_action_supported('collect_more_data',row['c'],context))
        self.assertIn('ratio observé partiel',mobile_summary(result))

    def test_pdf_displayed_percent_is_not_recomputed_from_rounded_values(self):
        from analysis.ai_report import _render_ledger_id
        fixture=json.loads((Path(__file__).parent/'fixtures/report_023_excerpt.json').read_text())
        context=_fact_ledger_context_v11(reference())
        total=next(s['i'] for s in context['sources'] if s.get('sk')=='total_active_energy')
        comp=next(c['i'] for c in context['comparison_sets'] if c['s']==total)
        row=next(f for f in context['facts'] if f.get('c')==comp and f['k']=='period_delta')
        row.update(d=fixture['displayed_energy']['historical_gap_kwh'],p=fixture['displayed_energy']['historical_gap_percent'])
        self.assertIn('-1,53',_render_ledger_id(row['i'],context,'fr','summary'))
        self.assertNotAlmostEqual(row['p'],(row['b']/row['r']-1)*100,places=3)

    def test_ventilation_uses_counts_without_claiming_timer_drift(self):
        result=reference()
        # Isolate this functional observation; no unrelated energy fixture can win.
        result['catalogs'][0]['devices']=result['catalogs'][0]['devices'][:1]+[result['catalogs'][0]['devices'][5]]
        target=result['comparisons']['targets'][0]
        target['catalogs'][0]['devices']=target['catalogs'][0]['devices'][:1]+[target['catalogs'][0]['devices'][5]]
        message=mobile_summary(result)
        self.assertIn('119 contre 95',message)
        self.assertIn('Sollicitations plus nombreuses',message)
        self.assertIn('aucune dérive',message)

    def test_tv_reconstruction_and_mobile_length(self):
        result=reference()
        self.assertIn('TV / PC salon',report_digest(result)['attention'][0])
        self.assertIn('reconstr',mobile_summary(result))
        self.assertLess(len(mobile_summary(result)),1600)

    def test_priority_and_qualified_numbers_survive_every_ai_context_mode(self):
        result=reference()
        full=_fact_ledger_context_v11(result)
        ids=full['selection_policy']['priority_highlights']
        for mode in ('optimized','extended','complete','automatic'):
            projected=json.loads(build_budgeted_ai_context(result,context_level=mode)[0])
            self.assertEqual(projected['selection_policy']['priority_highlights'],ids)
            index={f['i']:f for f in projected['facts']}
            for fid in ids:
                self.assertIn(fid,index)
