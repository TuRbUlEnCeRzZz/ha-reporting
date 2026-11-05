"""Presentation regressions for the 26 Oct–2 Nov 2026 examples.

Only quoted examples are reproduced; missing weekly history is not fabricated.
"""
import copy
import json
import unittest
from pathlib import Path
from datetime import datetime
from test_energy_insights import source, scenario, derived
from periods.engine import PeriodEngine
from comparisons.engine import ComparisonEngine
from analysis.insights import report_digest, mobile_summary
from analysis.ai_report import (
    _fact_ledger_context_v11, _validate_selection, _fallback_selection,
    _render_selection_analysis, _render_ledger_id, build_budgeted_ai_context,
    _recommendation_action_supported,
)
from rendering.html_report import render_report_html


def ratio_context(energy=0.0165, reference=0.0171, runtime=274/3600, previous_runtime=265/3600):
    result = scenario(energy*100, reference*100, 100, 100)
    item = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][2]
    item['values'][0].update(base=runtime*100, reference=previous_runtime*100)
    return _fact_ledger_context_v11(result)


def weekly_example():
    fixture = json.loads((Path(__file__).parent / 'fixtures/weekly_relevance_examples.json').read_text())
    result = scenario()
    base, reference = [], []
    for item in fixture['devices']:
        info = {k: item[k] for k in ('id', 'name', 'category') if k in item}
        current_sources, previous_sources = [], []
        for key, metric, unit in [('energy', 'energy_total', 'kWh'), ('runtime_seconds', 'runtime', 's'), ('cycles', 'cycles', 'cycles')]:
            if key not in item:
                continue
            current_sources.append(source(item['id']+'_'+key, metric, item[key][0], unit))
            previous_sources.append(source(item['id']+'_'+key, metric, item[key][1], unit))
        base.append({'device': info, 'sources': current_sources})
        reference.append({'device': copy.deepcopy(info), 'sources': previous_sources})
    result['resolved_period'] = PeriodEngine(fixture['period']['timezone']).resolve(
        {'type': 'custom', 'start': fixture['period']['start'], 'end': fixture['period']['end']}).as_dict()
    previous = copy.deepcopy(result)
    previous['resolved_period'] = PeriodEngine(fixture['period']['timezone']).resolve(
        {'type': 'custom', 'start': '2026-10-19', 'end': '2026-10-26'}).as_dict()
    previous['catalogs'][0]['devices'][0]['sources'][0]['analysis']['statistics']['delta'] = 59.7
    result['catalogs'][0]['devices'][1:] = base
    previous['catalogs'][0]['devices'][1:] = reference
    result['comparisons']['targets'] = [ComparisonEngine().compare_target(result, previous,
        {'id': 'previous', 'kind': 'period', 'offset': 1, 'label': 'Semaine précédente'})]
    return result


