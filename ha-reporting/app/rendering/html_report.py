from __future__ import annotations

from datetime import datetime
from html import escape
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo


def _e(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def _num(value: Any, unit: str = "") -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if not isfinite(n):
        return "—"
    a = abs(n)
    digits = 0 if a >= 100 else 1 if a >= 10 else 2
    text = f"{n:.{digits}f}"
    return f"{text} {_e(unit)}".strip()


def _signed(value: Any, unit: str = "") -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if not isfinite(n):
        return "—"
    prefix = "+" if n > 0 else ""
    a = abs(n)
    digits = 0 if a >= 100 else 1 if a >= 10 else 2
    return f"{prefix}{n:.{digits}f}{(' ' + _e(unit)) if unit else ''}"


def _timestamp(value: Any, timezone_name: str | None = None) -> str:
    try:
        timezone = ZoneInfo(timezone_name) if timezone_name else None
        dt = datetime.fromtimestamp(float(value), timezone) if timezone else datetime.fromtimestamp(float(value)).astimezone()
        return dt.strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError, OSError, KeyError):
        return "—"


def _source_values(source: dict[str, Any]) -> list[tuple[str, str]]:
    analysis = source.get("analysis") or {}
    stats = analysis.get("statistics") or {}
    metric = source.get("metric")
    unit = source.get("unit") or ""
    if source.get("status") != "ok":
        return [("État", source.get("message") or source.get("status") or "Indisponible")]
    if metric == "power":
        maximum = stats.get("max") or {}
        return [
            ("Pic", _num(maximum.get("value"), unit)),
            ("P95", _num(stats.get("p95"), unit)),
            ("Moyenne", _num(stats.get("mean"), unit)),
        ]
    if metric == "temperature":
        return [
            ("Minimum", _num((stats.get("min") or {}).get("value"), unit)),
            ("Moyenne", _num(stats.get("mean"), unit)),
            ("Maximum", _num((stats.get("max") or {}).get("value"), unit)),
        ]
    if metric in {"energy_total", "runtime", "cycles"}:
        return [
            ("Variation période", _num(stats.get("delta"), unit)),
            ("Fin compteur", _num((stats.get("last") or {}).get("value"), unit)),
            ("Reset(s)", _num(stats.get("resets_detected"), "")),
        ]
    return [
        ("Premier", _num((stats.get("first") or {}).get("value"), unit)),
        ("Dernier", _num((stats.get("last") or {}).get("value"), unit)),
    ]


def _quality_line(source: dict[str, Any]) -> str:
    analysis = source.get("analysis") or {}
    quality = analysis.get("quality") or {}
    bits = []
    coverage = quality.get("period_coverage_percent")
    density = quality.get("sample_density_percent")
    if coverage is not None:
        bits.append(f"couverture {_num(coverage, '%')}")
    if quality.get("density_applicable") and density is not None:
        bits.append(f"densité {_num(density, '%')}")
    elif quality:
        bits.append("densité n/a")
    if source.get("verification"):
        bits.append("runtime vérifié")
    if source.get("fallback"):
        bits.append("fallback détaillé")
    return " · ".join(bits)


def _source_card(source: dict[str, Any]) -> str:
    values = "".join(
        f'<div class="metric"><span>{_e(label)}</span><strong>{value}</strong></div>'
        for label, value in _source_values(source)
    )
    status = source.get("status") or "unknown"
    return f"""
    <article class="source source-{_e(status)}">
      <div class="source-head">
        <div><h4>{_e(source.get('sensor_key') or source.get('entity_id'))}</h4>
        <small>{_e(source.get('entity_id'))}</small></div>
        <span class="pill">{_e(source.get('metric'))}</span>
      </div>
      <div class="metrics">{values}</div>
      <div class="quality">{_e(_quality_line(source))}</div>
    </article>"""


def _comparison_chart(base: Any, reference: Any, unit: str) -> str:
    try:
        b, r = float(base), float(reference)
    except (TypeError, ValueError):
        return ""
    if not (isfinite(b) and isfinite(r)):
        return ""
    scale = max(abs(b), abs(r), 1e-12)
    bw = max(1.0, min(100.0, abs(b) / scale * 100.0))
    rw = max(1.0, min(100.0, abs(r) / scale * 100.0))
    return f"""
      <div class="compare-bars" role="img" aria-label="N {_num(b, unit)}, référence {_num(r, unit)}">
        <div><span>N</span><i style="width:{bw:.2f}%"></i><b>{_num(b, unit)}</b></div>
        <div><span>Réf.</span><i class="ref" style="width:{rw:.2f}%"></i><b>{_num(r, unit)}</b></div>
      </div>"""


