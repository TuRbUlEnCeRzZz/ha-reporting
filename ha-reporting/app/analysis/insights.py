"""Deterministic presentation insights; never alter measured statistics."""
from __future__ import annotations

import math
from collections import defaultdict


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def add_cycle_facts(context):
    """Join unambiguous device-local comparable counters for the same target.

    Reconstructed/partial/invalid counters remain in the original ledger but
    cannot establish a change in energy per cycle. Unknown coverage is also
    insufficient for this derived claim. No additional provider request occurs.
    """
    sources = {s['i']: s for s in context['sources']}
    comparisons = {c['i']: c for c in context['comparison_sets']}
    groups = defaultdict(lambda: defaultdict(list))
    for fact in list(context['facts']):
        comparison = comparisons.get(fact.get('c'), {})
        source = sources.get(comparison.get('s'), {})
        if fact.get('q') != 'comparison' or fact.get('k') != 'period_delta':
            continue
        if source.get('sh') or source.get('st') or source.get('w') or source.get('reset'):
            continue
        if comparison.get('p') != 'full_period_change_allowed' or comparison.get('st') not in {None, 'comparable'} or any(comparison.get(k) for k in ('br', 'rr', 'bz', 'rz')):
            continue
        if any(number(comparison.get(k)) is None or number(comparison[k]) < 95 for k in ('bc', 'rc')):
            continue
        scope = source.get('device_scope') or []
        if len(scope) != 2 or not all(scope):
            continue
        if any(number(fact.get(k)) is None or number(fact[k]) < 0 for k in ('b', 'r')):
            continue
        key = (*scope, comparison.get('tg'), comparison.get('tp'))
        groups[key][source.get('m')].append((fact, source, comparison))

    for metrics in groups.values():
        if len(metrics['cycles']) != 1:
            continue
        cycles, _, _ = metrics['cycles'][0]
        if cycles['b'] <= 0 or cycles['r'] <= 0:
            continue
        for metric, stat, units in (
            ('energy_total', 'energy_per_cycle', {'kwh': 1, 'wh': .001, 'mwh': 1000}),
            ('runtime', 'runtime_per_cycle', {'h': 1, 'min': 1/60, 's': 1/3600}),
        ):
            if len(metrics[metric]) != 1:
                continue
            fact, source, comparison = metrics[metric][0]
            factor = units.get(str(source.get('u') or '').lower())
            if factor is None:
                continue
            base = fact['b'] * factor / cycles['b']
            reference = fact['r'] * factor / cycles['r']
            if not all(math.isfinite(v) for v in (base, reference)):
                continue
            row = {
                'i': f"F{len(context['facts']) + 1}", 'q': 'comparison',
                's': source['i'], 'c': comparison['i'], 'k': stat,
                'b': base, 'r': reference, 'd': base-reference,
                'contributors': [fact['i'], cycles['i']],
                'cycles_base': cycles['b'], 'cycles_reference': cycles['r'],
                'total_gap': fact['b']-fact['r'],
                'energy_impact_kwh': max(abs(fact['b']-fact['r']) * factor, abs(base-reference) * cycles['b']) if metric == 'energy_total' else None,
            }
            if reference > 0:
                pct = (base-reference) / reference * 100
                if math.isfinite(pct):
                    row['p'] = pct
            context['facts'].append(row)


def report_digest(result, language='fr'):
    """Select complete sentences for both the PDF overview and mobile message."""
    from .ai_report import (
        _fact_ledger_context_v11, _allowed_selection_ids, _fact_score,
        _render_ledger_id, _render_recommendation,
    )
    context = _fact_ledger_context_v11(result)
    sources = {s['i']: s for s in context['sources']}
    comparisons = {c['i']: c for c in context['comparison_sets']}
    allowed, _, _ = _allowed_selection_ids(context)
    ranked = sorted(
        (f for f in context['facts'] if f['i'] in allowed),
        key=lambda f: (-_fact_score(f, sources, comparisons), f['i']),
    )
    energy = []
    total_sources = set()
    for relation in context['relationships']:
        if relation.get('kind') == 'energy_forecast_vs_actual' and relation.get('full_period_comparison_supported'):
            energy.append(_render_ledger_id(relation['id'], context, language, 'summary'))
            total_sources.add(relation.get('actual_source_id'))
    # A total is only identified from the validated forecast pairing or the
    # established total-meter sensor key, never by summing overlapping meters.
    for sid, source in sources.items():
        if 'total_active_energy' in str(source.get('sk') or '').lower():
            total_sources.add(sid)
    for fact in ranked:
        source_id = fact.get('s') or comparisons.get(fact.get('c'), {}).get('s')
        if source_id in total_sources and fact.get('k') == 'period_delta':
            if fact.get('q') == 'comparison' or not energy:
                energy.append(_render_ledger_id(fact['i'], context, language, 'summary'))
            if len(energy) >= 3:
                break
    highlights, seen_devices, recommendation = [], set(), []
    for fact in ranked:
        source = sources.get(fact.get('s') or comparisons.get(fact.get('c'), {}).get('s'), {})
        identity = (source.get('g'), source.get('d'))
        if source.get('i') in total_sources or identity in seen_devices or fact.get('q') != 'comparison':
            continue
        if number(fact.get('d')) in (None, 0):
            continue
        highlights.append(_render_ledger_id(fact['i'], context, language, 'summary'))
        seen_devices.add(identity)
        if not recommendation and fact.get('k') == 'energy_per_cycle' and (number(fact.get('p')) or 0) >= 20:
            recommendation.append(_render_recommendation('check_cycle_usage', fact['i'], context, language))
        if len(highlights) >= 3:
            break
    attention = []
    invalid = sum(int((result.get('summary') or {}).get(k) or 0) for k in ('sources_error', 'sources_invalid'))
    if invalid:
        attention.append(
            f'{invalid} source(s) invalid or in error; check the measurements in the PDF. No appliance fault is established.'
            if language == 'en' else
            f'{invalid} source(s) invalide(s) ou en erreur : vérifier les mesures dans le PDF. Aucune panne d’appareil n’est établie.'
        )
    return {'energy': list(dict.fromkeys(filter(None, energy))), 'highlights': highlights,
            'attention': attention, 'recommendation': recommendation}


def mobile_summary(result, language='fr'):
    digest = report_digest(result, language)
    labels = ('Energy', 'Highlights', 'Attention', 'Recommendation') if language == 'en' else ('Énergie', 'Faits marquants', 'Attention', 'Recommandation')
    return '\n\n'.join(
        label + '\n' + '\n'.join('- ' + text for text in digest[key][:limit])
        for label, key, limit in zip(labels, digest, (3, 2, 1, 1)) if digest[key]
    )
