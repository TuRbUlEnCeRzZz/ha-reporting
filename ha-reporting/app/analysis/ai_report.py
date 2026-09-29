from __future__ import annotations

import json
import os
import time
from typing import Any

import websocket


HA_AI_TASK_WS_URL = "ws://supervisor/core/websocket"
AI_WS_HEARTBEAT_SECONDS = 20
AI_DEFAULT_TIMEOUT_SECONDS = 600
AI_MIN_TIMEOUT_SECONDS = 60
AI_MAX_TIMEOUT_SECONDS = 7200
AI_TARGET_CONTEXT_CHARS = 90000
AI_MAX_CONTEXT_CHARS = 220000


def _format_timeout_duration(seconds: int, language: str = "en") -> str:
    """Return a compact human-readable duration for AI timeout messages."""
    total = max(0, int(seconds or 0))
    if total < 60:
        return f"{total} s"
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    if hours and minutes:
        return f"{hours} h {minutes} min"
    if hours:
        return f"{hours} h"
    return f"{minutes} min"


def _stat_value(stats: dict[str, Any], key: str) -> Any:
    value = stats.get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


def _comparison_quality_snapshot(quality: Any) -> dict[str, Any]:
    quality = quality if isinstance(quality, dict) else {}
    return {
        "availability": quality.get("availability"),
        "source_status": quality.get("source_status"),
        "period_coverage_percent": quality.get("period_coverage_percent"),
        "sample_density_percent": quality.get("sample_density_percent"),
        "counter_mode": quality.get("counter_mode"),
        "warnings": quality.get("warnings") or [],
    }


def _comparison_interpretation(source: dict[str, Any]) -> dict[str, Any]:
    status = source.get("comparison_status")
    base_quality = _comparison_quality_snapshot(source.get("base_quality"))
    reference_quality = _comparison_quality_snapshot(source.get("reference_quality"))
    base_coverage = base_quality.get("period_coverage_percent")
    reference_coverage = reference_quality.get("period_coverage_percent")

    base_coverage_limited = isinstance(base_coverage, (int, float)) and base_coverage < 80.0
    reference_coverage_limited = isinstance(reference_coverage, (int, float)) and reference_coverage < 80.0
    coverage_limited = base_coverage_limited or reference_coverage_limited
    base_reconstructed = str(base_quality.get("counter_mode") or "") in {
        "provider_reconstructed",
        "reconstructed",
    }
    reference_reconstructed = str(reference_quality.get("counter_mode") or "") in {
        "provider_reconstructed",
        "reconstructed",
    }
    full_period_change_supported = bool(status == "comparable" and not coverage_limited)

    if status == "unavailable":
        wording_policy = "no_change_claim"
    elif full_period_change_supported:
        wording_policy = "full_period_change_allowed"
    else:
        wording_policy = "descriptive_gap_only"

    return {
        "status": status,
        "coverage_limited": coverage_limited,
        "base_coverage_limited": base_coverage_limited,
        "reference_coverage_limited": reference_coverage_limited,
        "base_reconstructed": base_reconstructed,
        "reference_reconstructed": reference_reconstructed,
        "full_period_change_supported": full_period_change_supported,
        "wording_policy": wording_policy,
    }


