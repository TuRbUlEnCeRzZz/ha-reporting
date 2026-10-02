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
        "density_applicable": quality.get("density_applicable"),
        "counter_mode": quality.get("counter_mode"),
        "near_zero_signal": bool(quality.get("near_zero_signal")),
        "sparse_zero_uncertain": bool(quality.get("sparse_zero_uncertain")),
        "warnings": quality.get("warnings") or [],
    }


def _comparison_interpretation(source: dict[str, Any]) -> dict[str, Any]:
    status = source.get("comparison_status")
    base_quality = _comparison_quality_snapshot(source.get("base_quality"))
    reference_quality = _comparison_quality_snapshot(source.get("reference_quality"))
    base_coverage = base_quality.get("period_coverage_percent")
    reference_coverage = reference_quality.get("period_coverage_percent")

    def coverage_tier(value):
        if not isinstance(value, (int, float)):
            return "unknown"
        if value >= 95.0:
            return "good"
        if value >= 80.0:
            return "partial"
        return "limited"

    base_coverage_tier = coverage_tier(base_coverage)
    reference_coverage_tier = coverage_tier(reference_coverage)
    base_coverage_limited = base_coverage_tier == "limited"
    reference_coverage_limited = reference_coverage_tier == "limited"
    coverage_limited = base_coverage_limited or reference_coverage_limited
    base_reconstructed = str(base_quality.get("counter_mode") or "") in {
        "provider_reconstructed",
        "reconstructed",
    }
    reference_reconstructed = str(reference_quality.get("counter_mode") or "") in {
        "provider_reconstructed",
        "reconstructed",
    }
    full_period_change_supported = bool(
        status == "comparable"
        and base_coverage_tier in {"good", "unknown"}
        and reference_coverage_tier in {"good", "unknown"}
    )

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
        "base_coverage_tier": base_coverage_tier,
        "reference_coverage_tier": reference_coverage_tier,
        "base_sparse_zero_uncertain": bool(base_quality.get("sparse_zero_uncertain")),
        "reference_sparse_zero_uncertain": bool(reference_quality.get("sparse_zero_uncertain")),
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


def _as_number(value: Any) -> float | None:
    """Return a finite numeric value or None without coercing arbitrary text."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _is_forecast_source(source_name: Any) -> bool:
    """Recognize common forecast/prediction wording without provider-specific IDs."""
    text = str(source_name or "").casefold()
    return any(token in text for token in (
        "forecast", "prevision", "prévision", "prediction", "prédiction", "predicted", "prévisionnel",
    ))


def _power_to_w(value: Any, unit: Any) -> float | None:
    number = _as_number(value)
    if number is None:
        return None
    normalized = str(unit or "").strip().casefold()
    if normalized == "w":
        return number
    if normalized == "kw":
        return number * 1000.0
    return None


def _energy_to_kwh(value: Any, unit: Any) -> float | None:
    number = _as_number(value)
    if number is None:
        return None
    normalized = str(unit or "").strip().casefold()
    if normalized == "kwh":
        return number
    if normalized == "wh":
        return number / 1000.0
    return None


def _rounded_derived(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(float(value), digits)


def _coverage_allows_full_period(*values: Any) -> bool:
    coverages = [_as_number(value) for value in values]
    return bool(coverages and all(value is not None and value >= 95.0 for value in coverages))


def _ordering_from_gap(value: Any) -> str | None:
    """Return deterministic base-vs-reference ordering for an absolute gap."""
    number = _as_number(value)
    if number is None:
        return None
    if abs(number) < 1e-12:
        return "equal"
    return "base_higher" if number > 0 else "base_lower"


def _trend_from_gap(value: Any) -> str | None:
    """Return deterministic full-period trend direction for an absolute gap."""
    number = _as_number(value)
    if number is None:
        return None
    if abs(number) < 1e-12:
        return "unchanged"
    return "increase" if number > 0 else "decrease"


def _current_source_relationships(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build deterministic, provider-agnostic cross-source comparisons.

    Relationships are emitted only when pairing is unambiguous inside one report
    device. HA Reporting performs the arithmetic so the AI does not need to infer
    source pairing or recalculate gaps. Partial coverage is preserved and exposed;
    it never causes a source to be discarded.
    """
    forecast_power = [
        row for row in rows
        if row.get("metric") == "power"
        and _is_forecast_source(row.get("source"))
        and _as_number((row.get("values") or {}).get("integrated_energy_kwh")) is not None
    ]
    measured_power = [
        row for row in rows
        if row.get("metric") == "power" and not _is_forecast_source(row.get("source"))
    ]
    actual_energy = [
        row for row in rows
        if row.get("metric") == "energy_total"
        and not _is_forecast_source(row.get("source"))
        and _energy_to_kwh((row.get("values") or {}).get("period_delta"), row.get("unit")) is not None
    ]

    relationships: list[dict[str, Any]] = []
    if len(forecast_power) == 1 and len(actual_energy) == 1:
        forecast = forecast_power[0]
        actual = actual_energy[0]
        forecast_kwh = _as_number((forecast.get("values") or {}).get("integrated_energy_kwh"))
        actual_kwh = _energy_to_kwh((actual.get("values") or {}).get("period_delta"), actual.get("unit"))
        if forecast_kwh is not None and actual_kwh is not None:
            supported = _coverage_allows_full_period(
                forecast.get("coverage_pct"), actual.get("coverage_pct")
            )
            relationship = {
                "kind": "energy_forecast_vs_actual",
                "forecast_source": forecast.get("source"),
                "actual_source": actual.get("source"),
                "forecast_energy_kwh": _rounded_derived(forecast_kwh),
                "actual_energy_kwh": _rounded_derived(actual_kwh),
                "forecast_coverage_pct": forecast.get("coverage_pct"),
                "actual_coverage_pct": actual.get("coverage_pct"),
                "full_period_comparison_supported": supported,
                "comparison_policy": (
                    "validated_full_period_gap" if supported
                    else "coverage_insufficient_for_period_gap"
                ),
            }
            if supported:
                gap_kwh = actual_kwh - forecast_kwh
                gap_pct = None if abs(forecast_kwh) < 0.1 else gap_kwh / forecast_kwh * 100.0
                relationship.update({
                    "absolute_gap_kwh": _rounded_derived(gap_kwh),
                    "relative_gap_pct": _rounded_derived(gap_pct, 3),
                    "ordering": _ordering_from_gap(gap_kwh),
                    "trend_direction": _trend_from_gap(gap_kwh),
                })
            relationships.append(relationship)

    if len(forecast_power) == 1 and len(measured_power) == 1:
        forecast = forecast_power[0]
        actual = measured_power[0]
        forecast_values = forecast.get("values") or {}
        actual_values = actual.get("values") or {}
        forecast_mean_w = _power_to_w(forecast_values.get("mean"), forecast.get("unit"))
        actual_mean_w = _power_to_w(actual_values.get("mean"), actual.get("unit"))
        if forecast_mean_w is not None and actual_mean_w is not None:
            supported = _coverage_allows_full_period(
                forecast.get("coverage_pct"), actual.get("coverage_pct")
            )
            relationship = {
                "kind": "power_forecast_vs_actual",
                "forecast_source": forecast.get("source"),
                "actual_source": actual.get("source"),
                "forecast_mean_w": _rounded_derived(forecast_mean_w),
                "actual_mean_w": _rounded_derived(actual_mean_w),
                "forecast_p95_w": _rounded_derived(_power_to_w(forecast_values.get("p95"), forecast.get("unit"))),
                "actual_p95_w": _rounded_derived(_power_to_w(actual_values.get("p95"), actual.get("unit"))),
                "forecast_max_w": _rounded_derived(_power_to_w(forecast_values.get("max"), forecast.get("unit"))),
                "actual_max_w": _rounded_derived(_power_to_w(actual_values.get("max"), actual.get("unit"))),
                "forecast_coverage_pct": forecast.get("coverage_pct"),
                "actual_coverage_pct": actual.get("coverage_pct"),
                "full_period_comparison_supported": supported,
                "comparison_policy": (
                    "validated_full_period_gap" if supported
                    else "coverage_insufficient_for_period_gap"
                ),
            }
            if supported:
                mean_gap_w = actual_mean_w - forecast_mean_w
                mean_gap_pct = None if abs(forecast_mean_w) < 0.1 else mean_gap_w / forecast_mean_w * 100.0
                relationship.update({
                    "mean_gap_w": _rounded_derived(mean_gap_w),
                    "mean_gap_pct": _rounded_derived(mean_gap_pct, 3),
                    "ordering": _ordering_from_gap(mean_gap_w),
                    "trend_direction": _trend_from_gap(mean_gap_w),
                })
            relationships.append(relationship)

    return relationships