class InsightRelevanceTests(unittest.TestCase):
    def test_no_padding_with_negligible_changes(self):
        result = scenario(0.0101, 0.01, 5, 5)
        runtime = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][2]['values'][0]
        runtime.update(base=10, reference=10, absolute_change=0, relative_change_percent=0)
        self.assertEqual(report_digest(result)['highlights'], [])
        self.assertIn('Aucune évolution significative détectée sur cette période.', mobile_summary(result))

    def test_short_duration_and_small_energy_do_not_displace_washer(self):
        result = scenario()
        comparison = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]
        extra = copy.deepcopy(comparison)
        extra.update(id='fan', name='Ventilation WC')
        for src in extra['sources']:
            src['entity_id'] += '_fan'
            for value in src['values']:
                value.update(base=0, reference=0, absolute_change=0, relative_change_percent=0)
        extra['sources'][1]['values'][0].update(base=119, reference=95, absolute_change=24)
        extra['sources'][2]['values'][0].update(base=274*119/3600, reference=265*95/3600)
        result['comparisons']['targets'][0]['catalogs'][0]['devices'].append(extra)
        digest = report_digest(result)
        self.assertIn('Lave-linge', digest['highlights'][0])
        self.assertFalse(any('Ventilation WC' in s for s in digest['highlights']))

    def test_common_priority_survives_model_choice_and_projection(self):
        result = scenario()
        context = _fact_ledger_context_v11(result)
        policy = context['selection_policy']
        self.assertTrue(policy['priority_highlights'])
        selection, _ = _validate_selection({'summary': policy['mandatory_summary'][:1]}, context)
        self.assertIn(policy['priority_highlights'][0], selection['summary'])
        text = _render_selection_analysis(context, selection, 'fr')
        self.assertIn(report_digest(result)['highlights'][0], text)
        projected = json.loads(build_budgeted_ai_context(result)[0])
        self.assertEqual(projected['selection_policy']['priority_highlights'], policy['priority_highlights'])
        self.assertIn(report_digest(result)['highlights'][0], render_report_html(result))

    def test_adaptive_units_and_percentage_from_unrounded_values(self):
        context = ratio_context()
        energy = next(f for f in context['facts'] if f['k'] == 'energy_per_cycle')
        duration = next(f for f in context['facts'] if f['k'] == 'runtime_per_cycle')
        energy_text = _render_ledger_id(energy['i'], context, 'fr', 'summary')
        duration_text = _render_ledger_id(duration['i'], context, 'fr', 'summary')
        self.assertIn('16,5 Wh/cycle contre 17,1 Wh/cycle', energy_text)
        self.assertIn('-3,51', energy_text)
        self.assertIn('4 min 34 s/cycle contre 4 min 25 s/cycle', duration_text)
        self.assertIn('+3,4', duration_text)
        self.assertAlmostEqual(duration['p'], (274/265-1)*100)

    def test_subunit_cycle_denominators_are_not_ratios(self):
        self.assertEqual(derived(scenario(cycles=0.01)), [])
        self.assertEqual(derived(scenario(previous_cycles=0.5)), [])

    def test_missing_and_nonfinite_numerators_remain_missing(self):
        for value in (None, float('nan'), float('inf')):
            result = scenario(energy=value)
            self.assertFalse(any(f['k'] == 'energy_per_cycle' for f in derived(result)))

    def test_cycle_impact_is_not_total_usage_change(self):
        result = scenario(10.01, 1, 100, 10)
        energy = next(f for f in derived(result) if f['k'] == 'energy_per_cycle')
        self.assertLess(energy['energy_impact_kwh'], .01)
        self.assertNotIn('kWh/cycle', report_digest(result)['highlights'][0])

    def test_period_mismatch_cannot_join_ratios(self):
        from analysis.insights import add_cycle_facts
        context = ratio_context()
        context['facts'] = [f for f in context['facts'] if not f.get('contributors')]
        cycles = next(s['i'] for s in context['sources'] if s['m'] == 'cycles' and s.get('d') == 'Lave-linge')
        next(c for c in context['comparison_sets'] if c['s'] == cycles)['tp'] = 'different reference period'
        add_cycle_facts(context)
        self.assertFalse(any(f.get('contributors') for f in context['facts']))

    def test_refrigeration_is_descriptive_not_efficiency_or_advice(self):
        result = scenario()
        result['catalogs'][0]['devices'][1]['device']['category'] = 'refrigeration'
        context = _fact_ledger_context_v11(result)
        fact = next(f for f in context['facts'] if f['k'] == 'energy_per_cycle')
        self.assertFalse(_recommendation_action_supported('check_cycle_usage', fact['i'], context))
        text = _render_ledger_id(fact['i'], context, 'fr', 'summary')
        self.assertIn('démarrages', text)
        self.assertIn('rendement', text)
        self.assertEqual(result['catalogs'][0]['devices'][1]['device']['category'], 'refrigeration')

    def test_idle_source_has_no_collection_recommendation(self):
        result = scenario(0, 0, 0, 0)
        source = result['catalogs'][0]['devices'][1]['sources'][0]
        source['analysis']['quality']['period_coverage_percent'] = 20
        context = _fact_ledger_context_v11(result)
        sid = next(s['i'] for s in context['sources'] if s['e'] == source['entity_id'])
        self.assertFalse(_recommendation_action_supported('collect_more_data', sid, context))

    def test_quality_alerts_grouped_per_device_but_not_removed_from_ledger(self):
        result = scenario()
        for src in result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources']:
            src['comparison_status'] = 'partial'
        context = _fact_ledger_context_v11(result)
        ids = [c['i'] for c in context['comparison_sets'] if c.get('st') == 'partial']
        self.assertEqual(len(ids), 3)
        text = _render_selection_analysis(context, {'summary': [], 'attention': ids, 'recommendations': []}, 'fr')
        self.assertEqual(text.count('Lave-linge'), 1)
        self.assertEqual(len([c for c in context['comparison_sets'] if c.get('st') == 'partial']), 3)

    def test_reconstructed_counter_keeps_qualified_values_in_detail(self):
        result = scenario()
        src = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][0]
        src['comparison_status'] = 'reconstructed'
        context = _fact_ledger_context_v11(result)
        comparison = next(c for c in context['comparison_sets'] if c.get('st') == 'reconstructed')
        fact = next(f for f in context['facts'] if f.get('c') == comparison['i'] and f['k'] == 'period_delta')
        self.assertEqual(fact['b'], 3.49)
        self.assertIn('reconstr', _render_ledger_id(fact['i'], context, 'fr', 'attention'))
        self.assertIn('3.49 kWh', render_report_html(result))

    def test_inputs_and_statistics_not_mutated(self):
        result = scenario()
        before = copy.deepcopy(result)
        report_digest(result)
        mobile_summary(result)
        build_budgeted_ai_context(result)
        render_report_html(result)
        self.assertEqual(result, before)