def _comparison_source(source: dict[str, Any]) -> str:
    status = source.get("comparison_status") or "unavailable"
    unit = source.get("unit") or ""
    rows = []
    for value in source.get("values") or []:
        relative = ""
        if value.get("relative_change_applicable") and value.get("relative_change_percent") is not None:
            relative = f" · {_signed(value.get('relative_change_percent'), '%')}"
        rows.append(f"""
          <div class="compare-value">
            <div class="compare-value-head"><strong>{_e(value.get('label'))}</strong><span>{_signed(value.get('absolute_change'), unit)}{relative}</span></div>
            {_comparison_chart(value.get('base'), value.get('reference'), unit)}
          </div>""")
    reasons = " · ".join(source.get("reasons") or [])
    return f"""
      <article class="compare-source compare-{_e(status)}">
        <div class="source-head"><div><h4>{_e(source.get('sensor_key') or source.get('entity_id'))}</h4><small>{_e(source.get('metric'))}</small></div><span class="pill">{_e(status)}</span></div>
        {''.join(rows) if rows else '<p class="muted">Aucune valeur comparable.</p>'}
        <div class="quality">{_e(reasons)}</div>
      </article>"""


def _comparisons(result: dict[str, Any]) -> str:
    comparisons = result.get("comparisons") or {}
    if not comparisons.get("enabled"):
        return ""
    blocks = []
    for target in comparisons.get("targets") or []:
        summary = target.get("summary") or {}
        catalogs = []
        for catalog in target.get("catalogs") or []:
            devices = []
            for device in catalog.get("devices") or []:
                cards = "".join(_comparison_source(s) for s in device.get("sources") or [])
                devices.append(f'<section class="device"><h3>{_e(device.get("name"))}</h3><div class="source-grid">{cards}</div></section>')
            catalogs.append(f'<section class="catalog"><h2>{_e(catalog.get("name"))}</h2>{"".join(devices)}</section>')
        blocks.append(f"""
          <section class="comparison-block">
            <div class="section-title"><div><h2>Comparaison · {_e(target.get('label'))}</h2><p>{_e((target.get('resolved_period') or {}).get('label'))}</p></div></div>
            <div class="summary mini">
              <div><span>Comparables</span><strong>{_e(summary.get('sources_comparable', 0))}</strong></div>
              <div><span>Partielles</span><strong>{_e(summary.get('sources_partial', 0))}</strong></div>
              <div><span>Reconstruites</span><strong>{_e(summary.get('sources_reconstructed', 0))}</strong></div>
              <div><span>Indisponibles</span><strong>{_e(summary.get('sources_unavailable', 0))}</strong></div>
            </div>
            {''.join(catalogs)}
          </section>""")
    return '<section class="comparisons"><h1>Comparaisons N / N-x</h1>' + "".join(blocks) + "</section>"



def _ai_analysis(result: dict[str, Any]) -> str:
    ai = result.get("ai_analysis") or {}
    if not ai.get("enabled"):
        return ""
    status = ai.get("status") or "unknown"
    if status == "completed":
        text = _e(ai.get("text") or "").replace("\n", "<br>")
        entity = ai.get("entity_id") or "entité AI Task préférée"
        duration = _num(ai.get("duration_seconds"), "s")
        return f"""
          <section class="ai-analysis ai-ok">
            <div class="section-title"><div><h1>Analyse IA</h1><p>Interprétation automatique des statistiques. Les données, graphiques et indicateurs ci-dessous constituent la référence et permettent de vérifier, nuancer ou contester cette analyse.</p></div><span class="pill">AI Task · no-thinking</span></div>
            <div class="ai-text">{text}</div>
            <div class="quality">Source : {_e(entity)} · durée {duration} · les séries brutes ne sont pas transmises au modèle.</div>
          </section>"""
    if status in {"pending", "running"}:
        label = "en cours" if status == "running" else "en attente"
        return f"""
          <section class="ai-analysis">
            <div class="section-title"><div><h1>Analyse IA</h1><p>Le rapport statistique est disponible ; l’interprétation IA est traitée séparément.</p></div><span class="pill">{label}</span></div>
            <div class="ai-text">Analyse locale en cours…</div>
          </section>"""
    error = ai.get("error") or "Analyse IA indisponible"
    return f"""
      <section class="ai-analysis ai-error">
        <div class="section-title"><div><h1>Analyse IA</h1><p>Interprétation indisponible</p></div><span class="pill">erreur</span></div>
        <div class="ai-text">{_e(error)}</div>
      </section>"""