def _fact_ledger_context_v11(result: dict[str, Any]) -> dict[str, Any]:
    """Build the complete deterministic RC6 fact ledger.

    RC6 keeps the complete semantic ledger internally, deduplicates repeated
    entities by their real Home Assistant entity id, and adds deterministic
    report/comparison quality signals. A smaller deterministic projection of this
    ledger is sent to the LLM later; the report itself remains unchanged.
    """
    context: dict[str, Any] = {
        "schema": "ha-reporting-ai-context-v12",
        "ledger_complete": True,
        "legend": {
            "source": {
                "i":"id","e":"entity_id","sk":"sensor_key","d":"device","g":"catalog",
                "m":"metric","u":"unit","cov":"coverage_pct","den":"density_pct",
                "st":"status","w":"warnings","rv":"runtime_verified","sh":"shared_source",
            },
            "comparison_set": {
                "i":"id","tg":"target","tp":"target_period","s":"source_id","st":"status",
                "p":"policy","bc":"base_coverage_pct","rc":"reference_coverage_pct",
                "bz":"base_sparse_zero_uncertain","rz":"reference_sparse_zero_uncertain",
                "br":"base_reconstructed","rr":"reference_reconstructed","r":"reasons",
            },
            "fact": {
                "i":"id","q":"scope(current|comparison)","s":"source_id","c":"comparison_id",
                "k":"stat","v":"value","b":"base","r":"reference","d":"gap","p":"gap_pct",
                "t":"trend_direction","pr":"gap_pct_reason",
            },
            "quality_signal": {
                "i":"id","k":"kind","st":"status","ms":"mandatory_summary",
                "ma":"mandatory_attention",
            },
        },
        "semantics": {
            "fact": "atomic authoritative statement; never combine facts to create a new comparison",
            "period_delta": "change during report period",
            "counter_end": "cumulative reading at period end; never period consumption",
            "integrated_energy_kwh": "energy integrated from the same power source over the report period",
            "coverage_quality": ">=95 representative; 80-95 partial/cautious; <80 limited",
            "relationship": "only allowed cross-source comparison",
            "forecast_peak": "max gap is context only; it never proves overload, calibration error or a fault",
            "projection": "the LLM receives a deterministic shortlist; all report data remains in HA Reporting",
        },
        "report": [
            (result.get("report") or {}).get("name"),
            (result.get("resolved_period") or {}).get("label"),
            (result.get("resolved_period") or {}).get("timezone"),
        ],
        "summary": result.get("summary") or {},
        "sources": [],
        "comparison_sets": [],
        "facts": [],
        "relationships": [],
        "quality_signals": [],
        "selection_policy": {},
        "counts": {
            "current_sources": 0,
            "current_sources_unique": 0,
            "comparison_sources": 0,
            "comparison_sources_unique": 0,
        },
    }

    fact_seq = 0
    source_by_key: dict[tuple[str, str, str], str] = {}
    source_rows_by_id: dict[str, dict[str, Any]] = {}
    fact_by_key: dict[tuple[Any, ...], str] = {}
    comparison_by_key: dict[tuple[Any, ...], str] = {}

    def source_identity(entity_id: Any, sensor_key: Any, metric: Any, unit: Any) -> tuple[str, str, str]:
        identity = str(entity_id or "").strip() or str(sensor_key or "").strip()
        return (identity, str(metric or ""), str(unit or ""))

    def ensure_source(
        *,
        entity_id: Any,
        sensor_key: Any,
        metric: Any,
        unit: Any,
        device: Any = None,
        catalog: Any = None,
        **metadata: Any,
    ) -> str:
        key = source_identity(entity_id, sensor_key, metric, unit)
        source_id = source_by_key.get(key)
        aliases = {
            "coverage_pct":"cov","density_pct":"den","status":"st","warnings":"w",
            "runtime_verified":"rv",
        }
        if source_id is None:
            source_id = f"S{len(context['sources']) + 1}"
            source_by_key[key] = source_id
            row: dict[str, Any] = {
                "i": source_id,
                "e": str(entity_id or "").strip() or None,
                "sk": str(sensor_key or "").strip() or None,
                "d": str(device or "").strip() or None,
                "g": str(catalog or "").strip() or None,
                "m": metric,
                "u": unit,
            }
            row = {k: v for k, v in row.items() if v is not None}
            for key_name, value in metadata.items():
                if value is not None and value != []:
                    row[aliases.get(key_name, key_name)] = value
            context["sources"].append(row)
            source_rows_by_id[source_id] = row
        else:
            row = source_rows_by_id[source_id]
            new_device = str(device or "").strip()
            if new_device and row.get("d") and row.get("d") != new_device:
                row["sh"] = True
            for key_name, value in metadata.items():
                alias = aliases.get(key_name, key_name)
                if value is not None and value != [] and alias not in row:
                    row[alias] = value
        return source_id

    def add_fact(*, dedup_key: tuple[Any, ...] | None = None, **payload: Any) -> str:
        nonlocal fact_seq
        if dedup_key is not None and dedup_key in fact_by_key:
            return fact_by_key[dedup_key]
        fact_seq += 1
        aliases = {
            "scope":"q","source_id":"s","comparison_id":"c","stat":"k","value":"v",
            "base":"b","reference":"r","gap":"d","gap_pct":"p","trend_direction":"t",
            "gap_pct_reason":"pr",
        }
        row: dict[str, Any] = {"i": f"F{fact_seq}"}
        for key, value in payload.items():
            if value is not None:
                row[aliases.get(key, key)] = value
        context["facts"].append(row)
        if dedup_key is not None:
            fact_by_key[dedup_key] = row["i"]
        return row["i"]

    # Current-period sources/facts. Reused entities (for example one room
    # temperature attached to several devices) are represented only once.
    for catalog in result.get("catalogs") or []:
        catalog_name = catalog.get("name")
        for device in catalog.get("devices") or []:
            info = device.get("device") or {}
            device_name = info.get("name")
            device_rows: list[dict[str, Any]] = []
            for source in device.get("sources") or []:
                context["counts"]["current_sources"] += 1
                analysis = source.get("analysis") or {}
                stats = analysis.get("statistics") or {}
                quality = analysis.get("quality") or {}
                validation = analysis.get("validation") or {}
                metric = source.get("metric")
                sensor_key = source.get("sensor_key") or source.get("entity_id")
                entity_id = source.get("entity_id")
                coverage = quality.get("period_coverage_percent")
                density = quality.get("sample_density_percent") if quality.get("density_applicable") else None
                source_id = ensure_source(
                    entity_id=entity_id,
                    sensor_key=sensor_key,
                    metric=metric,
                    unit=source.get("unit"),
                    device=device_name,
                    catalog=catalog_name,
                    coverage_pct=coverage,
                    density_pct=density,
                    status=source.get("status") if source.get("status") != "ok" else None,
                    warnings=(validation.get("warnings") or []) or None,
                    runtime_verified=True if source.get("verification") else None,
                )

                values: dict[str, Any]
                if metric == "power":
                    values = {"max": _stat_value(stats, "max"), "p95": stats.get("p95"), "mean": stats.get("mean")}
                    if source.get("derive_energy") and stats.get("integrated_energy_kwh") is not None:
                        values["integrated_energy_kwh"] = stats.get("integrated_energy_kwh")
                elif metric in {"temperature", "humidity", "voltage", "current", "energy_measurement"}:
                    values = {
                        "first": _stat_value(stats, "first"), "min": _stat_value(stats, "min"),
                        "mean": stats.get("mean"), "max": _stat_value(stats, "max"),
                        "last": _stat_value(stats, "last"),
                    }
                elif metric in {"energy_total", "runtime", "cycles"}:
                    values = {"period_delta": stats.get("delta"), "counter_end": _stat_value(stats, "last")}
                    if int(stats.get("resets_detected", 0) or 0) > 0:
                        values["resets_detected"] = int(stats.get("resets_detected", 0) or 0)
                else:
                    values = {"first": _stat_value(stats, "first"), "last": _stat_value(stats, "last"), "mean": stats.get("mean")}

                for stat, value in values.items():
                    if value is not None:
                        add_fact(
                            dedup_key=("current", source_id, stat),
                            scope="current", source_id=source_id, stat=stat, value=value,
                        )

                # Relationship pairing remains device-local so unrelated meters
                # are never joined merely because they share a metric type.
                relation_name = "/".join(str(part) for part in (catalog_name, device_name, sensor_key) if part not in (None, ""))
                device_rows.append({
                    "source": relation_name, "source_id": source_id, "metric": metric,
                    "unit": source.get("unit"), "values": values, "coverage_pct": coverage,
                })
            context["relationships"].extend(_current_source_relationships(device_rows))

    context["counts"]["current_sources_unique"] = len(context["sources"])

    # N/N-x comparisons. Repeated shared entities are deduplicated per target.
    comparisons = result.get("comparisons") or {}
    for target in comparisons.get("targets") or []:
        target_label = target.get("label")
        target_period = (target.get("resolved_period") or {}).get("label")
        for catalog in target.get("catalogs") or []:
            catalog_name = catalog.get("name")
            for device in catalog.get("devices") or []:
                device_name = device.get("name")
                for source in device.get("sources") or []:
                    context["counts"]["comparison_sources"] += 1
                    interpretation = _comparison_interpretation(source)
                    base_quality = source.get("base_quality") or {}
                    reference_quality = source.get("reference_quality") or {}
                    sensor_key = source.get("sensor_key") or source.get("entity_id")
                    source_id = ensure_source(
                        entity_id=source.get("entity_id"), sensor_key=sensor_key,
                        metric=source.get("metric"), unit=source.get("unit"),
                        device=device_name, catalog=catalog_name,
                    )
                    comparison_key = (str(target_label or ""), str(target_period or ""), source_id)
                    comparison_id = comparison_by_key.get(comparison_key)
                    if comparison_id is None:
                        comparison_id = f"C{len(context['comparison_sets']) + 1}"
                        comparison_by_key[comparison_key] = comparison_id
                        comparison_status = source.get("comparison_status")
                        comparison_set = {
                            "i": comparison_id, "tg": target_label, "tp": target_period, "s": source_id,
                            "st": comparison_status if comparison_status != "comparable" else None,
                            "p": interpretation.get("wording_policy"),
                            "bc": base_quality.get("period_coverage_percent"),
                            "rc": reference_quality.get("period_coverage_percent"),
                            "bz": True if interpretation.get("base_sparse_zero_uncertain") else None,
                            "rz": True if interpretation.get("reference_sparse_zero_uncertain") else None,
                            "br": True if interpretation.get("base_reconstructed") else None,
                            "rr": True if interpretation.get("reference_reconstructed") else None,
                            "r": (source.get("reasons") or []) or None,
                        }
                        context["comparison_sets"].append({k: v for k, v in comparison_set.items() if v is not None})
                    for item in source.get("values") or []:
                        if not isinstance(item, dict):
                            continue
                        raw_stat = str(item.get("key") or item.get("label") or "value")
                        stat_name = "period_delta" if raw_stat == "delta" and source.get("metric") in {"energy_total", "runtime", "cycles"} else raw_stat
                        kwargs: dict[str, Any] = {
                            "scope":"comparison", "comparison_id":comparison_id,
                            "stat":stat_name,
                            "base":item.get("base"), "reference":item.get("reference"),
                            "gap":item.get("absolute_change"),
                        }
                        if interpretation.get("wording_policy") == "full_period_change_allowed":
                            kwargs["trend_direction"] = _trend_from_gap(item.get("absolute_change"))
                        if item.get("relative_change_percent") is not None and item.get("relative_change_applicable"):
                            kwargs["gap_pct"] = item.get("relative_change_percent")
                        if item.get("relative_change_reason"):
                            kwargs["gap_pct_reason"] = item.get("relative_change_reason")
                        add_fact(
                            dedup_key=("comparison", comparison_id, kwargs["stat"]),
                            **kwargs,
                        )

    context["counts"]["comparison_sources_unique"] = len(context["comparison_sets"])

    # Resolve relationship source IDs after source deduplication.
    dedup_relationships: list[dict[str, Any]] = []
    seen_relationships: set[tuple[Any, ...]] = set()
    for relationship in context["relationships"]:
        forecast_name = relationship.get("forecast_source")
        actual_name = relationship.get("actual_source")
        forecast_id = None
        actual_id = None
        for row in context["sources"]:
            # The relationship names end with the sensor key; matching this way
            # avoids retaining long catalog/device paths in the source registry.
            sensor_key = str(row.get("sk") or "")
            if forecast_name and sensor_key and str(forecast_name).endswith("/" + sensor_key):
                forecast_id = row.get("i")
            if actual_name and sensor_key and str(actual_name).endswith("/" + sensor_key):
                actual_id = row.get("i")
        relationship["forecast_source_id"] = forecast_id
        relationship["actual_source_id"] = actual_id
        relationship.pop("forecast_source", None)
        relationship.pop("actual_source", None)
        if relationship.get("kind") == "power_forecast_vs_actual":
            relationship["max_interpretation"] = "context_only_not_a_fault_indicator"
        key = (
            relationship.get("kind"), forecast_id, actual_id,
            relationship.get("full_period_comparison_supported"),
        )
        if key in seen_relationships:
            continue
        seen_relationships.add(key)
        dedup_relationships.append(relationship)
    context["relationships"] = dedup_relationships
    for index, relationship in enumerate(context["relationships"], start=1):
        relationship["id"] = f"R{index}"

    # Global deterministic quality facts. These are small but crucial: the model
    # must not describe a partial year as representative or pretend a N/N-x
    # comparison is useful when every comparison is limited/unavailable.
    qseq = 0
    report_summary = result.get("summary") or {}
    total = int(report_summary.get("sources_total") or 0)
    ok = int(report_summary.get("sources_ok") or 0)
    no_data = int(report_summary.get("sources_no_data") or 0)
    errors = int(report_summary.get("sources_error") or 0)
    invalid = int(report_summary.get("sources_invalid") or 0)
    availability_pct = (ok / total * 100.0) if total else 100.0
    qseq += 1
    context["quality_signals"].append({
        "i": f"Q{qseq}", "k": "report_source_availability",
        "st": "good" if availability_pct >= 95.0 else ("partial" if availability_pct >= 80.0 else "limited"),
        "total": total, "ok": ok, "no_data": no_data, "errors": errors, "invalid": invalid,
        "availability_pct": _rounded_derived(availability_pct, 1),
        "ms": True if availability_pct < 80.0 else None,
        "ma": True if availability_pct < 95.0 else None,
    })

    for target in comparisons.get("targets") or []:
        summary = target.get("summary") or {}
        target_total = int(summary.get("sources_total") or 0)
        comparable = int(summary.get("sources_comparable") or 0)
        partial = int(summary.get("sources_partial") or 0)
        limited = int(summary.get("sources_limited") or 0)
        reconstructed = int(summary.get("sources_reconstructed") or 0)
        unavailable = int(summary.get("sources_unavailable") or 0)
        representative = comparable + partial
        qseq += 1
        no_representative = bool(target_total and representative == 0)
        weak = bool(target_total and representative / target_total < 0.5)
        context["quality_signals"].append({
            "i": f"Q{qseq}", "k": "comparison_quality",
            "st": "no_representative" if no_representative else ("limited" if weak else "good"),
            "target": target.get("label"),
            "target_period": (target.get("resolved_period") or {}).get("label"),
            "total": target_total, "comparable": comparable, "partial": partial,
            "limited": limited, "reconstructed": reconstructed, "unavailable": unavailable,
            "representative": representative,
            "ms": True if no_representative else None,
            "ma": True if no_representative or weak else None,
        })

    _populate_selection_policy(context)
    return context

