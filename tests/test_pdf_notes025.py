"""Conservative detail-note grouping, scoped to a device and comparison target."""
import copy
import re
import unittest

from test_energy_insights import scenario
from analysis.ai_report import _fact_ledger_context_v11, _render_ledger_id
from rendering.html_report import _comparisons, render_report_html


def refrigerator(language='fr'):
    result = scenario()
    result['report']['language'] = language
    result['catalogs'][0]['devices'][1]['device']['category'] = 'refrigeration'
    for source in result['comparisons']['targets'][0]['catalogs'][0]['devices'][1]['sources']:
        source['comparison_status'] = 'partial'
        source['base_quality']['period_coverage_percent'] = 90
        source['reference_quality']['period_coverage_percent'] = 85
    return result


class PdfDetailNotes025Tests(unittest.TestCase):
    def test_repeated_common_cautions_are_grouped_once(self):
        result = refrigerator()
        context = _fact_ledger_context_v11(result)
        html = _comparisons(result, context)
        self.assertEqual(html.count('Les cycles du compteur peuvent être des démarrages'), 1)
        self.assertEqual(html.casefold().count('performance de période complète non établie'), 1)
        self.assertIn('Note de fiabilité', html)

    def test_indicator_specific_coverages_and_all_numbers_survive(self):
        result = refrigerator()
        context = _fact_ledger_context_v11(result)
        ratios = [f for f in context['facts'] if f['k'] in {'energy_per_cycle', 'runtime_per_cycle'}]
        ratios[0]['coverage'], ratios[1]['coverage'] = 82.3, 91.1
        before = copy.deepcopy(context)
        html = _comparisons(result, context)
        self.assertIn('82,3 %', html)
        self.assertIn('91,1 %', html)
        for fact in ratios:
            text = _render_ledger_id(fact['i'], context, 'fr', 'detail')
            for value in re.findall(r'\d+(?:,\d+)?', text):
                self.assertIn(value, html)
        self.assertIn('kWh/h', html)
        self.assertEqual(context, before)

    def test_notes_are_not_merged_across_periods(self):
        result = refrigerator()
        target = copy.deepcopy(result['comparisons']['targets'][0])
        target.update(id='n2', label='N-2')
        target['resolved_period']['label'] = 'Earlier reference'
        result['comparisons']['targets'].append(target)
        html = _comparisons(result, _fact_ledger_context_v11(result))
        self.assertEqual(html.count('Les cycles du compteur peuvent être des démarrages'), 2)
        self.assertEqual(html.casefold().count('performance de période complète non établie'), 2)

    def test_single_indicator_keeps_its_own_specific_caution(self):
        result = refrigerator()
        context = _fact_ledger_context_v11(result)
        context['facts'] = [f for f in context['facts'] if f['k'] not in {'runtime_per_cycle', 'energy_per_runtime'}]
        html = _comparisons(result, context)
        self.assertEqual(html.count('Les cycles du compteur peuvent être des démarrages'), 1)
        self.assertNotIn('Note de fiabilité', html)
        self.assertIn('performance de période complète non établie', html)

    def test_english_grouping_preserves_units_and_partial_scope(self):
        result = refrigerator('en')
        html = _comparisons(result, _fact_ledger_context_v11(result))
        self.assertEqual(html.count('Counter cycles may represent starts'), 1)
        self.assertEqual(html.casefold().count('full-period performance is not established'), 1)
        self.assertIn('Reliability note', html)
        self.assertIn('kWh/cycle', html)
        self.assertIn('h/cycle', html)
        self.assertIn('kWh/h', html)

    def test_configured_categories_are_preserved_even_when_unknown(self):
        for category in ('refrigeration', 'ventilation', 'custom_user_category', None):
            result = refrigerator()
            result['catalogs'][0]['devices'][1]['device']['category'] = category
            before = copy.deepcopy(result)
            html = render_report_html(result)
            if category:
                self.assertIn(category, html)
            self.assertEqual(result, before)

    def test_empty_derived_group_does_not_create_an_empty_note(self):
        result = scenario()
        result.pop('comparisons')
        html = render_report_html(result)
        self.assertNotIn('derived-reliability', html)

    def test_unknown_or_indicator_specific_warning_is_not_removed(self):
        from rendering.html_report import _derived_detail_html
        specific = 'Energy source sample interval is uncertain.'
        rows = [('energy_per_cycle', 'Value 0.70 kWh/cycle. ' + specific),
                ('runtime_per_cycle', 'Value 2.00 h/cycle. Different runtime limitation.')]
        html = _derived_detail_html(rows, 'en')
        self.assertIn(specific, html)
        self.assertIn('Different runtime limitation.', html)
        self.assertNotIn('derived-reliability', html)

    def test_unstable_identity_does_not_trigger_common_note_grouping(self):
        from rendering.html_report import _derived_detail_html
        clause = ' Counter cycles may represent starts; this descriptive ratio does not measure efficiency.'
        rows = [('energy_per_cycle', '1 kWh/cycle.' + clause),
                ('runtime_per_cycle', '1 h/cycle.' + clause)]
        html = _derived_detail_html(rows, 'en', group_notes=False)
        self.assertEqual(html.count('Counter cycles may represent starts'), 2)
        self.assertNotIn('derived-reliability', html)
