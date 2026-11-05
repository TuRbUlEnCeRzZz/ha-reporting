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
        key = (*scope, comparison.get('target_id'), comparison.get('tg'), comparison.get('tp'))
        groups[key][source.get('m')].append((fact, source, comparison))

    for metrics in groups.values():
        if len(metrics['cycles']) != 1:
            continue
        cycles, cycle_source, _ = metrics['cycles'][0]
        cycle_unit = str(cycle_source.get('u') or '').lower()
        if cycle_unit not in {'', 'cycle', 'cycles', 'count', 'counts', 'start', 'starts', 'démarrages'}:
            continue
        if cycles['b'] < 1 or cycles['r'] < 1:
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
                'energy_impact_kwh': abs(base-reference) * min(cycles['b'], cycles['r']) if metric == 'energy_total' else None,
            }
            if cycle_unit in {'start', 'starts', 'démarrages'}:
                row['cycle_kind'] = 'starts'
            if reference > 0:
                pct = (base-reference) / reference * 100
                if math.isfinite(pct):
                    row['p'] = pct
            context['facts'].append(row)


def no_significant_change(language='fr'):
    return ('No significant change detected during this period.' if language == 'en'
            else 'Aucune évolution significative détectée sur cette période.')


def meaningful_change(fact, source, comparison):
    """Presentation noise guard, not a statistical significance test.

    Physical-unit floors differ by metric; percentages alone are insufficient.
    Existing coverage policies remain authoritative. No appliance family or
    counter meaning is guessed from a name.
    """
    if fact.get('q') != 'comparison' or comparison.get('st') not in (None, 'comparable'):
        return False
    if any(comparison.get(k) for k in ('bz', 'rz', 'br', 'rr')) or source.get('st'):
        return False
    coverage = [number(comparison.get(k)) for k in ('bc', 'rc')]
    if any(v is not None and v < 95 for v in coverage):
        return False
    gap = number(fact.get('d'))
    if gap in (None, 0):
        return False
    pct = abs(number(fact.get('p')) or 0)
    stat, metric = fact.get('k'), source.get('m')
    if stat == 'energy_per_cycle':
        # A configured refrigeration family does not establish usage-cycle
        # semantics. Ratios stay descriptive in the ledger, not headline advice.
        return (source.get('category') != 'refrigeration' and pct >= 5
                and (number(fact.get('energy_impact_kwh')) or 0) >= .1)
    if stat == 'runtime_per_cycle':
        return (source.get('category') != 'refrigeration' and pct >= 10
                and abs(gap)*3600 >= 30
                and abs(gap)*min(fact.get('cycles_base', 0), fact.get('cycles_reference', 0)) >= .25)
    if stat == 'period_delta' and metric == 'energy_total':
        factor = {'kwh': 1, 'wh': .001, 'mwh': 1000}.get(str(source.get('u') or '').lower())
        return factor is not None and abs(gap)*factor >= .1 and (pct >= 5 or abs(gap)*factor >= 1)
    if stat == 'period_delta' and metric == 'runtime':
        factor = {'h': 1, 'min': 1/60, 's': 1/3600}.get(str(source.get('u') or '').lower())
        return factor is not None and abs(gap)*factor >= .5 and pct >= 10
    if stat == 'mean' and metric == 'temperature':
        return str(source.get('u') or '').lower() in {'°c', 'c', '°f', 'f'} and abs(gap) >= 1
    if stat == 'mean' and metric == 'power':
        factor = {'w': 1, 'kw': 1000, 'mw': 1000000}.get(str(source.get('u') or '').lower())
        return factor is not None and abs(gap)*factor >= 10 and pct >= 10
    # Standalone start counts and power peaks do not establish energy impact.
    return False