def _populate_selection_policy(context: dict[str, Any]) -> None:
    """Declare the RC6 shortlist/id-only selection protocol."""
    mandatory_quality_summary = [
        str(row.get("i")) for row in context.get("quality_signals") or []
        if row.get("i") and row.get("ms")
    ]
    mandatory_attention = [
        str(row.get("i")) for row in context.get("quality_signals") or []
        if row.get("i") and row.get("ma")
    ]
    # RC6: a validated forecast-vs-actual relation is authoritative and must not
    # be dropped by the LLM shortlist selection. Prefer energy before power so
    # the period-energy relationship survives even when other mandatory quality
    # signals consume part of the four-line summary budget.
    validated_relationships = [
        row for row in context.get("relationships") or []
        if row.get("id") and row.get("full_period_comparison_supported")
    ]
    validated_relationships.sort(
        key=lambda row: (
            0 if row.get("kind") == "energy_forecast_vs_actual" else 1,
            str(row.get("id")),
        )
    )
    mandatory_summary: list[str] = []
    for row in validated_relationships:
        rid = str(row.get("id"))
        if rid not in mandatory_summary:
            mandatory_summary.append(rid)
    for qid in mandatory_quality_summary:
        if qid not in mandatory_summary:
            mandatory_summary.append(qid)
    context["selection_policy"] = {
        "protocol": "id_only_v3_relationship_priority",
        "summary_prefixes": ["F", "R", "Q"],
        "attention_prefixes": ["F", "C", "S", "R", "Q"],
        "mandatory_summary": mandatory_summary,
        "mandatory_attention": mandatory_attention,
        "recommendation_actions": [
            "collect_more_data",
            "monitor_forecast",
            "monitor_source",
            "verify_reconstructed_counter",
        ],
    }


