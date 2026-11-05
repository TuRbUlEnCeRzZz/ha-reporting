"""Synthetic reference scenarios, not a replay of unavailable HA history."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ha-reporting' / 'app'))
from analysis.ai_report import (_fact_ledger_context_v11, _allowed_selection_ids,
    _fact_score, _render_selection_analysis, _fallback_selection, _validate_selection,
    build_budgeted_ai_context, _render_recommendation)
from analysis.insights import report_digest, mobile_summary
from comparisons.engine import ComparisonEngine
from rendering.html_report import render_report_html
from rendering.pdf_report import render_pdf_native
import main


def source(key, metric, value, unit, **statistics):
    stats = {'delta': value, 'last': {'value': value}, 'mode': 'direct', **statistics}
    return {'sensor_key': key, 'entity_id': 'sensor.' + key, 'metric': metric,
        'unit': unit, 'status': 'ok', 'analysis': {'statistics': stats,
        'quality': {'period_coverage_percent': 100, 'density_applicable': False},
        'validation': {'valid': True, 'warnings': []}}}


def scenario(energy=3.49, reference=3.10, cycles=5, previous_cycles=7):
    devices = [
        {'device': {'id': 'total', 'name': 'Appartement'}, 'sources': [
            source('total_active_energy', 'energy_total', 58.80, 'kWh'),
            dict(source('emhass_forecast', 'power', 0, 'W', mean=307.9167,
                        integrated_energy_kwh=51.73), derive_energy=True)]},
        {'device': {'id': 'washer', 'name': 'Lave-linge'}, 'sources': [
            source('washer_energy', 'energy_total', energy, 'kWh'),
            source('washer_cycles', 'cycles', cycles, 'cycles'),
            source('washer_runtime', 'runtime', 10, 'h')]},
    ]
    current = {'report': {'name': 'Rapport domotique hebdomadaire', 'language': 'fr'},
        'resolved_period': {'label': '26.10.2026–02.11.2026', 'timezone': 'Europe/Zurich'},
        'summary': {'sources_total': 5, 'sources_ok': 5, 'devices_total': 2},
        'catalogs': [{'id': 'home', 'name': 'Maison', 'devices': devices}]}
    previous = copy.deepcopy(current)
    previous['catalogs'][0]['devices'][0]['sources'][0]['analysis']['statistics']['delta'] = 59.7
    for item, value in zip(previous['catalogs'][0]['devices'][1]['sources'], (reference, previous_cycles, 14)):
        item['analysis']['statistics']['delta'] = value
    current['comparisons'] = {'enabled': True, 'targets': [ComparisonEngine().compare_target(
        current, previous, {'id': 'previous', 'kind': 'period', 'offset': 1, 'label': 'Semaine précédente'})]}
    return current


def derived(result):
    return [f for f in _fact_ledger_context_v11(result)['facts'] if f['k'] in {'energy_per_cycle', 'runtime_per_cycle'}]


class EnergyInsightsTests(unittest.TestCase):
    def test_reference_numbers_and_precision(self):
        result = scenario()
        before = copy.deepcopy(result)
        context = _fact_ledger_context_v11(result)
        relation = context['relationships'][0]
        self.assertAlmostEqual(relation['actual_energy_kwh'], 58.80)
        self.assertAlmostEqual(relation['forecast_energy_kwh'], 51.73)
        self.assertAlmostEqual(relation['relative_gap_pct'], 13.667, delta=.001)
        total = next(f for f in context['facts'] if f.get('q') == 'comparison' and f.get('k') == 'period_delta')
        self.assertAlmostEqual(total['p'], -1.5075376884422)
        energy = next(f for f in derived(result) if f['k'] == 'energy_per_cycle')
        self.assertAlmostEqual(energy['b'], .698)
        self.assertAlmostEqual(energy['r'], 3.1/7)
        self.assertAlmostEqual(energy['p'], (3.49/5/(3.1/7)-1)*100)
        self.assertEqual(result, before)

    def test_duration_per_cycle_and_units(self):
        self.assertEqual(next(f for f in derived(scenario()) if f['k'] == 'runtime_per_cycle')['b'], 2)
        result = scenario()
        for item in result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources']:
            if item['metric'] == 'runtime':
                item['unit'] = 'min'
                item['values'][0]['base'] = 600
                item['values'][0]['reference'] = 840
        self.assertAlmostEqual(next(f for f in derived(result) if f['k'] == 'runtime_per_cycle')['b'], 2)

    def test_zero_cycles_missing_values_and_nonfinite(self):
        for value in (0, None, float('nan'), float('inf'), -1):
            with self.subTest(value=value):
                self.assertEqual(derived(scenario(cycles=value)), [])
        self.assertEqual(derived(scenario(previous_cycles=0)), [])

    def test_zero_energy_not_a_highlight(self):
        result = scenario(0, 0)
        context = _fact_ledger_context_v11(result)
        summary, _, _ = _allowed_selection_ids(context)
        self.assertFalse(any(f['i'] in summary for f in context['facts'] if f.get('b') == 0 and f.get('r') == 0))
        self.assertNotIn('0 kWh contre 0 kWh', mobile_summary(result))

    def test_zero_reference_does_not_invent_percentage(self):
        energy = next(f for f in derived(scenario(reference=0)) if f['k'] == 'energy_per_cycle')
        self.assertNotIn('p', energy)

    def test_partial_reconstructed_missing_coverage_and_invalid_are_not_ratios(self):
        for status in ('limited', 'reconstructed', 'unavailable'):
            result = scenario()
            item = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][1]
            item['comparison_status'] = status
            self.assertEqual(derived(result), [])
            self.assertEqual(item['comparison_status'], status)
        result = scenario()
        result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][1]['base_quality'].pop('period_coverage_percent')
        self.assertEqual(derived(result), [])
        result = scenario()
        result['catalogs'][0]['devices'][1]['sources'][1]['status'] = 'invalid'
        self.assertEqual(derived(result), [])

    def test_multiple_resets_preserved_without_appliance_diagnosis(self):
        result = scenario()
        src = result['catalogs'][0]['devices'][1]['sources'][1]
        src['analysis']['statistics'].update(resets_detected=3, mode='detailed_reconstructed')
        self.assertEqual(derived(result), [])
        self.assertEqual(src['analysis']['statistics']['resets_detected'], 3)
        self.assertNotIn('panne', mobile_summary(result))

    def test_ambiguous_cycles_not_paired(self):
        result = scenario()
        device = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]
        other = copy.deepcopy(device['sources'][1])
        other['entity_id'] = 'sensor.other_cycles'
        other['sensor_key'] = 'other_cycles'
        device['sources'].append(other)
        self.assertEqual(derived(result), [])

    def test_no_reference_no_ratios_no_forecast_still_renders(self):
        result = scenario()
        result.pop('comparisons')
        result['catalogs'][0]['devices'][0]['sources'].pop()
        self.assertEqual(derived(result), [])
        message = mobile_summary(result)
        self.assertIn('58,8', message)
        self.assertNotIn('prév', message)
        self.assertNotIn('contre', message)
        self.assertIn('58,8', render_report_html(result))

    def test_absolute_impact_outranks_small_doubling(self):
        sources = {'S': {'m': 'energy_total', 'u': 'kWh'}}
        comparisons = {'C': {'s': 'S'}}
        small = {'q': 'comparison', 'c': 'C', 'k': 'period_delta', 'd': .01, 'p': 100}
        big = dict(small, d=4, p=10)
        self.assertGreater(_fact_score(big, sources, comparisons), _fact_score(small, sources, comparisons))

    def test_sparse_power_available_is_not_summary_evidence(self):
        result = scenario()
        src = result['catalogs'][0]['devices'][0]['sources'][1]
        src['analysis']['quality'].update(density_applicable=True, sample_density_percent=1)
        context = _fact_ledger_context_v11(result)
        summary, attention, _ = _allowed_selection_ids(context)
        source_id = next(s['i'] for s in context['sources'] if s['e'] == src['entity_id'])
        self.assertIn(source_id, attention)
        self.assertFalse(any(f['i'] in summary for f in context['facts'] if f.get('s') == source_id))

    def test_ai_selection_and_recommendation_are_guarded(self):
        context = _fact_ledger_context_v11(scenario())
        fact = next(f for f in context['facts'] if f['k'] == 'energy_per_cycle')
        selection, valid = _validate_selection({'summary': [fact['i']], 'attention': [fact['i']],
            'recommendations': [{'action': 'check_cycle_usage', 'evidence': fact['i']}]}, context)
        self.assertTrue(valid)
        text = _render_selection_analysis(context, selection, 'fr')
        self.assertIn('0,70 kWh/cycle', text)
        self.assertIn('Moins de cycles', text)
        self.assertIn('conditions d’utilisation', text)
        self.assertIn('cause n’est pas établie', text)
        self.assertEqual(_render_recommendation('check_cycle_usage', 'F1', context, 'fr'), '')
        self.assertTrue(_fallback_selection(context)['recommendations'])

    def test_mobile_ignores_full_ai_text_and_preserves_targets(self):
        job = {'id': 'job', 'report_id': 'report', 'options': {'notification': {
            'persistent': True, 'notify_entity': 'notify.phone'}}}
        with patch.object(main, '_cached_report_result', return_value=scenario()), patch.object(main, 'home_assistant_call_service', return_value=[]) as call:
            main._notifications_for_job(job, scenario()['report'], {'status': 'completed', 'text': 'TECHNICAL WARNING ' * 1000})
        self.assertEqual(call.call_count, 2)
        messages = [c.args[2]['message'] for c in call.call_args_list]
        self.assertEqual(messages[0], messages[1])
        self.assertLess(len(messages[0]), 1500)
        self.assertIn('Énergie', messages[0])
        self.assertNotIn('TECHNICAL', messages[0])
        self.assertNotIn('Attention', messages[0])

    def test_ai_unavailable_still_pdf_and_overview(self):
        result = scenario()
        result['ai_analysis'] = {'enabled': True, 'status': 'error', 'error': 'Ollama unavailable'}
        html = render_report_html(result)
        self.assertIn('kWh/cycle', html)
        self.assertIn('Interprétation indisponible', html)
        self.assertEqual(result['ai_analysis']['error'], 'Ollama unavailable')
        path = render_pdf_native(html)
        self.assertGreater(path.stat().st_size, 1000)

    def test_deterministic_projection_keeps_cycle_facts(self):
        context, meta = build_budgeted_ai_context(scenario())
        context = json.loads(context)
        self.assertTrue(any(f['k'] == 'energy_per_cycle' for f in context['facts']))
        self.assertEqual(mobile_summary(scenario()), mobile_summary(scenario()))

    def test_many_devices_and_english_output(self):
        result = scenario()
        for n in range(60):
            other = copy.deepcopy(result['catalogs'][0]['devices'][1])
            other['device'] = {'id': f'd{n}', 'name': f'Appliance {n}'}
            for src in other['sources']:
                src['entity_id'] += str(n)
            result['catalogs'][0]['devices'].append(other)
        message = mobile_summary(result, 'en')
        self.assertIn('Energy', message)
        self.assertNotIn('Énergie', message)
        self.assertLess(len(message), 1500)
        result['report']['language'] = 'en'
        self.assertIn('Period overview', render_report_html(result))

class AdditionalRegressionTests(unittest.TestCase):
    def test_unvalidated_long_comments_do_not_expand_or_overflow_pdf(self):
        from weasyprint import HTML
        result = scenario()
        result['ai_analysis'] = {'enabled': True, 'status': 'completed', 'text': ('Commentaires détaillés sur les mesures. ' * 200) + ('longcomment' * 100)}
        document = HTML(string=render_report_html(result)).render()
        self.assertGreaterEqual(len(document.pages), 1)
        self.assertNotIn('longcommentlongcomment', render_report_html(result))
        for page in document.pages:
            for box in page._page_box.descendants():
                if getattr(box, 'text', None):
                    self.assertGreaterEqual(box.position_x, 0)
                    self.assertLessEqual(box.position_x + box.width, page.width + 1)

    def test_duration_change_is_linked_to_energy_per_cycle(self):
        result = scenario()
        item = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources'][2]
        item['values'][0]['base'] = 20
        item['values'][0]['absolute_change'] = 6
        message = mobile_summary(result)
        self.assertIn('Durée moyenne : 4,00 h/cycle contre 2,00 h/cycle', message)

    def test_model_cannot_drop_history_in_favor_of_forecast(self):
        context = _fact_ledger_context_v11(scenario())
        selection, valid = _validate_selection({'summary': [context['relationships'][0]['id']]}, context)
        self.assertTrue(valid)
        text = _render_selection_analysis(context, selection, 'fr')
        self.assertIn('+13,7 %', text)
        self.assertIn('-1,51 %', text)

    def test_sparse_forecast_remains_a_quality_warning(self):
        result = scenario()
        result['catalogs'][0]['devices'][0]['sources'][1]['analysis']['quality'].update(density_applicable=True, sample_density_percent=1)
        context = _fact_ledger_context_v11(result)
        relation = context['relationships'][0]
        self.assertFalse(relation['full_period_comparison_supported'])
        self.assertNotIn('relative_gap_pct', relation)
        text = _render_selection_analysis(context, _fallback_selection(context), 'fr')
        self.assertIn('densité', text)

    def test_pdf_overview_does_not_repeat_complete_ai_sentences(self):
        from rendering.html_report import _energy_overview
        result = scenario()
        context = _fact_ledger_context_v11(result)
        result['ai_analysis'] = {'status': 'completed', 'text': _render_selection_analysis(context, _fallback_selection(context), 'fr')}
        self.assertIn('L’essentiel', _energy_overview(result))

    def test_same_sensor_keys_keep_forecast_pairing_local(self):
        result = scenario()
        other = copy.deepcopy(result['catalogs'][0]['devices'][0])
        other['device'] = {'id': 'other', 'name': 'Autre logement'}
        for src in other['sources']:
            src['entity_id'] += '_other'
        result['catalogs'][0]['devices'].append(other)
        context = _fact_ledger_context_v11(result)
        relations = [r for r in context['relationships'] if r['kind'] == 'energy_forecast_vs_actual']
        self.assertEqual(len(relations), 2)
        self.assertNotEqual(relations[0]['actual_source_id'], relations[1]['actual_source_id'])

    def test_same_display_name_does_not_join_distinct_devices(self):
        result = scenario()
        device = result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]
        other = copy.deepcopy(device)
        other['id'] = 'other'
        other['sources'] = [other['sources'][1]]
        device['sources'].pop(1)
        result['comparisons']['targets'][0]['catalogs'][0]['devices'].append(other)
        self.assertEqual(derived(result), [])

    def test_dst_zurich_stays_half_open(self):
        from periods.engine import PeriodEngine
        engine = PeriodEngine('Europe/Zurich')
        for start, end, hours in (('2026-10-25', '2026-10-26', 25), ('2026-03-29', '2026-03-30', 23), ('2026-10-26', '2026-11-02', 168)):
            resolved = engine.resolve({'type': 'custom', 'start': start, 'end': end}).as_dict()
            self.assertEqual(resolved['duration_seconds'], hours*3600)
            self.assertEqual(resolved['semantics'], '[start, end)')

    def test_invalid_ai_json_uses_deterministic_fallback(self):
        context = _fact_ledger_context_v11(scenario())
        for invalid in ('not JSON', {'summary': ['invented']}, {'summary': None}):
            selection, valid = _validate_selection(invalid, context)
            self.assertFalse(valid)
            text = _render_selection_analysis(context, _fallback_selection(context), 'fr')
            self.assertIn('kWh', text)
            self.assertNotIn('invented', text)

    def test_generic_advice_not_repeated_for_many_sources(self):
        from analysis.ai_report import _merged_recommendation_lines
        context = _fact_ledger_context_v11(scenario())
        selection = {'recommendations': [{'action': 'monitor_source', 'evidence': s['i']} for s in context['sources']]}
        self.assertEqual(len(_merged_recommendation_lines(selection, context, 'fr')), 1)


if __name__ == '__main__':
    unittest.main()