class WeeklyExamplesTests(unittest.TestCase):
    def test_order_is_impact_and_quality_not_input_order(self):
        result = weekly_example()
        highlights = report_digest(result)['highlights']
        self.assertEqual(len(highlights), 3)
        for text, name in zip(highlights, ('Lave-linge', 'Lave-vaisselle', 'Sèche-linge')):
            self.assertTrue(text.startswith(name))
        self.assertNotIn('Armoire combinée', mobile_summary(result))
        self.assertNotIn('Ventilation WC', mobile_summary(result))
        self.assertEqual(len({line.split(' :')[0] for line in highlights}), 3)
        # A favoured example loses priority as soon as its quality is inadequate.
        for src in result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources']:
            src['base_quality']['period_coverage_percent'] = 40
        self.assertTrue(report_digest(result)['highlights'][0].startswith('Lave-vaisselle'))

    def test_small_ratios_remain_in_pdf_details(self):
        html = render_report_html(weekly_example())
        self.assertIn('derived-indicators', html)
        self.assertIn('4 min 34 s/cycle', html)
        self.assertIn('16,5 Wh/cycle', html)

    def test_energy_units_convert_without_altering_percent(self):
        result = scenario()
        original = next(f for f in derived(result) if f['k'] == 'energy_per_cycle')
        for src in result['catalogs'][0]['devices'][1]['sources']:
            if src['metric'] == 'energy_total':
                src['unit'] = 'Wh'
                src['analysis']['statistics']['delta'] *= 1000
        src = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][0]
        src['unit'] = 'Wh'
        for value in src['values']:
            for key in ('base', 'reference', 'absolute_change'):
                value[key] *= 1000
        converted = next(f for f in derived(result) if f['k'] == 'energy_per_cycle')
        self.assertAlmostEqual(original['b'], converted['b'])
        self.assertAlmostEqual(original['p'], converted['p'])

    def test_explicit_start_counters_are_not_renamed_usage_cycles(self):
        result = scenario()
        result['catalogs'][0]['devices'][1]['sources'][1]['unit'] = 'starts'
        result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][1]['unit'] = 'starts'
        context = _fact_ledger_context_v11(result)
        fact = next(f for f in context['facts'] if f['k'] == 'energy_per_cycle')
        self.assertEqual(fact['cycle_kind'], 'starts')
        self.assertIn('kWh/démarrage', _render_ledger_id(fact['i'], context, 'fr', 'summary'))
        self.assertIn('kWh/start', _render_ledger_id(fact['i'], context, 'en', 'summary'))
        self.assertFalse(_recommendation_action_supported('check_cycle_usage', fact['i'], context))

    def test_incompatible_counter_unit_is_not_a_ratio(self):
        result = scenario()
        result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][1]['unit'] = '%'
        self.assertEqual(derived(result), [])

    def test_daily_monthly_yearly_and_n_minus_x_keep_common_selection(self):
        for period_type in ('day', 'week', 'month', 'quarter', 'semester', 'year', 'custom'):
            result = weekly_example()
            spec = {'type': period_type, 'mode': 'previous', 'start': '2026-10-26', 'end': '2026-11-02'}
            result['resolved_period'] = PeriodEngine('Europe/Zurich').resolve(spec, now=datetime.fromisoformat('2026-11-05T12:00:00+01:00')).as_dict()
            target = result['comparisons']['targets'][0]
            target.update(offset=2, id='n_minus_2', label='N-2')
            digest = report_digest(result)
            context = _fact_ledger_context_v11(result)
            text = _render_selection_analysis(context, _fallback_selection(context), 'fr')
            for fact in digest['highlights']:
                self.assertIn(fact, text)
            self.assertIn('N-2', mobile_summary(result))

    def test_same_label_different_targets_do_not_join_counters(self):
        from analysis.insights import add_cycle_facts
        context = ratio_context()
        context['facts'] = [f for f in context['facts'] if not f.get('contributors')]
        cycles = next(s['i'] for s in context['sources'] if s['m'] == 'cycles' and s.get('d') == 'Lave-linge')
        next(c for c in context['comparison_sets'] if c['s'] == cycles)['target_id'] = 'other'
        add_cycle_facts(context)
        self.assertFalse(any(f.get('contributors') for f in context['facts']))

    def test_subsecond_rounding_does_not_show_an_inconsistent_percentage(self):
        context = ratio_context(runtime=.00001, previous_runtime=.000011)
        fact = next(f for f in context['facts'] if f['k'] == 'runtime_per_cycle')
        text = _render_ledger_id(fact['i'], context, 'fr', 'detail')
        self.assertIn('0 s/cycle contre 0 s/cycle', text)
        self.assertNotIn('%', text)