def compact_report_context(result: dict[str, Any]) -> dict[str, Any]:
    """Build a bounded, structured context for AI interpretation.

    Raw samples, previews, provider internals and verification traces are deliberately
    excluded. The model receives only statistics and quality/comparison metadata that
    HA Reporting has already computed.
    """

    output: dict[str, Any] = {
        "report": {
            "name": (result.get("report") or {}).get("name"),
            "period": (result.get("resolved_period") or {}).get("label"),
            "timezone": (result.get("resolved_period") or {}).get("timezone"),
        },
        "summary": result.get("summary") or {},
        "catalogs": [],
        "comparisons": [],
    }

    for catalog in result.get("catalogs") or []:
        cat_out = {"name": catalog.get("name"), "devices": []}
        for device in catalog.get("devices") or []:
            info = device.get("device") or {}
            dev_out = {
                "name": info.get("name"),
                "category": info.get("category"),
                "sources": [],
            }
            for source in device.get("sources") or []:
                analysis = source.get("analysis") or {}
                stats = analysis.get("statistics") or {}
                quality = analysis.get("quality") or {}
                metric = source.get("metric")
                values: dict[str, Any] = {}

                if metric == "power":
                    values = {
                        "max": _stat_value(stats, "max"),
                        "p95": stats.get("p95"),
                        "mean": stats.get("mean"),
                    }
                    if source.get("derive_energy") and stats.get("integrated_energy_kwh") is not None:
                        values["integrated_energy_kwh"] = stats.get("integrated_energy_kwh")
                elif metric in {"temperature", "humidity", "voltage", "current", "energy_measurement"}:
                    values = {
                        "min": _stat_value(stats, "min"),
                        "mean": stats.get("mean"),
                        "max": _stat_value(stats, "max"),
                    }
                elif metric in {"energy_total", "runtime", "cycles"}:
                    values = {
                        "delta": stats.get("delta"),
                        "last": _stat_value(stats, "last"),
                    }
                    # A zero-reset diagnostic is an implementation detail, not
                    # a user-facing finding. Only transmit it when a reset
                    # actually affected the interpretation.
                    if int(stats.get("resets_detected", 0) or 0) > 0:
                        values["resets_detected"] = int(stats.get("resets_detected", 0) or 0)
                else:
                    values = {
                        "first": _stat_value(stats, "first"),
                        "last": _stat_value(stats, "last"),
                        "mean": stats.get("mean"),
                    }

                dev_out["sources"].append(
                    {
                        "name": source.get("sensor_key") or source.get("entity_id"),
                        "metric": metric,
                        "unit": source.get("unit"),
                        "status": source.get("status"),
                        "values": values,
                        "quality": {
                            "period_coverage_percent": quality.get("period_coverage_percent"),
                            "sample_density_percent": quality.get("sample_density_percent"),
                            "density_applicable": quality.get("density_applicable"),
                        },
                        "runtime_verified": bool(source.get("verification")),
                        "warnings": (analysis.get("validation") or {}).get("warnings") or [],
                    }
                )
            cat_out["devices"].append(dev_out)
        output["catalogs"].append(cat_out)

    comparisons = result.get("comparisons") or {}
    for target in comparisons.get("targets") or []:
        target_out = {
            "label": target.get("label"),
            "period": (target.get("resolved_period") or {}).get("label"),
            "summary": target.get("summary") or {},
            "catalogs": [],
        }
        for catalog in target.get("catalogs") or []:
            cat_out = {"name": catalog.get("name"), "devices": []}
            for device in catalog.get("devices") or []:
                dev_out = {"name": device.get("name"), "sources": []}
                for source in device.get("sources") or []:
                    dev_out["sources"].append(
                        {
                            "name": source.get("sensor_key") or source.get("entity_id"),
                            "metric": source.get("metric"),
                            "unit": source.get("unit"),
                            "status": source.get("comparison_status"),
                            "reasons": source.get("reasons") or [],
                            "base_quality": _comparison_quality_snapshot(source.get("base_quality")),
                            "reference_quality": _comparison_quality_snapshot(source.get("reference_quality")),
                            "interpretation": _comparison_interpretation(source),
                            "values": source.get("values") or [],
                        }
                    )
                cat_out["devices"].append(dev_out)
            target_out["catalogs"].append(cat_out)
        output["comparisons"].append(target_out)

    return output



def _compact_comparison_values(values: Any) -> list[dict[str, Any]]:
    """Keep only comparison values that are useful to the language model."""
    output: list[dict[str, Any]] = []
    for item in values or []:
        if not isinstance(item, dict):
            continue
        compact: dict[str, Any] = {
            "stat": item.get("key") or item.get("label"),
            "base": item.get("base"),
            "reference": item.get("reference"),
            "gap": item.get("absolute_change"),
        }
        if item.get("relative_change_applicable") and item.get("relative_change_percent") is not None:
            compact["gap_pct"] = item.get("relative_change_percent")
        output.append({key: value for key, value in compact.items() if value is not None})
    return output


def _pool_value(context: dict[str, Any], indexes: dict[str, dict[str, int]], key: str, value: Any) -> int | None:
    """Store a repeated semantic value once and return its array index.

    Values are keyed by their canonical JSON representation so strings, lists and
    dictionaries keep their original JSON value instead of being coerced to text.
    """
    if value is None:
        return None
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    index = indexes.setdefault(key, {})
    if encoded not in index:
        index[encoded] = len(context[key])
        context[key].append(value)
    return index[encoded]


def _trim_trailing_none(row: list[Any]) -> list[Any]:
    """Remove only optional trailing nulls; positional meaning is preserved by the legend."""
    while row and row[-1] is None:
        row.pop()
    return row


def _current_value_vector(metric: Any, stats: dict[str, Any]) -> list[Any]:
    """Return deterministic statistics in the metric-specific v3 column order."""
    if metric == "power":
        return [_stat_value(stats, "max"), stats.get("p95"), stats.get("mean")]
    if metric == "temperature":
        return [_stat_value(stats, "min"), stats.get("mean"), _stat_value(stats, "max")]
    if metric in {"energy_total", "runtime", "cycles"}:
        return [stats.get("delta"), _stat_value(stats, "last"), int(stats.get("resets_detected", 0) or 0)]
    return [_stat_value(stats, "first"), _stat_value(stats, "last"), stats.get("mean")]