def _allowed_selection_ids(context: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    """Return deterministic allowed ID sets for the projected ledger.

    RC6 deliberately refuses low-coverage current values and limited/reconstructed
    N/N-x facts as normal summary evidence. Those facts remain available as
    attention evidence through their source/comparison quality IDs.
    """
    sources = {row.get("i"): row for row in context.get("sources") or []}
    comparisons = {row.get("i"): row for row in context.get("comparison_sets") or []}
    summary: set[str] = set()
    attention: set[str] = set()

    for quality in context.get("quality_signals") or []:
        qid = quality.get("i")
        if not qid:
            continue
        if quality.get("ms"):
            summary.add(str(qid))
        if quality.get("ma") or quality.get("st") not in {None, "good"}:
            attention.add(str(qid))

    for relationship in context.get("relationships") or []:
        rid = relationship.get("id")
        if not rid:
            continue
        if relationship.get("full_period_comparison_supported", True):
            summary.add(str(rid))
        else:
            attention.add(str(rid))

    for fact in context.get("facts") or []:
        fid = fact.get("i")
        if not fid:
            continue
        fid = str(fid)
        scope = fact.get("q")
        stat = fact.get("k")
        source = sources.get(fact.get("s")) or {}
        metric = source.get("m")
        comparison = comparisons.get(fact.get("c")) or {}
        if scope == "current":
            coverage = _as_number(source.get("cov"))
            representative = coverage is None or coverage >= 80.0
            if representative and stat in {"mean", "period_delta", "integrated_energy_kwh"}:
                summary.add(fid)
        elif scope == "comparison":
            status = comparison.get("st") or "comparable"
            if status in {"comparable", "partial"} and stat in {"mean", "period_delta"}:
                summary.add(fid)
            if status in {"partial", "limited", "reconstructed"} and stat in {"mean", "period_delta"}:
                attention.add(fid)
            elif fact.get("p") is not None and stat in {"mean", "period_delta"}:
                try:
                    if abs(float(fact.get("p"))) >= 20:
                        attention.add(fid)
                except (TypeError, ValueError):
                    pass

    for comparison in context.get("comparison_sets") or []:
        cid = comparison.get("i")
        if cid and (
            comparison.get("st") in {"partial", "limited", "reconstructed", "unavailable"}
            or comparison.get("r")
            or comparison.get("bz")
            or comparison.get("rz")
            or comparison.get("br")
            or comparison.get("rr")
        ):
            attention.add(str(cid))

    for source in context.get("sources") or []:
        sid = source.get("i")
        coverage = _as_number(source.get("cov"))
        if sid and (source.get("st") or source.get("w") or (coverage is not None and coverage < 80.0)):
            attention.add(str(sid))

    return summary, attention, set(attention)


def _selection_index(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key in ("sources", "comparison_sets", "facts", "relationships", "quality_signals"):
        for row in context.get(key) or []:
            rid = row.get("i") or row.get("id")
            if rid:
                out[str(rid)] = row
    return out


def _fact_score(fact: dict[str, Any], sources: dict[str, dict[str, Any]], comparisons: dict[str, dict[str, Any]]) -> float:
    """Score one deterministic fact for RC6's LLM shortlist."""
    stat = str(fact.get("k") or "")
    score = {"period_delta": 100.0, "integrated_energy_kwh": 96.0, "mean": 90.0}.get(stat, 10.0)
    source = sources.get(fact.get("s")) or {}
    metric = source.get("m")
    if metric == "energy_total":
        score += 18.0
    elif metric == "power":
        score += 10.0
    elif metric == "temperature":
        score += 4.0
    coverage = _as_number(source.get("cov"))
    if coverage is not None:
        score += 15.0 if coverage >= 95.0 else (5.0 if coverage >= 80.0 else -40.0)
    if fact.get("q") == "comparison":
        comparison = comparisons.get(fact.get("c")) or {}
        status = comparison.get("st") or "comparable"
        score += {"comparable": 25.0, "partial": 10.0, "limited": -50.0, "reconstructed": -30.0, "unavailable": -100.0}.get(status, 0.0)
        pct = _as_number(fact.get("p"))
        if pct is not None:
            score += min(abs(pct), 200.0) / 8.0
        gap = _as_number(fact.get("d"))
        if gap is not None and pct is None:
            score += min(abs(gap), 100.0) / 20.0
    return score


def _comparison_attention_score(row: dict[str, Any]) -> float:
    status = row.get("st") or "comparable"
    score = {"reconstructed": 100.0, "limited": 90.0, "partial": 60.0, "unavailable": 35.0}.get(status, 0.0)
    if row.get("br") or row.get("rr"):
        score += 30.0
    for key in ("bc", "rc"):
        coverage = _as_number(row.get(key))
        if coverage is not None:
            score += max(0.0, 80.0 - coverage) / 4.0
    if row.get("r"):
        score += 5.0
    return score


def _project_ai_context(full: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic RC6 shortlist for the LLM.

    The complete ledger stays inside HA Reporting. The model sees only facts that
    can materially improve the synthesis or explain quality limitations. This is
    the main RC6 latency optimization for local CPU inference.
    """
    sources = {row.get("i"): row for row in full.get("sources") or []}
    comparisons = {row.get("i"): row for row in full.get("comparison_sets") or []}
    facts = list(full.get("facts") or [])
    relationships = list(full.get("relationships") or [])
    quality_signals = list(full.get("quality_signals") or [])

    # Top representative current/comparison facts. Power peaks/P95/counter_end
    # never enter the shortlist because they are not normal summary candidates.
    summary_allowed, attention_allowed, _ = _allowed_selection_ids(full)
    summary_facts = [f for f in facts if str(f.get("i")) in summary_allowed]
    summary_facts.sort(key=lambda f: (-_fact_score(f, sources, comparisons), str(f.get("i"))))
    selected_fact_ids = {str(f.get("i")) for f in summary_facts[:28]}

    # Keep a small set of high-impact comparable changes as attention candidates.
    attention_facts = [
        f for f in facts
        if str(f.get("i")) in attention_allowed and f.get("q") == "comparison"
    ]
    attention_facts.sort(key=lambda f: (-_fact_score(f, sources, comparisons), str(f.get("i"))))
    selected_fact_ids.update(str(f.get("i")) for f in attention_facts[:8])

    # Keep the most useful comparison-quality objects, prioritizing limited and
    # reconstructed cases. Unavailable entries are summarized globally instead
    # of flooding the LLM with dozens of near-identical rows.
    attention_comparisons = [
        row for row in comparisons.values()
        if str(row.get("i")) in attention_allowed and row.get("st") != "unavailable"
    ]
    attention_comparisons.sort(key=lambda r: (-_comparison_attention_score(r), str(r.get("i"))))
    selected_comparison_ids = {str(row.get("i")) for row in attention_comparisons[:14]}
    for fact in facts:
        if str(fact.get("i")) in selected_fact_ids and fact.get("c"):
            selected_comparison_ids.add(str(fact.get("c")))

    # Source-quality warnings: only the worst few are needed because global Q*
    # signals already describe the report-wide completeness.
    quality_sources = []
    for row in sources.values():
        sid = str(row.get("i"))
        if sid not in attention_allowed:
            continue
        coverage = _as_number(row.get("cov"))
        severity = 100.0 - (coverage if coverage is not None else 100.0)
        if row.get("st"):
            severity += 25.0
        if row.get("w"):
            severity += 10.0
        quality_sources.append((severity, sid, row))
    quality_sources.sort(key=lambda item: (-item[0], item[1]))
    selected_source_alert_ids = {item[1] for item in quality_sources[:8]}

    selected_source_ids = set(selected_source_alert_ids)
    for fact in facts:
        if str(fact.get("i")) in selected_fact_ids:
            sid = fact.get("s")
            if sid:
                selected_source_ids.add(str(sid))
            cid = fact.get("c")
            if cid:
                comp = comparisons.get(cid) or {}
                if comp.get("s"):
                    selected_source_ids.add(str(comp.get("s")))
    for cid in selected_comparison_ids:
        comp = comparisons.get(cid) or {}
        if comp.get("s"):
            selected_source_ids.add(str(comp.get("s")))
    for relationship in relationships:
        for key in ("forecast_source_id", "actual_source_id"):
            if relationship.get(key):
                selected_source_ids.add(str(relationship.get(key)))

    projected = {
        "schema": full.get("schema"),
        "ledger_complete": False,
        "projection": "deterministic_shortlist_v1",
        "legend": full.get("legend"),
        "semantics": full.get("semantics"),
        "report": full.get("report"),
        "summary": full.get("summary"),
        "sources": [row for row in full.get("sources") or [] if str(row.get("i")) in selected_source_ids],
        "comparison_sets": [row for row in full.get("comparison_sets") or [] if str(row.get("i")) in selected_comparison_ids],
        "facts": [row for row in facts if str(row.get("i")) in selected_fact_ids],
        "relationships": relationships,
        "quality_signals": quality_signals,
        "selection_policy": {},
        "counts": dict(full.get("counts") or {}),
        "ledger_stats": {
            "full_sources": len(full.get("sources") or []),
            "shortlisted_sources": len(selected_source_ids),
            "full_comparison_sets": len(full.get("comparison_sets") or []),
            "shortlisted_comparison_sets": len(selected_comparison_ids),
            "full_facts": len(facts),
            "shortlisted_facts": len(selected_fact_ids),
        },
    }
    _populate_selection_policy(projected)
    return projected

def _extract_json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _validate_selection(data: Any, context: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Validate an id-only AI selection and inject mandatory quality facts."""
    parsed = _extract_json_object(data) or {}
    policy = context.get("selection_policy") or {}
    summary_allowed, attention_allowed, evidence_allowed = _allowed_selection_ids(context)
    actions_allowed = set(policy.get("recommendation_actions") or [])

    def ids(key: str, allowed: set[str], limit: int) -> list[str]:
        value = parsed.get(key)
        if not isinstance(value, list):
            return []
        selected: list[str] = []
        for item in value:
            item = str(item)
            if item in allowed and item not in selected:
                selected.append(item)
            if len(selected) >= limit:
                break
        return selected

    model_summary = ids("summary", summary_allowed, 4)
    model_attention = ids("attention", attention_allowed, 5)
    model_valid = bool(model_summary)

    mandatory_summary = [
        str(item) for item in (policy.get("mandatory_summary") or [])
        if str(item) in summary_allowed
    ]
    mandatory_attention = [
        str(item) for item in (policy.get("mandatory_attention") or [])
        if str(item) in attention_allowed
    ]

    summary: list[str] = []
    for item in mandatory_summary + model_summary:
        if item not in summary:
            summary.append(item)
        if len(summary) >= 4:
            break
    attention: list[str] = []
    for item in mandatory_attention + model_attention:
        if item not in attention:
            attention.append(item)
        if len(attention) >= 5:
            break

    recommendations: list[dict[str, str]] = []
    raw_recommendations = parsed.get("recommendations")
    if isinstance(raw_recommendations, list):
        for item in raw_recommendations:
            if not isinstance(item, dict):
                continue
            action = str(item.get("action") or "")
            evidence = str(item.get("evidence") or "")
            if action in actions_allowed and evidence in evidence_allowed:
                pair = {"action": action, "evidence": evidence}
                if pair not in recommendations:
                    recommendations.append(pair)
            if len(recommendations) >= 4:
                break

    return {
        "summary": summary,
        "attention": attention,
        "recommendations": recommendations,
    }, model_valid

def _fallback_selection(context: dict[str, Any]) -> dict[str, Any]:
    """Deterministic fallback if the model does not return valid JSON IDs."""
    summary_set, attention_set, _ = _allowed_selection_ids(context)
    index = _selection_index(context)
    ordered_ids = list(index)
    summary_allowed = [item for item in ordered_ids if item in summary_set]
    attention_allowed = [item for item in ordered_ids if item in attention_set]
    policy = context.get("selection_policy") or {}

    summary: list[str] = []
    for item in policy.get("mandatory_summary") or []:
        item = str(item)
        if item in summary_set and item not in summary:
            summary.append(item)

    # Prefer validated energy and power forecast relationships for EMHASS-like reports.
    for kind in ("energy_forecast_vs_actual", "power_forecast_vs_actual"):
        for rid in summary_allowed:
            row = index.get(rid) or {}
            if row.get("kind") == kind and row.get("full_period_comparison_supported"):
                if rid not in summary:
                    summary.append(rid)
                break

    # Then choose representative comparison means/period totals, followed by
    # representative current facts. Low-quality facts are excluded upstream.
    for rid in summary_allowed:
        if len(summary) >= 4:
            break
        if rid in summary:
            continue
        row = index.get(rid) or {}
        if rid.startswith("F") and row.get("q") == "comparison" and row.get("k") in {"period_delta", "mean"}:
            summary.append(rid)
    for rid in summary_allowed:
        if len(summary) >= 4:
            break
        if rid not in summary:
            summary.append(rid)

    attention: list[str] = []
    fallback_attention = [item for item in attention_allowed if not str(item).startswith("F")]
    for item in (policy.get("mandatory_attention") or []) + fallback_attention:
        item = str(item)
        if item in attention_set and item not in attention:
            attention.append(item)
        if len(attention) >= 5:
            break

    recommendations: list[dict[str, str]] = []
    for rid in attention[:4]:
        row = index.get(rid) or {}
        if rid.startswith("R"):
            action = "monitor_forecast"
        elif rid.startswith("C") and (row.get("br") or row.get("rr")):
            action = "verify_reconstructed_counter"
        elif rid.startswith("Q"):
            action = "collect_more_data"
        elif rid.startswith("C") and row.get("st") in {"partial", "limited", "unavailable"}:
            action = "collect_more_data"
        else:
            action = "monitor_source"
        recommendations.append({"action": action, "evidence": rid})
    return {"summary": summary[:4], "attention": attention, "recommendations": recommendations[:4]}

def _source_label(source: dict[str, Any], language: str = "fr") -> str:
    """Return a human-oriented label without leaking grouping artefacts.

    Temperature/humidity sources prefer their real sensor identity so a shared
    room sensor is not described as if it belonged to the first appliance group
    that referenced it. Other device-specific metrics keep the configured device
    name where that is more readable.
    """
    language = "en" if str(language).lower() == "en" else "fr"
    sensor_key = str(source.get("sk") or source.get("e") or source.get("n") or "source")
    metric = str(source.get("m") or "")
    device = str(source.get("d") or "").strip()
    catalog = str(source.get("g") or "").strip()
    lowered = sensor_key.casefold()

    if "p_load_forecast" in lowered or _is_forecast_source(sensor_key):
        return "EMHASS forecast" if language == "en" else "Prévision EMHASS"
    if "total_active_power" in lowered or lowered.endswith("active_power"):
        return "Total electrical power" if language == "en" else "Puissance électrique totale"
    if "total_active_energy" in lowered or lowered.endswith("active_energy"):
        return "Total electrical energy" if language == "en" else "Énergie électrique totale"

    def human_sensor(value: str) -> str:
        text = value
        if text.startswith("sensor."):
            text = text[7:]
        for prefix in ("sensor_temp_", "temp_", "temperature_"):
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        for suffix in ("_temperature", "_humidity", "_power", "_puissance", "_energy", "_energie"):
            if text.endswith(suffix):
                text = text[:-len(suffix)]
                break
        text = text.replace("_", " ").strip()
        return text or value

    if metric in {"temperature", "humidity"} or source.get("sh"):
        label = human_sensor(sensor_key)
        return label[0].upper() + label[1:] if label else "Source"
    if device and device.casefold() not in {"emhass", "devices", "device"}:
        return device
    label = human_sensor(sensor_key)
    if label and label != "source":
        return label[0].upper() + label[1:]
    return device or catalog or ("Source" if language == "en" else "Source")

def _fmt_number(value: Any, language: str = "fr", signed: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    abs_number = abs(number)
    decimals = 0 if abs_number >= 100 else (1 if abs_number >= 10 else 2)
    text = f"{number:+.{decimals}f}" if signed else f"{number:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if language == "fr":
        text = text.replace(".", ",")
    return text


def _stat_label(metric: str | None, stat: str | None, language: str) -> str:
    fr = {
        "mean": "moyenne", "max": "maximum", "min": "minimum", "p95": "P95",
        "period_delta": "consommation de période" if metric == "energy_total" else "variation de période",
        "integrated_energy_kwh": "énergie intégrée", "counter_end": "index de fin de compteur",
        "resets_detected": "resets détectés", "first": "première valeur", "last": "dernière valeur",
    }
    en = {
        "mean": "mean", "max": "maximum", "min": "minimum", "p95": "P95",
        "period_delta": "period consumption" if metric == "energy_total" else "period change",
        "integrated_energy_kwh": "integrated energy", "counter_end": "end meter reading",
        "resets_detected": "detected resets", "first": "first value", "last": "last value",
    }
    return (en if language == "en" else fr).get(str(stat), str(stat or "value"))


def _quality_suffix(comparison: dict[str, Any], language: str) -> str:
    status = comparison.get("st") or "comparable"
    bc = comparison.get("bc")
    rc = comparison.get("rc")
    if language == "en":
        if status == "partial":
            return f" The comparison is partial (coverage {_fmt_number(bc, language) if bc is not None else '?'}% / {_fmt_number(rc, language) if rc is not None else '?'}%)."
        if status == "limited":
            return f" The comparison is limited (coverage {_fmt_number(bc, language) if bc is not None else '?'}% / {_fmt_number(rc, language) if rc is not None else '?'}%)."
        if status == "reconstructed":
            return " The comparison uses a reconstructed counter after reset(s)."
        return ""
    if status == "partial":
        return f" La comparaison est partielle (couverture {_fmt_number(bc, language) if bc is not None else '?'} % / {_fmt_number(rc, language) if rc is not None else '?'} %)."
    if status == "limited":
        return f" La comparaison est limitée (couverture {_fmt_number(bc, language) if bc is not None else '?'} % / {_fmt_number(rc, language) if rc is not None else '?'} %)."
    if status == "reconstructed":
        return " La comparaison utilise un compteur reconstruit après reset(s)."
    return ""


def _render_ledger_id(item_id: str, context: dict[str, Any], language: str, section: str) -> str | None:
    index = _selection_index(context)
    row = index.get(item_id)
    if not row:
        return None
    sources = {item.get("i"): item for item in context.get("sources") or []}
    comparisons = {item.get("i"): item for item in context.get("comparison_sets") or []}

    if item_id.startswith("Q"):
        kind = row.get("k")
        if kind == "report_source_availability":
            total = int(row.get("total") or 0)
            ok = int(row.get("ok") or 0)
            no_data = int(row.get("no_data") or 0)
            errors = int(row.get("errors") or 0)
            invalid = int(row.get("invalid") or 0)
            pct = _fmt_number(row.get("availability_pct"), language)
            if language == "en":
                return f"Report source availability is {ok}/{total} ({pct}%); {no_data} have no data, {errors} errors and {invalid} invalid sources."
            return f"Disponibilité des sources du rapport : {ok}/{total} ({pct} %) ; {no_data} sans données, {errors} en erreur et {invalid} invalides."
        if kind == "comparison_quality":
            target = row.get("target") or ("reference" if language == "en" else "référence")
            comparable = int(row.get("comparable") or 0)
            partial = int(row.get("partial") or 0)
            limited = int(row.get("limited") or 0)
            reconstructed = int(row.get("reconstructed") or 0)
            unavailable = int(row.get("unavailable") or 0)
            if row.get("st") == "no_representative":
                if language == "en":
                    return f"{target}: no representative N/N-x comparison is available ({comparable} comparable, {partial} partial, {limited} limited, {reconstructed} reconstructed, {unavailable} unavailable)."
                return f"{target} : aucune comparaison N/N-x représentative n'est disponible ({comparable} comparable, {partial} partielle, {limited} limitées, {reconstructed} reconstruites, {unavailable} indisponibles)."
            if language == "en":
                return f"{target}: comparison quality is mixed ({comparable} comparable, {partial} partial, {limited} limited, {reconstructed} reconstructed, {unavailable} unavailable)."
            return f"{target} : qualité de comparaison hétérogène ({comparable} comparables, {partial} partielles, {limited} limitées, {reconstructed} reconstruites, {unavailable} indisponibles)."

    if item_id.startswith("F"):
        comparison = comparisons.get(row.get("c")) or {}
        source = sources.get(row.get("s")) or sources.get(comparison.get("s")) or {}
        label = _source_label(source, language)
        metric = source.get("m")
        stat = row.get("k")
        # integrated_energy_kwh is a derived ENERGY fact even when the source
        # itself is a power sensor expressed in W. Never inherit the source unit.
        unit = "kWh" if stat == "integrated_energy_kwh" else (source.get("u") or "")
        stat_label = _stat_label(metric, stat, language)
        if row.get("q") == "comparison":
            base = _fmt_number(row.get("b"), language)
            reference = _fmt_number(row.get("r"), language)
            gap = _fmt_number(row.get("d"), language, signed=True)
            pct = row.get("p")
            pct_text = f" ({_fmt_number(pct, language, signed=True)} %)" if pct is not None else ""
            if language == "en":
                text = f"{label}: {stat_label} {base} {unit} versus {reference} {unit}; gap {gap} {unit}{pct_text}."
            else:
                text = f"{label} : {stat_label} {base} {unit} contre {reference} {unit} ; écart {gap} {unit}{pct_text}."
            if comparison.get("st"):
                text += _quality_suffix(comparison, language)
            return text.replace("  ", " ").strip()
        value = _fmt_number(row.get("v"), language)
        if language == "en":
            if metric == "temperature" and stat == "mean":
                return f"The mean temperature for {label} is {value} {unit}."
            if metric == "power" and stat == "mean":
                return f"The mean power for {label} is {value} {unit}."
            if metric == "energy_total" and stat == "period_delta":
                return f"The period energy consumption for {label} is {value} {unit}."
            return f"{label}: {stat_label} {value} {unit}.".replace("  ", " ")
        if metric == "temperature" and stat == "mean":
            return f"La température moyenne de {label} est de {value} {unit}."
        if metric == "power" and stat == "mean":
            return f"La puissance moyenne de {label} est de {value} {unit}."
        if metric == "energy_total" and stat == "period_delta":
            return f"La consommation d'énergie de {label} sur la période est de {value} {unit}."
        return f"{label} : {stat_label} {value} {unit}.".replace("  ", " ")

    if item_id.startswith("R"):
        kind = row.get("kind")
        supported = bool(row.get("full_period_comparison_supported"))
        if kind == "energy_forecast_vs_actual":
            forecast = _fmt_number(row.get("forecast_energy_kwh"), language)
            actual = _fmt_number(row.get("actual_energy_kwh"), language)
            fcov = _fmt_number(row.get("forecast_coverage_pct"), language)
            acov = _fmt_number(row.get("actual_coverage_pct"), language)
            if supported:
                gap = _fmt_number(row.get("absolute_gap_kwh"), language, signed=True)
                pct = _fmt_number(row.get("relative_gap_pct"), language, signed=True)
                if language == "en":
                    return f"Actual period energy is {actual} kWh versus {forecast} kWh forecast; gap {gap} kWh ({pct} %)."
                return f"L'énergie réelle de la période est de {actual} kWh contre {forecast} kWh prévus ; écart {gap} kWh ({pct} %)."
            if language == "en":
                return f"Forecast integrated energy is {forecast} kWh ({fcov}% coverage) and actual energy is {actual} kWh ({acov}% coverage); coverage is insufficient for a full-period gap."
            return f"L'énergie prévisionnelle intégrée est de {forecast} kWh (couverture {fcov} %) et l'énergie réelle de {actual} kWh (couverture {acov} %) ; la couverture est insuffisante pour calculer un écart de période complet."
        if kind == "power_forecast_vs_actual":
            forecast = _fmt_number(row.get("forecast_mean_w"), language)
            actual = _fmt_number(row.get("actual_mean_w"), language)
            if supported:
                gap = _fmt_number(row.get("mean_gap_w"), language, signed=True)
                pct = _fmt_number(row.get("mean_gap_pct"), language, signed=True)
                if language == "en":
                    return f"Mean measured power is {actual} W versus {forecast} W forecast; gap {gap} W ({pct} %)."
                return f"La puissance moyenne mesurée est de {actual} W contre {forecast} W prévue ; écart {gap} W ({pct} %)."
            fcov = _fmt_number(row.get("forecast_coverage_pct"), language)
            acov = _fmt_number(row.get("actual_coverage_pct"), language)
            if language == "en":
                return f"Mean forecast power is {forecast} W ({fcov}% coverage) and measured power is {actual} W ({acov}% coverage); coverage is insufficient for a full-period gap."
            return f"La puissance moyenne prévue est de {forecast} W (couverture {fcov} %) et la puissance moyenne mesurée de {actual} W (couverture {acov} %) ; la couverture est insuffisante pour un écart de période complet."

    if item_id.startswith("C"):
        source = sources.get(row.get("s")) or {}
        label = _source_label(source, language)
        status = row.get("st") or "comparable"
        reasons = row.get("r") or []
        reason = str(reasons[0]) if reasons else ""
        if language == "en":
            if status == "limited":
                return f"{label}: comparison is limited. {reason}".strip()
            if status == "partial":
                return f"{label}: comparison is partial and should be interpreted cautiously. {reason}".strip()
            if status == "reconstructed" or row.get("br") or row.get("rr"):
                return f"{label}: the comparison includes a counter reconstructed after reset(s)."
            return f"{label}: comparison quality requires attention. {reason}".strip()
        if status == "limited":
            return f"{label} : comparaison limitée. {reason}".strip()
        if status == "partial":
            return f"{label} : comparaison partielle à interpréter avec prudence. {reason}".strip()
        if status == "reconstructed" or row.get("br") or row.get("rr"):
            return f"{label} : la comparaison inclut un compteur reconstruit après reset(s)."
        return f"{label} : la qualité de comparaison demande de la prudence. {reason}".strip()

    if item_id.startswith("S"):
        label = _source_label(row, language)
        coverage = row.get("cov")
        warnings = row.get("w") or []
        if language == "en":
            detail = f" Coverage: {_fmt_number(coverage, language)}%." if coverage is not None else ""
            if warnings:
                detail += f" Warning: {warnings[0]}"
            return f"{label}: source quality requires attention.{detail}".strip()
        detail = f" Couverture : {_fmt_number(coverage, language)} %." if coverage is not None else ""
        if warnings:
            detail += f" Avertissement : {warnings[0]}"
        return f"{label} : la qualité de la source demande de la prudence.{detail}".strip()
    return None


def _render_recommendation(action: str, evidence: str, context: dict[str, Any], language: str) -> str:
    index = _selection_index(context)
    row = index.get(evidence) or {}
    sources = {item.get("i"): item for item in context.get("sources") or []}
    source = None
    if evidence.startswith("F"):
        source = sources.get(row.get("s"))
        if source is None and row.get("c"):
            comparisons = {item.get("i"): item for item in context.get("comparison_sets") or []}
            comparison = comparisons.get(row.get("c")) or {}
            source = sources.get(comparison.get("s"))
    elif evidence.startswith("C"):
        source = sources.get(row.get("s"))
    elif evidence.startswith("S"):
        source = row
    elif evidence.startswith("R"):
        source = sources.get(row.get("actual_source_id")) or sources.get(row.get("forecast_source_id"))
    elif evidence.startswith("Q"):
        source = None
    label = _source_label(source or {}, language)

    if evidence.startswith("Q"):
        if row.get("k") == "report_source_availability":
            return (
                "Continue collecting missing source history before treating the report as fully representative."
                if language == "en" else
                "Poursuivre la collecte des historiques manquants avant de considérer le rapport comme pleinement représentatif."
            )
        if row.get("k") == "comparison_quality":
            return (
                "Wait for a more representative reference period before drawing N/N-x conclusions."
                if language == "en" else
                "Attendre une période de référence plus représentative avant de tirer des conclusions N/N-x."
            )

    if language == "en":
        texts = {
            "collect_more_data": f"Continue collecting data for {label} before drawing stronger conclusions.",
            "monitor_forecast": "Monitor forecast-versus-measured differences over several periods before concluding that there is a systematic bias.",
            "monitor_source": f"Monitor {label} and reassess it when more representative data are available.",
            "verify_reconstructed_counter": f"Keep monitoring {label} after counter reconstruction and check future resets.",
        }
    else:
        texts = {
            "collect_more_data": f"Poursuivre la collecte de données pour {label} avant de tirer des conclusions plus fortes.",
            "monitor_forecast": "Surveiller l'écart entre prévision et mesure sur plusieurs périodes avant de conclure à un biais systématique.",
            "monitor_source": f"Surveiller {label} et réévaluer la situation lorsque les données seront plus représentatives.",
            "verify_reconstructed_counter": f"Continuer à surveiller {label} après reconstruction du compteur et contrôler les prochains resets.",
        }
    return texts.get(action, texts["monitor_source"])


def _recommendation_source_identity(evidence: str, context: dict[str, Any]) -> tuple[str, str] | None:
    """Return a stable source identity and label for recommendation merging."""
    index = _selection_index(context)
    row = index.get(evidence) or {}
    sources = {item.get("i"): item for item in context.get("sources") or []}
    comparisons = {item.get("i"): item for item in context.get("comparison_sets") or []}
    source = None
    if evidence.startswith("F"):
        source = sources.get(row.get("s"))
        if source is None and row.get("c"):
            source = sources.get((comparisons.get(row.get("c")) or {}).get("s"))
    elif evidence.startswith("C"):
        source = sources.get(row.get("s"))
    elif evidence.startswith("S"):
        source = row
    elif evidence.startswith("R"):
        # Forecast relationships are intentionally grouped as their own semantic
        # topic rather than folded into the actual meter recommendation.
        return (f"relationship:{evidence}", "")
    elif evidence.startswith("Q"):
        return (f"quality:{evidence}", "")
    if not source:
        return None
    identity = str(source.get("e") or source.get("sk") or source.get("i") or evidence)
    return identity, str(source.get("i") or "")


def _merged_recommendation_lines(selection: dict[str, Any], context: dict[str, Any], language: str) -> list[str]:
    """Merge multiple recommendation actions that target the same real source."""
    raw = [item for item in selection.get("recommendations") or [] if isinstance(item, dict)]
    groups: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    for item in raw:
        action = str(item.get("action") or "")
        evidence = str(item.get("evidence") or "")
        identity = _recommendation_source_identity(evidence, context)
        key = identity[0] if identity else f"evidence:{evidence}"
        group = by_key.get(key)
        if group is None:
            group = {"key": key, "actions": [], "items": []}
            by_key[key] = group
            groups.append(group)
        if action and action not in group["actions"]:
            group["actions"].append(action)
        group["items"].append(item)

    lines: list[str] = []
    for group in groups:
        items = group["items"]
        actions = set(group["actions"])
        first = items[0]
        evidence = str(first.get("evidence") or "")
        # Quality and relationship recommendations keep their dedicated wording.
        if group["key"].startswith(("quality:", "relationship:")) or len(actions) <= 1:
            text = _render_recommendation(str(first.get("action") or ""), evidence, context, language)
            if text:
                lines.append(text)
            continue

        # For one real source, preserve both the data-quality and reset guidance
        # in a single sentence instead of emitting two near-duplicate bullets.
        index = _selection_index(context)
        row = index.get(evidence) or {}
        sources = {item.get("i"): item for item in context.get("sources") or []}
        comparisons = {item.get("i"): item for item in context.get("comparison_sets") or []}
        source = None
        if evidence.startswith("C"):
            source = sources.get(row.get("s"))
        elif evidence.startswith("F"):
            source = sources.get(row.get("s")) or sources.get((comparisons.get(row.get("c")) or {}).get("s"))
        elif evidence.startswith("S"):
            source = row
        label = _source_label(source or {}, language)
        has_reset = "verify_reconstructed_counter" in actions
        has_quality = bool(actions & {"collect_more_data", "monitor_source"})
        if language == "en":
            if has_reset and has_quality:
                lines.append(f"Monitor {label}; reassess it when the data are more representative and check future resets after counter reconstruction.")
            else:
                lines.append(_render_recommendation(str(first.get("action") or ""), evidence, context, language))
        else:
            if has_reset and has_quality:
                lines.append(f"Surveiller {label} ; réévaluer la situation lorsque les données seront plus représentatives et contrôler les prochains resets après reconstruction du compteur.")
            else:
                lines.append(_render_recommendation(str(first.get("action") or ""), evidence, context, language))
    return [line for line in lines if line]


def _render_selection_analysis(context: dict[str, Any], selection: dict[str, Any], language: str) -> str:
    language = "en" if language == "en" else "fr"
    summary_heading = "SUMMARY" if language == "en" else "SYNTHÈSE"
    attention_heading = "ATTENTION POINTS" if language == "en" else "POINTS D'ATTENTION"
    recommendation_heading = "RECOMMENDATIONS" if language == "en" else "RECOMMANDATIONS"

    def dedupe(items: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for text in items:
            key = " ".join(str(text).casefold().split())
            if key and key not in seen:
                seen.add(key)
                out.append(text)
        return out

    summary = dedupe([
        text for item_id in selection.get("summary") or []
        if (text := _render_ledger_id(item_id, context, language, "summary"))
    ])
    attention = dedupe([
        text for item_id in selection.get("attention") or []
        if (text := _render_ledger_id(item_id, context, language, "attention"))
    ])
    summary_keys = {" ".join(text.casefold().split()) for text in summary}
    attention = [text for text in attention if " ".join(text.casefold().split()) not in summary_keys]
    recommendations = dedupe(_merged_recommendation_lines(selection, context, language))

    if not summary:
        summary = ["No representative quantitative fact was selected." if language == "en" else "Aucun fait quantitatif représentatif n'a été sélectionné."]
    if not attention:
        attention = ["No notable attention point." if language == "en" else "Aucun point d'attention notable."]
    if not recommendations:
        recommendations = ["No specific recommendation." if language == "en" else "Aucune recommandation particulière."]

    return "\n".join([
        summary_heading,
        " ".join(summary),
        "",
        attention_heading,
        *[f"- {text}" for text in attention],
        "",
        recommendation_heading,
        *[f"- {text}" for text in recommendations],
    ]).strip()

def _encoded_context(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))


def build_budgeted_ai_context(
    result: dict[str, Any],
    target_chars: int = AI_TARGET_CONTEXT_CHARS,
) -> tuple[str, dict[str, Any]]:
    """Return RC6's deterministic shortlist while retaining the full ledger internally.

    The report data and complete fact ledger are preserved in HA Reporting. Only a
    deterministic shortlist of representative/significant facts is sent to the
    language model, which materially reduces local CPU inference time without
    allowing the model to invent values or comparisons.
    """
    legacy_json = _encoded_context(compact_report_context(result))
    full_context = _fact_ledger_context_v11(result)
    full_context_json = _encoded_context(full_context)
    context = _project_ai_context(full_context)
    context_json = _encoded_context(context)
    stats = context.get("ledger_stats") or {}
    metadata = {
        "schema": context.get("schema"),
        "mode": "deterministic_shortlist",
        "lossless": False,
        "report_data_lossless": True,
        "characters": len(context_json),
        "target_characters": target_chars,
        "limit_characters": AI_MAX_CONTEXT_CHARS,
        "legacy_characters": len(legacy_json),
        "full_compact_characters": len(full_context_json),
        "omitted_current_sources": 0,
        "omitted_comparison_sources": 0,
        "current_sources": (full_context.get("counts") or {}).get("current_sources", 0),
        "comparison_sources": (full_context.get("counts") or {}).get("comparison_sources", 0),
        "relationships": len(context.get("relationships") or []),
        "full_sources": stats.get("full_sources", 0),
        "shortlisted_sources": stats.get("shortlisted_sources", 0),
        "full_comparison_sets": stats.get("full_comparison_sets", 0),
        "shortlisted_comparison_sets": stats.get("shortlisted_comparison_sets", 0),
        "full_facts": stats.get("full_facts", 0),
        "shortlisted_facts": stats.get("shortlisted_facts", 0),
        "quality_signals": len(context.get("quality_signals") or []),
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
    """Ask the model to select ledger IDs only; HA Reporting writes the prose."""
    language = "en" if str(language).lower() == "en" else "fr"
    if language == "en":
        return f"""You are selecting evidence for a home-automation report calculated by HA Reporting.
Do not write the report and do not expose internal reasoning.
The context uses `ha-reporting-ai-context-v12`, a deterministic shortlisted fact ledger.

Your ONLY job is to select IDs already listed in `selection_policy`.
Return exactly one JSON object and nothing else:
{{"summary":["ID"],"attention":["ID"],"recommendations":[{{"action":"ACTION","evidence":"ID"}}]}}

Rules:
- `summary`: 1 to 4 eligible `F*`, `R*` or mandatory `Q*` IDs. Prefer current `mean`/`period_delta`/`integrated_energy_kwh`, representative comparison `mean`/`period_delta`, explicit relationships, and mandatory quality signals.
- `attention`: 0 to 5 eligible IDs. Prefer mandatory `Q*` quality signals, partial/limited/reconstructed comparison sets, quality-limited sources, or relationships whose full-period comparison is not supported.
- `recommendations`: 0 to 4 objects. `action` must be one of `selection_policy.recommendation_actions`; `evidence` must be an attention-worthy ID from the context.
- Return IDs only. Never return names, values, percentages, explanations, prose, markdown, code fences or extra keys.
- Prefer representative current-period energy/mean facts and explicit `relationships` over isolated power peaks.
- A `power_forecast_vs_actual` peak gap is context only and must not be selected as evidence for overload, calibration error or a fault.
- If a relationship has `full_period_comparison_supported=false`, it may be selected as an attention/coverage limitation, but never as evidence of a period performance gap.
- For N/N-x, prefer `comparable` facts for summary. Use `partial`, `limited`, `reconstructed` or sparse-zero items mainly as attention evidence.
- Do not invent cross-source comparisons. Do not calculate anything.
- This is a deterministic shortlist of the full HA Reporting ledger. Do not infer anything about omitted routine facts.

Validated HA Reporting context:
{context_json}
"""
    return f"""Tu sélectionnes les éléments à mettre en avant dans un rapport domotique calculé par HA Reporting.
N'écris pas le rapport et n'affiche aucun raisonnement interne.
Le contexte utilise `ha-reporting-ai-context-v12`, un registre déterministe de faits présélectionnés.

Ta SEULE tâche est de sélectionner des identifiants déjà présents dans `selection_policy`.
Retourne exactement un objet JSON et rien d'autre :
{{"summary":["ID"],"attention":["ID"],"recommendations":[{{"action":"ACTION","evidence":"ID"}}]}}

Règles :
- `summary` : 1 à 4 IDs `F*`, `R*` ou `Q*` obligatoires éligibles. Privilégie les `mean`/`period_delta`/`integrated_energy_kwh` courants, les `mean`/`period_delta` de comparaison représentative, les relations explicites et les signaux globaux de qualité obligatoires.
- `attention` : 0 à 5 IDs éligibles. Privilégie les signaux `Q*` obligatoires, les comparaisons partielles/limitées/reconstruites, les sources de qualité limitée ou les relations dont la comparaison de période complète n’est pas supportée.
- `recommendations` : 0 à 4 objets. `action` doit appartenir à `selection_policy.recommendation_actions` et `evidence` doit être un ID digne d’attention présent dans le contexte.
- Retourne uniquement des IDs. N'écris jamais de nom, valeur, pourcentage, explication, prose, markdown, bloc de code ni clé supplémentaire.
- Privilégie les énergies de période, moyennes représentatives et `relationships` explicites plutôt que les pics de puissance isolés.
- Un écart de pic dans `power_forecast_vs_actual` est seulement contextuel : il ne doit jamais servir de preuve de surcharge, mauvais calibrage ou panne.
- Si une relation contient `full_period_comparison_supported=false`, elle peut être sélectionnée comme limite de couverture, mais jamais comme preuve d'un écart de performance sur toute la période.
- Pour N/N-x, privilégie les faits `comparable` dans la synthèse. Utilise surtout les éléments `partial`, `limited`, `reconstructed` ou sparse-zero dans les points d'attention.
- N'invente aucune comparaison entre sources. Ne calcule rien.
- Ce contexte est une présélection déterministe du registre complet HA Reporting. N'infère rien à propos des faits routiniers non transmis au modèle.

Contexte validé par HA Reporting :
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
        context = json.loads(context_json)
        if len(context_json) > AI_MAX_CONTEXT_CHARS:
            if language == "en":
                message = f"AI shortlist context remains too large ({len(context_json)} characters, limit {AI_MAX_CONTEXT_CHARS})"
            else:
                message = f"Présélection IA encore trop volumineuse ({len(context_json)} caractères, limite {AI_MAX_CONTEXT_CHARS})"
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
        selection, selection_valid = _validate_selection(data, context)
        selection_fallback = not selection_valid
        if selection_fallback:
            selection = _fallback_selection(context)
        text = _render_selection_analysis(context, selection, language)

        finished = time.time()
        return {
            **base,
            "status": "completed",
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "conversation_id": conversation_id,
            "heartbeat_count": heartbeat_count,
            "text": text,
            "selection": selection,
            "selection_fallback": selection_fallback,
            "input": {
                "context_characters": context_meta["characters"],
                "context_target_characters": context_meta["target_characters"],
                "context_limit_characters": context_meta["limit_characters"],
                "context_original_characters": context_meta["full_compact_characters"],
                "context_legacy_characters": context_meta["legacy_characters"],
                "context_full_compact_characters": context_meta["full_compact_characters"],
                "context_mode": context_meta["mode"],
                "context_schema": context_meta["schema"],
                "context_lossless": context_meta["lossless"],
                "report_data_lossless": context_meta["report_data_lossless"],
                "context_full_sources": context_meta["full_sources"],
                "context_shortlisted_sources": context_meta["shortlisted_sources"],
                "context_full_comparison_sets": context_meta["full_comparison_sets"],
                "context_shortlisted_comparison_sets": context_meta["shortlisted_comparison_sets"],
                "context_full_facts": context_meta["full_facts"],
                "context_shortlisted_facts": context_meta["shortlisted_facts"],
                "context_quality_signals": context_meta["quality_signals"],
                "context_current_sources": context_meta["current_sources"],
                "context_comparison_sources": context_meta["comparison_sources"],
                "context_relationships": context_meta["relationships"],
                "selection_protocol": "id_only_v3_relationship_priority",
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