def render_report_html(result: dict[str, Any], theme: str = "dark") -> str:
    report = result.get("report") or {}
    period = result.get("resolved_period") or {}
    execution = result.get("execution") or {}
    summary = result.get("summary") or {}
    catalogs = []
    for catalog in result.get("catalogs") or []:
        devices = []
        for device in catalog.get("devices") or []:
            info = device.get("device") or {}
            cards = "".join(_source_card(s) for s in device.get("sources") or [])
            devices.append(f"""
              <section class="device">
                <div class="device-title"><div><h3>{_e(info.get('name'))}</h3><p>{_e(info.get('category'))}</p></div><span>{_e((device.get('summary') or {}).get('sources_ok', 0))}/{_e((device.get('summary') or {}).get('sources_total', 0))} sources OK</span></div>
                <div class="source-grid">{cards}</div>
              </section>""")
        catalogs.append(f'<section class="catalog"><h2>{_e(catalog.get("name"))}</h2>{"".join(devices)}</section>')

    generated = _timestamp(execution.get("finished_at_epoch"), period.get("timezone"))
    title = report.get("name") or "Rapport Home Assistant"
    theme = "light" if str(theme).lower() == "light" else "dark"
    if theme == "light":
        palette = "--ink:#212529;--muted:#667085;--line:#cfd6df;--paper:#ffffff;--canvas:#f3f5f7;--soft:#f7f9fb;--accent:#2563eb;--ref:#7c3aed;--good:#15803d;--warn:#b45309"
        color_scheme = "light"
        source_bg = "#ffffff"
        device_bg = "#f7f9fb"
    else:
        palette = "--ink:#f2f4f7;--muted:#aeb7c2;--line:#39414b;--paper:#14191f;--canvas:#0c1015;--soft:#1a2028;--accent:#2563eb;--ref:#7c3aed;--good:#34d399;--warn:#f59e0b"
        color_scheme = "dark"
        source_bg = "#171d24"
        device_bg = "#151b22"
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(title)}</title>
<style>
:root{{{palette}}}
*{{box-sizing:border-box}}
html{{color-scheme:{color_scheme};background:var(--canvas)}}
body{{margin:0;background:var(--canvas);color:var(--ink);font:14px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.page{{max-width:1180px;margin:28px auto;background:var(--paper);padding:38px 42px;box-shadow:0 12px 40px #0008;border:1px solid #252c35}}
h1,h2,h3,h4,p{{margin-top:0}} h1{{font-size:28px;margin-bottom:6px}} h2{{font-size:20px;margin:28px 0 12px}} h3{{font-size:16px;margin:0}} h4{{font-size:12px;margin:0 0 3px;overflow-wrap:anywhere}}
.muted,.quality,small{{color:var(--muted)}}
.toolbar{{display:flex;justify-content:flex-end;margin-bottom:18px}}
button{{border:0;border-radius:8px;background:var(--accent);color:#fff;padding:9px 14px;font-weight:700;cursor:pointer}}
.hero{{border-bottom:2px solid #66717e;padding-bottom:18px;margin-bottom:20px}}
.hero-meta{{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted)}}
.summary{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:18px 0 26px}}
.summary.mini{{grid-template-columns:repeat(4,1fr)}}
.summary>div{{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:12px}}
.summary span{{display:block;color:var(--muted);font-size:11px}} .summary strong{{font-size:19px}}
.catalog{{break-inside:auto}}
.catalog>h2,.device-title,.section-title,.comparisons>h1{{break-after:avoid-page;page-break-after:avoid}}
.device{{background:{device_bg};border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0 20px;break-inside:auto}}
.device-title,.section-title{{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;margin-bottom:12px}}
.device-title p,.section-title p{{color:var(--muted);margin:2px 0 0}} .device-title>span{{color:var(--muted);font-size:11px}}
.source-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;break-inside:auto}}
.source,.compare-source{{background:{source_bg};border:1px solid var(--line);border-radius:10px;padding:12px;break-inside:avoid;page-break-inside:avoid}}
.source-head{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}}
.pill{{font-size:9px;border:1px solid #4a5562;border-radius:999px;padding:3px 7px;color:var(--muted);background:#11161c}}
.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0 8px}}
.metric span{{display:block;font-size:9px;color:var(--muted)}} .metric strong{{display:block;font-size:14px;margin-top:2px}}
.quality{{font-size:9px}} .source-error{{border-color:#ef4444}}
.comparisons{{margin-top:28px}}
.ai-analysis{{margin:8px 0 28px;border:1px solid var(--line);border-radius:12px;padding:14px;background:#151b22;break-inside:auto}}
.ai-text{{white-space:normal;background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:14px;line-height:1.6;margin-bottom:8px}}
.ai-error .ai-text{{border-color:#ef4444}}
.comparison-block{{margin-top:24px;border-top:2px solid #66717e;padding-top:20px;break-inside:auto}}
.compare-source{{margin-bottom:0}}
.compare-value{{border-top:1px solid var(--line);padding-top:9px;margin-top:9px}}
.compare-value-head{{display:flex;justify-content:space-between;gap:12px;font-size:11px}}
.compare-bars{{margin-top:7px}}
.compare-bars>div{{display:grid;grid-template-columns:32px 1fr 82px;gap:7px;align-items:center;font-size:9px;margin:4px 0}}
.compare-bars i{{display:block;height:7px;background:var(--accent);border-radius:999px;box-shadow:inset 0 0 0 99px var(--accent)}}
.compare-bars i.ref{{background:var(--ref);box-shadow:inset 0 0 0 99px var(--ref)}}
.compare-bars b{{font-weight:600;text-align:right}}
footer{{border-top:1px solid var(--line);margin-top:28px;padding-top:12px;color:var(--muted);font-size:10px}}
@media(max-width:800px){{.page{{margin:0;padding:22px}}.summary,.summary.mini{{grid-template-columns:repeat(2,1fr)}}.source-grid{{grid-template-columns:1fr}}}}
@media print{{
  @page{{size:A4;margin:10mm}}
  html,body,.page,.summary>div,.device,.source,.compare-source,.pill,.compare-bars i{{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}}
  html,body{{background:var(--canvas)!important;color:var(--ink)!important}}
  body{{font-size:10px}}
  .page{{max-width:none;margin:0;padding:0;background:var(--paper)!important;box-shadow:none;border:0}}
  .toolbar{{display:none}}
  h1{{font-size:20px}} h2{{font-size:15px}} h3{{font-size:12px}}
  .hero{{padding-bottom:10px;margin-bottom:12px}}
  .summary{{gap:5px;margin:10px 0 15px}}
  .summary>div{{padding:7px;background:var(--soft)!important}}
  .summary strong{{font-size:14px}}
  .catalog,.device,.comparison-block{{break-inside:auto;page-break-inside:auto}}
  .catalog>h2,.device-title,.section-title,.comparisons>h1{{break-after:avoid-page;page-break-after:avoid}}
  .source-grid{{gap:6px;break-inside:auto;page-break-inside:auto}}
  .source,.compare-source{{padding:8px;background:{source_bg}!important;break-inside:avoid;page-break-inside:avoid}}
  .device{{padding:10px;margin:8px 0 12px;background:#151b22!important}}
  .comparison-block{{margin-top:16px;padding-top:12px}}
  .ai-analysis{{margin:8px 0 14px;padding:10px;background:{device_bg}!important;break-inside:auto;page-break-inside:auto}}
  .ai-text{{padding:9px;background:var(--soft)!important;break-inside:auto;page-break-inside:auto}}
  .compare-bars i{{background:var(--accent)!important;box-shadow:inset 0 0 0 99px var(--accent)!important}}
  .compare-bars i.ref{{background:var(--ref)!important;box-shadow:inset 0 0 0 99px var(--ref)!important}}
  footer{{margin-top:16px}}
}}
</style></head><body><main class="page">
<div class="toolbar"><button onclick="window.print()">Imprimer / enregistrer en PDF</button></div>
<header class="hero"><h1>{_e(title)}</h1><div class="hero-meta"><span>{_e(period.get('label'))}</span><span>Fuseau {_e(period.get('timezone'))}</span><span>Généré le {_e(generated)}</span></div></header>
<section class="summary">
<div><span>Appareils</span><strong>{_e(summary.get('devices_total', 0))}</strong></div>
<div><span>Sources OK</span><strong>{_e(summary.get('sources_ok', 0))}/{_e(summary.get('sources_total', 0))}</strong></div>
<div><span>Sans données</span><strong>{_e(summary.get('sources_no_data', 0))}</strong></div>
<div><span>Erreurs / invalides</span><strong>{_e((summary.get('sources_error', 0) or 0) + (summary.get('sources_invalid', 0) or 0))}</strong></div>
<div><span>Runtimes vérifiés</span><strong>{_e(summary.get('sources_runtime_verified', 0))}</strong></div>
<div><span>Fallbacks</span><strong>{_e(summary.get('sources_fallback', 0))}</strong></div>
</section>
{_ai_analysis(result)}
{''.join(catalogs)}
{_comparisons(result)}
<footer>HA Reporting · moteur {_e(execution.get('analysis_mode'))} · calcul {_num(execution.get('data_total_duration_seconds') or execution.get('duration_seconds'), 's')}{(' · IA ' + _num(execution.get('ai_analysis_duration_seconds'), 's')) if (execution.get('ai_analysis_duration_seconds') or 0) > 0 else ''} · sémantique {_e(period.get('semantics'))}</footer>
</main></body></html>"""
    return html