def _lossless_ai_context_v3(result: dict[str, Any]) -> dict[str, Any]:
    """Build the beta.22 lossless normalized semantic context.

    The representation removes structural repetition by using array-index IDs,
    registries and positional rows. It does not remove current-period sources or
    comparison sources, including entries with partial coverage. Raw samples,
    previews and provider traces remain intentionally outside the AI contract.
    """
    context: dict[str, Any] = {
        "schema": "ha-reporting-ai-context-v3",
        "lossless": True,
        "legend": {
            "ids": "array indexes",
            "device": ["catalog_id", "name", "category_id"],
            "source": ["device_id", "name", "metric_id", "unit_id"],
            "current": ["source_id", "values", "coverage_pct", "density_pct", "status_id?", "flags?", "warning_ids?"],
            "comparison": ["target_id", "source_id", "base_coverage_pct", "reference_coverage_pct", "values", "status_id?", "policy_id?", "flags?", "reason_ids?"],
            "comparison_value": ["stat_id", "base", "reference", "absolute_change", "relative_change_percent?", "relative_change_applicable_override?"],
            "value_schemas": {
                "power": ["max", "p95", "mean"],
                "temperature": ["min", "mean", "max"],
                "counter": ["delta", "last", "resets_detected"],
                "generic": ["first", "last", "mean"],
            },
            "metric_value_schema": {
                "power": "power",
                "temperature": "temperature",
                "energy_total": "counter",
                "runtime": "counter",
                "cycles": "counter",
                "*": "generic",
            },
            "flags": {
                "v": "runtime_verified",
                "n": "density_not_applicable",
                "b": "base_reconstructed",
                "r": "reference_reconstructed",
            },
            "defaults": {
                "current_status": "ok",
                "comparison_status": "comparable",
                "comparison_policy": "full_period_change_allowed",
                "relative_change_applicable": "false when percent is absent; true when percent is present; optional override 0/1 preserves exceptional cases",
            },
        },
        "report": [
            (result.get("report") or {}).get("name"),
            (result.get("resolved_period") or {}).get("label"),
            (result.get("resolved_period") or {}).get("timezone"),
        ],
        "summary": result.get("summary") or {},
        "catalogs": [],
        "categories": [],
        "metrics": [],
        "units": [],
        "statuses": [],
        "policies": [],
        "stats": [],
        "devices": [],
        "sources": [],
        "warnings": [],
        "reasons": [],
        "targets": [],
        "current": [],
        "comparisons": [],
    }

    pools: dict[str, dict[str, int]] = {}
    catalog_ids: dict[str, int] = {}
    device_ids: dict[tuple[int, str], int] = {}
    source_ids: dict[tuple[int, str, str, str], int] = {}

    def catalog_id(name: Any) -> int:
        key = json.dumps(name, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if key not in catalog_ids:
            catalog_ids[key] = len(context["catalogs"])
            context["catalogs"].append(name)
        return catalog_ids[key]

    def device_id(catalog: int, name: Any, category: Any = None) -> int:
        name_key = json.dumps(name, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        key = (catalog, name_key)
        if key not in device_ids:
            device_ids[key] = len(context["devices"])
            context["devices"].append([
                catalog,
                name,
                _pool_value(context, pools, "categories", category),
            ])
        elif category is not None and context["devices"][device_ids[key]][2] is None:
            context["devices"][device_ids[key]][2] = _pool_value(context, pools, "categories", category)
        return device_ids[key]

    def source_id(device: int, name: Any, metric: Any, unit: Any) -> int:
        key = (
            device,
            json.dumps(name, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            json.dumps(metric, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            json.dumps(unit, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
        if key not in source_ids:
            source_ids[key] = len(context["sources"])
            context["sources"].append([
                device,
                name,
                _pool_value(context, pools, "metrics", metric),
                _pool_value(context, pools, "units", unit),
            ])
        return source_ids[key]

    for catalog in result.get("catalogs") or []:
        cid = catalog_id(catalog.get("name"))
        for device in catalog.get("devices") or []:
            info = device.get("device") or {}
            did = device_id(cid, info.get("name"), info.get("category"))
            for source in device.get("sources") or []:
                sid = source_id(
                    did,
                    source.get("sensor_key") or source.get("entity_id"),
                    source.get("metric"),
                    source.get("unit"),
                )
                analysis = source.get("analysis") or {}
                stats = analysis.get("statistics") or {}
                quality = analysis.get("quality") or {}
                validation = analysis.get("validation") or {}

                density_applicable = bool(quality.get("density_applicable"))
                row: list[Any] = [
                    sid,
                    _current_value_vector(source.get("metric"), stats),
                    quality.get("period_coverage_percent"),
                    quality.get("sample_density_percent") if density_applicable else None,
                ]

                status = source.get("status")
                status_id = None if not status or status == "ok" else _pool_value(context, pools, "statuses", status)
                flags = ""
                if source.get("verification"):
                    flags += "v"
                if not density_applicable:
                    flags += "n"
                warning_ids = [
                    _pool_value(context, pools, "warnings", warning)
                    for warning in (validation.get("warnings") or [])
                ]
                row.extend([status_id, flags or None, warning_ids or None])
                context["current"].append(_trim_trailing_none(row))

    comparisons = result.get("comparisons") or {}
    for target in comparisons.get("targets") or []:
        tid = len(context["targets"])
        context["targets"].append([
            target.get("label"),
            (target.get("resolved_period") or {}).get("label"),
            target.get("summary") or {},
        ])
        for catalog in target.get("catalogs") or []:
            cid = catalog_id(catalog.get("name"))
            for device in catalog.get("devices") or []:
                did = device_id(cid, device.get("name"))
                for source in device.get("sources") or []:
                    sid = source_id(
                        did,
                        source.get("sensor_key") or source.get("entity_id"),
                        source.get("metric"),
                        source.get("unit"),
                    )
                    interpretation = _comparison_interpretation(source)
                    base_quality = source.get("base_quality") or {}
                    reference_quality = source.get("reference_quality") or {}
                    values: list[list[Any]] = []
                    for item in source.get("values") or []:
                        if not isinstance(item, dict):
                            continue
                        relative_applicable = bool(item.get("relative_change_applicable"))
                        relative_percent = item.get("relative_change_percent")
                        value_row: list[Any] = [
                            _pool_value(context, pools, "stats", item.get("key") or item.get("label")),
                            item.get("base"),
                            item.get("reference"),
                            item.get("absolute_change"),
                        ]
                        if relative_percent is not None:
                            value_row.append(relative_percent)
                            if not relative_applicable:
                                value_row.append(0)
                        elif relative_applicable:
                            value_row.extend([None, 1])
                        values.append(value_row)

                    comparison_status = source.get("comparison_status")
                    policy = interpretation.get("wording_policy")
                    status_id = None if comparison_status == "comparable" else _pool_value(context, pools, "statuses", comparison_status)
                    policy_id = None if policy == "full_period_change_allowed" else _pool_value(context, pools, "policies", policy)
                    flags = ""
                    if interpretation.get("base_reconstructed"):
                        flags += "b"
                    if interpretation.get("reference_reconstructed"):
                        flags += "r"
                    reason_ids = [
                        _pool_value(context, pools, "reasons", reason)
                        for reason in (source.get("reasons") or [])
                    ]
                    row = [
                        tid,
                        sid,
                        base_quality.get("period_coverage_percent"),
                        reference_quality.get("period_coverage_percent"),
                        values,
                        status_id,
                        policy_id,
                        flags or None,
                        reason_ids or None,
                    ]
                    context["comparisons"].append(_trim_trailing_none(row))

    return context


def _lossless_ai_context_v4(result: dict[str, Any]) -> dict[str, Any]:
    """Build a lossless, self-describing AI context.

    beta.24 deliberately trades a little structural compression for semantic
    clarity. Each source carries its readable source name and named statistics,
    so a small local model never has to decode positional arrays or join metric
    schemas to values. No current or comparison source is omitted, including
    partial sources. Raw samples and provider traces remain outside the AI
    contract because they are not report statistics.
    """
    context: dict[str, Any] = {
        "schema": "ha-reporting-ai-context-v4",
        "lossless": True,
        "semantics": {
            "period_delta": "change during the report period",
            "counter_end": "cumulative counter reading at period end; never a period delta",
            "integrated_energy_kwh": "energy obtained by integrating the power source over the report period",
            "max": "maximum",
            "p95": "95th percentile",
            "mean": "time-weighted mean for power when available",
            "coverage_pct": "period coverage",
            "density_pct": "sampling density when applicable",
        },
        "report": {
            "name": (result.get("report") or {}).get("name"),
            "period": (result.get("resolved_period") or {}).get("label"),
            "timezone": (result.get("resolved_period") or {}).get("timezone"),
        },
        "summary": result.get("summary") or {},
        "current": [],
        "comparisons": [],
    }

    for catalog in result.get("catalogs") or []:
        catalog_name = catalog.get("name")
        for device in catalog.get("devices") or []:
            info = device.get("device") or {}
            device_name = info.get("name")
            category = info.get("category")
            for source in device.get("sources") or []:
                analysis = source.get("analysis") or {}
                stats = analysis.get("statistics") or {}
                quality = analysis.get("quality") or {}
                validation = analysis.get("validation") or {}
                metric = source.get("metric")
                values: dict[str, Any] = {}

                if metric == "power":
                    values = {
                        "max": _stat_value(stats, "max"),
                        "p95": stats.get("p95"),
                        "mean": stats.get("mean"),
                    }
                    if source.get("derive_energy") and stats.get("integrated_energy_kwh") is not None:
                        values["integrated_energy_kwh"] = stats.get("integrated_energy_kwh")
                elif metric in {"temperature", "humidity", "voltage", "current", "energy_measurement"}:
                    values = {
                        "first": _stat_value(stats, "first"),
                        "min": _stat_value(stats, "min"),
                        "mean": stats.get("mean"),
                        "max": _stat_value(stats, "max"),
                        "last": _stat_value(stats, "last"),
                    }
                elif metric in {"energy_total", "runtime", "cycles"}:
                    values = {
                        "period_delta": stats.get("delta"),
                        "counter_end": _stat_value(stats, "last"),
                    }
                    if int(stats.get("resets_detected", 0) or 0) > 0:
                        values["resets_detected"] = int(stats.get("resets_detected", 0) or 0)
                else:
                    values = {
                        "first": _stat_value(stats, "first"),
                        "last": _stat_value(stats, "last"),
                        "mean": stats.get("mean"),
                    }

                source_name = source.get("sensor_key") or source.get("entity_id")
                source_path = "/".join(
                    str(part) for part in (catalog_name, device_name, source_name) if part not in (None, "")
                )
                row: dict[str, Any] = {
                    "source": source_path,
                    "metric": metric,
                    "unit": source.get("unit"),
                    "values": values,
                    "coverage_pct": quality.get("period_coverage_percent"),
                }
                if quality.get("density_applicable"):
                    row["density_pct"] = quality.get("sample_density_percent")
                status = source.get("status")
                if status and status != "ok":
                    row["status"] = status
                if source.get("verification"):
                    row["runtime_verified"] = True
                warnings = validation.get("warnings") or []
                if warnings:
                    row["warnings"] = warnings
                context["current"].append(row)

    comparisons = result.get("comparisons") or {}
    for target in comparisons.get("targets") or []:
        target_label = target.get("label")
        target_period = (target.get("resolved_period") or {}).get("label")
        for catalog in target.get("catalogs") or []:
            catalog_name = catalog.get("name")
            for device in catalog.get("devices") or []:
                device_name = device.get("name")
                for source in device.get("sources") or []:
                    interpretation = _comparison_interpretation(source)
                    base_quality = source.get("base_quality") or {}
                    reference_quality = source.get("reference_quality") or {}
                    values: dict[str, Any] = {}
                    for item in source.get("values") or []:
                        if not isinstance(item, dict):
                            continue
                        stat = str(item.get("key") or item.get("label") or "value")
                        stat_values: dict[str, Any] = {
                            "base": item.get("base"),
                            "reference": item.get("reference"),
                            "gap": item.get("absolute_change"),
                        }
                        if item.get("relative_change_percent") is not None:
                            stat_values["gap_pct"] = item.get("relative_change_percent")
                            stat_values["gap_pct_applicable"] = bool(item.get("relative_change_applicable"))
                        values[stat] = stat_values

                    source_name = source.get("sensor_key") or source.get("entity_id")
                    source_path = "/".join(
                        str(part) for part in (catalog_name, device_name, source_name) if part not in (None, "")
                    )
                    row = {
                        "target": target_label,
                        "target_period": target_period,
                        "source": source_path,
                        "metric": source.get("metric"),
                        "unit": source.get("unit"),
                        "base_coverage_pct": base_quality.get("period_coverage_percent"),
                        "reference_coverage_pct": reference_quality.get("period_coverage_percent"),
                        "policy": interpretation.get("wording_policy"),
                        "values": values,
                    }
                    comparison_status = source.get("comparison_status")
                    if comparison_status and comparison_status != "comparable":
                        row["status"] = comparison_status
                    if interpretation.get("base_reconstructed"):
                        row["base_reconstructed"] = True
                    if interpretation.get("reference_reconstructed"):
                        row["reference_reconstructed"] = True
                    reasons = source.get("reasons") or []
                    if reasons:
                        row["reasons"] = reasons
                    context["comparisons"].append(row)

    return context


def _encoded_context(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))


def build_budgeted_ai_context(
    result: dict[str, Any],
    target_chars: int = AI_TARGET_CONTEXT_CHARS,
) -> tuple[str, dict[str, Any]]:
    """Return the complete semantic AI context using self-describing normalization.

    beta.24 keeps every current and comparison source, including partial entries.
    Named statistics replace positional value arrays so small local models do not
    need to decode max/p95/mean or counter semantics. The hard limit is enforced
    by the caller; when the lossless context cannot fit, analysis fails explicitly
    instead of silently omitting data.
    """
    legacy_json = _encoded_context(compact_report_context(result))
    context = _lossless_ai_context_v4(result)
    context_json = _encoded_context(context)
    metadata = {
        "schema": context.get("schema"),
        "mode": "lossless_self_describing",
        "lossless": True,
        "characters": len(context_json),
        "target_characters": target_chars,
        "limit_characters": AI_MAX_CONTEXT_CHARS,
        "legacy_characters": len(legacy_json),
        "full_compact_characters": len(context_json),
        "omitted_current_sources": 0,
        "omitted_comparison_sources": 0,
        "current_sources": len(context.get("current") or []),
        "comparison_sources": len(context.get("comparisons") or []),
    }
    return context_json, metadata

def _extract_ai_task_payload(payload: Any) -> tuple[Any, str | None]:
    """Extract ai_task.generate_data data from direct or entity-namespaced payloads."""
    if not isinstance(payload, dict):
        raise RuntimeError("Réponse AI Task absente")

    if "data" in payload:
        return payload.get("data"), payload.get("conversation_id")

    for value in payload.values():
        if isinstance(value, dict) and "data" in value:
            return value.get("data"), value.get("conversation_id")

    raise RuntimeError("AI Task n'a retourné aucune donnée")


def _extract_service_response(payload: Any) -> tuple[Any, str | None]:
    """Backward-compatible extractor for REST response shapes."""
    if not isinstance(payload, dict):
        raise RuntimeError("Réponse Home Assistant AI Task invalide")
    return _extract_ai_task_payload(payload.get("service_response", payload))


def _recv_json(ws) -> dict[str, Any]:
    raw = ws.recv()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    message = json.loads(raw)
    if not isinstance(message, dict):
        raise RuntimeError("Message WebSocket Home Assistant invalide")
    return message


def _websocket_error_message(message: dict[str, Any]) -> str:
    error = message.get("error") or {}
    if isinstance(error, dict):
        code = error.get("code")
        text = error.get("message")
        if code and text:
            return f"{code}: {text}"
        return str(text or code or error)
    return str(error or "Erreur WebSocket Home Assistant")

def _sanitize_ai_text(text: str, language: str = "fr") -> str:
    """Remove contradictory boilerplate without rewriting the AI meaning."""
    language = "en" if str(language).lower() == "en" else "fr"
    heading = "RECOMMENDATIONS" if language == "en" else "RECOMMANDATIONS"
    empty_recommendation = (
        "- no specific recommendation."
        if language == "en"
        else "- aucune recommandation particulière."
    )
    lines = str(text or "").splitlines()
    recommendation_index = next(
        (i for i, line in enumerate(lines) if line.strip().upper() == heading),
        None,
    )
    if recommendation_index is None:
        return str(text or "").strip()

    recommendation_lines = lines[recommendation_index + 1 :]
    substantive_bullets = [
        line
        for line in recommendation_lines
        if line.strip().startswith("-")
        and line.strip().lower() != empty_recommendation
    ]
    if substantive_bullets:
        lines = [
            line
            for i, line in enumerate(lines)
            if not (
                i > recommendation_index
                and line.strip().lower() == empty_recommendation
            )
        ]
    return "\n".join(lines).strip()


def _instructions(context_json: str, language: str = "fr") -> str:
    language = "en" if str(language).lower() == "en" else "fr"
    if language == "en":
        return f"""You are analyzing a home-automation report calculated by HA Reporting.
Answer directly and concisely in English without exposing internal reasoning.
Do not invent or recalculate values: use only the supplied statistics.
Clearly distinguish calculated facts from interpretation. Ignore technical identifiers when a readable name is available.
Do not turn internal engine diagnostics into attention points. In particular, never mention that a value was not reconstructed, that no reset occurred, or that no fallback was used. Mention a reset/reconstruction only when it actually occurred and materially affects reliability or interpretation.

Mandatory rules for N/N-x comparisons:
- An `unavailable` source does not support any conclusion about change.
- Read `policy` first for each compared source.
- If `policy` is `descriptive_gap_only` or `no_change_claim`, do NOT state that a quantity increased, decreased, went up, went down, or use equivalent wording that presents the gap as a real full-period trend.
- Instead use wording such as: “for the available data, the calculated gap is ...” or “the calculated value is higher/lower by ...”, then explain why the gap cannot be interpreted as a complete-period trend.
- Forbidden example: “consumption increased by 182%”. Expected style: “for the available data, the calculated gap is +182%, but it does not support a conclusion that annual consumption rose by that amount because the reference covers only 34.8% of the period”.
- Forbidden example: “average power is down 8.6% from the previous year”. Expected style: “for the available data, calculated average power is 8.6% lower, but the comparison remains partial”.
- Never use a relative percentage from an incomplete comparison to assert drift, overconsumption, or improvement.
- Keep reconstruction and coverage strictly separate: `base_reconstructed=true` means N was reconstructed after one or more resets; `reference_coverage_pct` independently describes N-x reference coverage. Never merge these concepts into wording such as “partial reconstruction”.
- If `base_reconstructed` is true, mention reconstruction only if useful to reliability. If absent/false, do not discuss resets or reconstruction. If `reference_coverage_pct` is below 80, separately state that the historical reference is partial and include its coverage. Do not claim the reference is reconstructed unless `reference_reconstructed` is true.
- `ha-reporting-ai-context-v4` is lossless and self-describing. Every current/comparison source is a complete named record; no source is omitted, including partially covered sources. Never swap values between records or reinterpret named fields.
- For power, `max`, `p95`, and `mean` are authoritative named fields. Never treat `max` as `mean` or `mean` as `max`. `integrated_energy_kwh`, when present, is the period energy derived from that exact power source.
- For cumulative counters, `period_delta` is the period change/consumption. `counter_end` is only the cumulative meter reading at the end and must NEVER be presented as a period delta or period consumption.
- `energy_measurement` is a gauge-like energy measurement, not a cumulative counter. Do not infer a consumption delta from it unless an explicit comparison value says so.
- Preserve source semantics: a source whose name contains `forecast` / `prevision` is a forecast, not a measured value. Do not call forecast power measured power.
- Recommendations based only on a partial/reconstructed comparison must remain proportionate: prefer monitoring, continuing data collection, or checking again once coverage is sufficient. Do not ask the user to investigate causes unless current-period data independently supports a concrete anomaly.

Produce exactly these three plain-text sections:
SUMMARY
2 to 4 sentences on the main facts of the period. Current-period facts may be stated directly; incomplete comparisons must follow the rules above.

ATTENTION POINTS
0 to 5 bullets beginning with "- ". Mention only items supported by the data, including coverage limitations when they affect interpretation. Write "- No notable attention point." when appropriate.

RECOMMENDATIONS
0 to 4 bullets beginning with "- ". Stay cautious and concrete. Do not invent a fault diagnosis.
Write "- No specific recommendation." only when there is no other recommendation. Never combine that sentence with other bullets.

Validated structured data from HA Reporting:
{context_json}
"""

    return f"""Tu analyses un rapport domotique calculé par HA Reporting.
Réponds directement et brièvement en français, sans afficher de raisonnement interne.
N'invente aucun chiffre et ne recalcule pas les données : utilise exclusivement les statistiques fournies.
Distingue clairement un fait calculé d'une interprétation. Ignore les identifiants techniques lorsqu'un nom lisible est disponible.
Ne transforme pas les diagnostics internes du moteur en points d'attention. En particulier, ne mentionne jamais qu'une valeur « n'a pas été reconstruite », qu'aucun reset n'a eu lieu, ni l'absence d'un fallback. Mentionne un reset/reconstruction uniquement s'il s'est réellement produit et s'il affecte la fiabilité ou l'interprétation de la valeur.

Règles impératives pour les comparaisons N/N-x :
- Une source `unavailable` ne permet aucune conclusion d'évolution.
- Lis d'abord `policy` pour chaque source comparée.
- Si `policy` vaut `descriptive_gap_only` ou `no_change_claim`, il est INTERDIT d'écrire qu'une grandeur « a augmenté », « a diminué », « est en hausse », « est en baisse » ou toute formulation équivalente qui présente l'écart comme une évolution réelle de la période complète.
- Dans ce cas, écris plutôt : « sur les données disponibles, l'écart calculé est de ... », « la valeur calculée est supérieure/inférieure de ... », puis précise pourquoi cet écart n'est pas directement interprétable comme une évolution complète.
- Exemple interdit : « la consommation a augmenté de 182 % ». Exemple attendu : « sur les données disponibles, l'écart calculé est de +182 %, mais il ne permet pas de conclure à une hausse annuelle de cette ampleur car la référence ne couvre que 34,8 % de la période ».
- Exemple interdit : « la puissance moyenne est en baisse de 8,6 % par rapport à l'année précédente ». Exemple attendu : « sur les données disponibles, la puissance moyenne calculée est inférieure de 8,6 %, mais la comparaison reste partielle ».
- N'utilise jamais un pourcentage relatif issu d'une comparaison incomplète pour affirmer une dérive, une surconsommation ou une amélioration.
- Distingue strictement reconstruction et couverture : `base_reconstructed=true` signifie que la valeur N a été reconstruite après un ou plusieurs resets ; `reference_coverage_pct` décrit séparément la couverture de la référence N-x. Ne fusionne jamais ces deux notions dans une expression comme « reconstruction partielle ».
- Si `base_reconstructed` vaut true, tu peux signaler la reconstruction uniquement si elle est utile à la fiabilité de l'analyse. Si elle est absente/false, ne parle jamais de reset ou de reconstruction. Si `reference_coverage_pct` est inférieur à 80, dis séparément « la référence historique est partielle » avec sa couverture. N'affirme pas que la référence est reconstruite sauf si `reference_reconstructed` vaut true.
- `ha-reporting-ai-context-v4` est une représentation sans omission et auto-descriptive. Chaque source courante/comparée est un enregistrement complet avec des champs nommés ; aucune source n'est retirée, y compris lorsqu'elle ne couvre qu'une partie de la période. N'échange jamais des valeurs entre deux enregistrements et ne réinterprète pas les noms de champs.
- Pour une puissance, `max`, `p95` et `mean` sont des champs nommés faisant foi. Ne transforme jamais `max` en moyenne ni `mean` en maximum. `integrated_energy_kwh`, lorsqu'il existe, est l'énergie de la période dérivée exactement de cette source de puissance.
- Pour un compteur cumulatif, `period_delta` est la variation/consommation de la période. `counter_end` est uniquement l'index cumulé en fin de période et ne doit JAMAIS être présenté comme un delta ou une consommation de période.
- `energy_measurement` est une mesure d'énergie de type jauge, pas un compteur cumulatif. N'en déduis pas une consommation par différence sauf si une comparaison explicite le fournit.
- Respecte la sémantique du nom de source : une source contenant `forecast` / `prevision` est une prévision, pas une mesure réelle. Ne qualifie pas une puissance prévisionnelle de puissance mesurée.
- Une recommandation fondée seulement sur une comparaison partielle/reconstruite doit rester proportionnée : privilégie « surveiller », « poursuivre la collecte » ou « recontrôler quand la couverture sera suffisante ». Ne demande pas d'en rechercher les causes sauf si les données de la période courante montrent, indépendamment de la comparaison, une anomalie étayée.

Produis exactement ces trois sections, en texte simple :
SYNTHÈSE
2 à 4 phrases sur les faits principaux de la période. Les faits de la période courante peuvent être formulés directement ; les comparaisons incomplètes doivent suivre les règles ci-dessus.

POINTS D'ATTENTION
0 à 5 puces commençant par "- ". Ne signale que des éléments réellement étayés par les données, y compris les limites de couverture si elles affectent l'interprétation. Écris "- Aucun point d'attention notable." si nécessaire.

RECOMMANDATIONS
0 à 4 puces commençant par "- ". Reste prudent et concret. N'invente pas de diagnostic de panne.
Écris "- Aucune recommandation particulière." uniquement s'il n'y a aucune autre recommandation. Ne combine jamais cette phrase avec d'autres puces.

Données structurées validées par HA Reporting :
{context_json}
"""


def analyze_report_with_ai(
    result: dict[str, Any],
    config: dict[str, Any] | None,
    token: str | None = None,
) -> dict[str, Any]:
    config = config or {}
    language = "en" if str((result.get("report") or {}).get("language") or "fr").lower() == "en" else "fr"
    if not bool(config.get("enabled")):
        return {"enabled": False, "status": "disabled"}

    token = token if token is not None else os.environ.get("SUPERVISOR_TOKEN", "")
    entity_id = str(config.get("entity_id") or "").strip()
    try:
        timeout_seconds = int(config.get("timeout_seconds", AI_DEFAULT_TIMEOUT_SECONDS) or AI_DEFAULT_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        timeout_seconds = AI_DEFAULT_TIMEOUT_SECONDS
    timeout_seconds = max(AI_MIN_TIMEOUT_SECONDS, min(AI_MAX_TIMEOUT_SECONDS, timeout_seconds))
    started = time.time()

    base = {
        "enabled": True,
        "status": "error",
        "entity_id": entity_id or None,
        "mode": "no_thinking_expected",
        "mode_control": "ai_task_entity_configuration",
        "timeout_seconds": timeout_seconds,
        "transport": "home_assistant_websocket",
        "websocket_url": HA_AI_TASK_WS_URL,
        "heartbeat_interval_seconds": AI_WS_HEARTBEAT_SECONDS,
        "started_at_epoch": started,
    }

    if not token:
        return {
            **base,
            "finished_at_epoch": time.time(),
            "error": "SUPERVISOR_TOKEN indisponible pour appeler AI Task",
        }

    ws = None
    try:
        context_json, context_meta = build_budgeted_ai_context(result)
        if len(context_json) > AI_MAX_CONTEXT_CHARS:
            if language == "en":
                message = f"Lossless AI context remains too large after normalization ({len(context_json)} characters, limit {AI_MAX_CONTEXT_CHARS})"
            else:
                message = f"Contexte IA sans omission encore trop volumineux après normalisation ({len(context_json)} caractères, limite {AI_MAX_CONTEXT_CHARS})"
            raise RuntimeError(message)

        service_data: dict[str, Any] = {
            "task_name": f"HA Reporting · {(result.get('report') or {}).get('name') or 'rapport'}",
            "instructions": _instructions(context_json, language),
        }
        if entity_id:
            service_data["entity_id"] = entity_id

        # The Supervisor exposes Home Assistant's WebSocket API at this internal URL.
        # Keep the connect timeout short; the configured AI timeout applies to the service call itself.
        connect_timeout = min(30, max(5, timeout_seconds))
        ws = websocket.create_connection(
            HA_AI_TASK_WS_URL,
            timeout=connect_timeout,
            http_proxy_host=None,
            http_proxy_port=None,
        )

        auth_required = _recv_json(ws)
        if auth_required.get("type") != "auth_required":
            raise RuntimeError(f"Handshake WebSocket inattendu: {auth_required.get('type')}")

        ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth_result = _recv_json(ws)
        if auth_result.get("type") != "auth_ok":
            if auth_result.get("type") == "auth_invalid":
                raise RuntimeError(f"Authentification WebSocket refusée: {auth_result.get('message') or 'token invalide'}")
            raise RuntimeError(f"Authentification WebSocket inattendue: {auth_result.get('type')}")

        command_id = 1
        next_id = 2
        ws.send(
            json.dumps(
                {
                    "id": command_id,
                    "type": "call_service",
                    "domain": "ai_task",
                    "service": "generate_data",
                    "service_data": service_data,
                    "return_response": True,
                },
                ensure_ascii=False,
            )
        )

        deadline = time.monotonic() + timeout_seconds
        heartbeat_count = 0
        response_payload = None

        while response_payload is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timeout_label = _format_timeout_duration(timeout_seconds, language)
                if language == "en":
                    raise TimeoutError(f"AI analysis stopped after {timeout_label} (configured maximum timeout).")
                raise TimeoutError(f"Analyse IA interrompue après {timeout_label} (délai maximal configuré).")

            ws.settimeout(min(AI_WS_HEARTBEAT_SECONDS, max(1, remaining)))
            try:
                message = _recv_json(ws)
            except websocket.WebSocketTimeoutException:
                ping_id = next_id
                next_id += 1
                heartbeat_count += 1
                ws.send(json.dumps({"id": ping_id, "type": "ping"}))
                continue

            # Ignore unrelated results such as our heartbeat pongs.
            if message.get("type") != "result" or message.get("id") != command_id:
                continue

            if not message.get("success"):
                raise RuntimeError(f"AI Task WebSocket: {_websocket_error_message(message)}")

            result_payload = message.get("result") or {}
            if not isinstance(result_payload, dict):
                raise RuntimeError("Réponse WebSocket AI Task invalide")
            response_payload = result_payload.get("response")

        data, conversation_id = _extract_ai_task_payload(response_payload)
        if isinstance(data, (dict, list)):
            text = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            text = str(data or "").strip()
        if not text:
            raise RuntimeError("AI Task a retourné un texte vide")
        text = _sanitize_ai_text(text, language)

        finished = time.time()
        return {
            **base,
            "status": "completed",
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "conversation_id": conversation_id,
            "heartbeat_count": heartbeat_count,
            "text": text,
            "input": {
                "context_characters": context_meta["characters"],
                "context_target_characters": context_meta["target_characters"],
                "context_limit_characters": context_meta["limit_characters"],
                "context_original_characters": context_meta["legacy_characters"],
                "context_full_compact_characters": context_meta["full_compact_characters"],
                "context_mode": context_meta["mode"],
                "context_schema": context_meta["schema"],
                "context_lossless": context_meta["lossless"],
                "context_current_sources": context_meta["current_sources"],
                "context_comparison_sources": context_meta["comparison_sources"],
                "omitted_current_sources": context_meta["omitted_current_sources"],
                "omitted_comparison_sources": context_meta["omitted_comparison_sources"],
                "sources": (result.get("summary") or {}).get("sources_total", 0),
                "comparison_targets": (result.get("comparisons") or {}).get("target_count", 0),
            },
        }
    except TimeoutError as exc:
        finished = time.time()
        return {
            **base,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "error": str(exc),
        }
    except websocket.WebSocketException as exc:
        finished = time.time()
        return {
            **base,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "error": f"WebSocket Home Assistant: {exc}",
        }
    except Exception as exc:
        finished = time.time()
        return {
            **base,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "error": str(exc),
        }
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