class ReconstructedAttentionTests(unittest.TestCase):
    def test_large_reconstructed_change_is_qualified_consistently(self):
        result = scenario(20.2, 10, 5, 5)
        src = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][0]
        src['comparison_status'] = 'reconstructed'
        context = _fact_ledger_context_v11(result)
        priorities = context['selection_policy']['priority_attention']
        self.assertEqual(len(priorities), 1)
        digest = report_digest(result)
        self.assertIn('reconstr', digest['attention'][0])
        self.assertIn('+102', digest['attention'][0])
        self.assertIn(digest['attention'][0], mobile_summary(result))
        selection, _ = _validate_selection({}, context)
        self.assertIn(priorities[0], selection['attention'])
        self.assertIn(digest['attention'][0], _render_selection_analysis(context, selection, 'fr'))
        self.assertFalse(any(f['k'] == 'energy_per_cycle' for f in derived(result)))

    def test_low_coverage_reconstruction_is_not_a_headline(self):
        result = scenario(20.2, 10)
        src = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][0]
        src['comparison_status'] = 'reconstructed'
        src['base_quality']['period_coverage_percent'] = 40
        context = _fact_ledger_context_v11(result)
        self.assertEqual(context['selection_policy']['priority_attention'], [])

    def test_invalid_reconstructed_source_is_not_qualified_evidence(self):
        result = scenario(20.2, 10)
        result['catalogs'][0]['devices'][1]['sources'][0]['status'] = 'invalid'
        result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][0]['comparison_status'] = 'reconstructed'
        context = _fact_ledger_context_v11(result)
        self.assertEqual(context['selection_policy']['priority_attention'], [])