def priority_highlights(context, limit=3):
    """Shared ordered appliance selection for PDF, mobile and AI policy."""
    from .ai_report import _fact_score
    sources = {s['i']: s for s in context.get('sources', [])}
    comparisons = {c['i']: c for c in context.get('comparison_sets', [])}
    totals = {r.get('actual_source_id') for r in context.get('relationships', [])
              if r.get('kind') == 'energy_forecast_vs_actual'}
    totals.update(sid for sid, s in sources.items()
                  if 'total_active_energy' in str(s.get('sk') or '').lower())
    ranked = []
    for fact in context.get('facts', []):
        comp = comparisons.get(fact.get('c'), {})
        source = sources.get(fact.get('s') or comp.get('s'), {})
        if source.get('i') in totals or not meaningful_change(fact, source, comp):
            continue
        scope = tuple(source.get('device_scope') or [])
        if len(scope) != 2 or not all(scope):
            continue
        ranked.append((fact, source, comp, scope))
    ranked.sort(key=lambda row: (-_fact_score(row[0], sources, comparisons), row[0]['i']))
    selected, seen = [], set()
    for fact, source, comp, scope in ranked:
        if scope in seen:
            continue
        seen.add(scope)
        selected.append(fact['i'])
        if len(selected) >= limit:
            break
    return selected


def qualified_attention(context):
    """Keep a material reconstructed total usable, explicitly as qualified data."""
    sources = {s['i']: s for s in context.get('sources', [])}
    comparisons = {c['i']: c for c in context.get('comparison_sets', [])}
    candidates = []
    for fact in context.get('facts', []):
        comp = comparisons.get(fact.get('c'), {})
        source = sources.get(comp.get('s'), {})
        if fact.get('q') != 'comparison' or fact.get('k') != 'period_delta' or source.get('m') != 'energy_total':
            continue
        if not (comp.get('st') == 'reconstructed' or comp.get('br') or comp.get('rr')):
            continue
        if source.get('st') or comp.get('st') in {'unavailable', 'limited'} or any(comp.get(k) for k in ('bz', 'rz')):
            continue
        if any(number(comp.get(k)) is None or number(comp[k]) < 95 for k in ('bc', 'rc')):
            continue
        if any(number(fact.get(k)) is None for k in ('b', 'r', 'd')):
            continue
        factor = {'kwh': 1, 'wh': .001, 'mwh': 1000}.get(str(source.get('u') or '').lower())
        if factor is None:
            continue
        impact = abs(fact['d'])*factor
        if impact >= .1 and (abs(number(fact.get('p')) or 0) >= 5 or impact >= 1):
            candidates.append((impact, fact['i']))
    return [fid for _, fid in sorted(candidates, key=lambda row: (-row[0], row[1]))[:1]]


def format_cycle_pair(stat, base, reference, language='fr'):
    """Format only at the presentation boundary; preserve authoritative ratios."""
    def fixed(value, digits):
        text = f'{value:.{digits}f}'
        return text.replace('.', ',') if language == 'fr' else text
    if stat == 'runtime_per_cycle' and max(base, reference) < 1:
        def duration(hours):
            seconds = round(hours*3600)
            minutes, seconds = divmod(seconds, 60)
            return f'{minutes} min {seconds:02d} s' if minutes else f'{seconds} s'
        return duration(base), duration(reference), '/cycle'
    factor, unit, digits = 1, ('h/cycle' if stat == 'runtime_per_cycle' else 'kWh/cycle'), 2
    if stat == 'energy_per_cycle' and 0 < max(base, reference) < .1:
        factor, unit, digits = 1000, 'Wh/cycle', 1
    while digits < 4 and base != reference and fixed(base*factor, digits) == fixed(reference*factor, digits):
        digits += 1
    return fixed(base*factor, digits), fixed(reference*factor, digits), unit


def report_digest(result, language='fr', context=None):
    """Select complete sentences for both the PDF overview and mobile message."""
    from .ai_report import (
        _fact_ledger_context_v11, _allowed_selection_ids, _fact_score,
        _render_ledger_id, _render_recommendation,
    )
    context = context if context is not None else _fact_ledger_context_v11(result)
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
    selected = (context.get('selection_policy') or {}).get('priority_highlights', [])
    highlights = [_render_ledger_id(fid, context, language, 'summary') for fid in selected]
    recommendation = []
    for fid in selected[:2]:
        text = _render_recommendation('check_cycle_usage', fid, context, language)
        if text:
            recommendation.append(text)
            break
    attention = [_render_ledger_id(fid, context, language, 'attention')
                 for fid in (context.get('selection_policy') or {}).get('priority_attention', [])]
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
    if not digest['highlights']:
        digest['highlights'] = [no_significant_change(language)]
    return '\n\n'.join(
        label + '\n' + '\n'.join('- ' + text for text in digest[key][:limit])
        for label, key, limit in zip(labels, digest, (3, 2, 1, 1)) if digest[key]
    )
