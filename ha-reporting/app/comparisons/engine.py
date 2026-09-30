from __future__ import annotations

from typing import Any


COVERAGE_GOOD_MIN = 95.0
COVERAGE_PARTIAL_MIN = 80.0
POWER_DENSITY_LIMITED_MAX = 2.0
POWER_DENSITY_PARTIAL_MAX = 10.0


class ComparisonEngine:
    """Compare normalized report executions source-by-source.

    The engine does not query providers. It only compares already normalized
    report executions, so it remains independent of VictoriaMetrics.
    """

    def compare_target(
        self,
        base_result: dict[str, Any],
        reference_result: dict[str, Any],
        target_meta: dict[str, Any],
    ) -> dict[str, Any]:
        reference_index = self._source_index(reference_result)

        counts = {
            "sources_total": 0,
            "sources_comparable": 0,
            "sources_partial": 0,
            "sources_limited": 0,
            "sources_reconstructed": 0,
            "sources_unavailable": 0,
        }
        catalogs_out = []

        for catalog in base_result.get("catalogs") or []:
            devices_out = []
            for device in catalog.get("devices") or []:
                sources_out = []
                device_id = (device.get("device") or {}).get("id")
                for source in device.get("sources") or []:
                    counts["sources_total"] += 1
                    key = (catalog.get("id"), device_id, source.get("sensor_key"))
                    reference = reference_index.get(key)
                    item = self._compare_source(source, reference)
                    sources_out.append(item)
                    status_key = {
                        "comparable": "sources_comparable",
                        "partial": "sources_partial",
                        "limited": "sources_limited",
                        "reconstructed": "sources_reconstructed",
                        "unavailable": "sources_unavailable",
                    }[item["comparison_status"]]
                    counts[status_key] += 1

                devices_out.append(
                    {
                        "id": device_id,
                        "name": (device.get("device") or {}).get("name", device_id),
                        "category": (device.get("device") or {}).get("category", "other"),
                        "sources": sources_out,
                    }
                )

            catalogs_out.append(
                {
                    "id": catalog.get("id"),
                    "name": catalog.get("name", catalog.get("id")),
                    "devices": devices_out,
                }
            )

        return {
            "id": target_meta["id"],
            "kind": target_meta["kind"],
            "offset": target_meta["offset"],
            "label": target_meta["label"],
            "resolved_period": reference_result.get("resolved_period"),
            "reference_execution": reference_result.get("execution"),
            "reference_summary": reference_result.get("summary"),
            "summary": counts,
            "catalogs": catalogs_out,
        }

    @staticmethod
    def _source_index(result: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
        output = {}
        for catalog in result.get("catalogs") or []:
            catalog_id = catalog.get("id")
            for device in catalog.get("devices") or []:
                device_id = (device.get("device") or {}).get("id")
                for source in device.get("sources") or []:
                    output[(catalog_id, device_id, source.get("sensor_key"))] = source
        return output

    def _compare_source(
        self,
        base: dict[str, Any],
        reference: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metric = base.get("metric")
        unit = base.get("unit")
        base_profile = self._quality_profile(base)
        reference_profile = self._quality_profile(reference)

        if reference is None:
            return self._unavailable_source(
                base,
                base_profile,
                reference_profile,
                "Source absente de la période de référence.",
            )

        if base_profile["availability"] != "available":
            return self._unavailable_source(
                base,
                base_profile,
                reference_profile,
                "La période N ne fournit pas une valeur comparable.",
            )

        if reference_profile["availability"] != "available":
            return self._unavailable_source(
                base,
                base_profile,
                reference_profile,
                "La période de référence ne fournit pas une valeur comparable.",
            )

        specs = self._stat_specs(metric)
        values = []
        base_stats = ((base.get("analysis") or {}).get("statistics") or {})
        reference_stats = ((reference.get("analysis") or {}).get("statistics") or {})

        relative_reasons = []
        for key, label, path in specs:
            base_value = self._nested_number(base_stats, path)
            reference_value = self._nested_number(reference_stats, path)
            if base_value is None or reference_value is None:
                continue
            absolute = base_value - reference_value
            relative_applicable = metric != "temperature"
            relative = None
            relative_reason = None
            if relative_applicable:
                if base_profile.get("sparse_zero_uncertain") or reference_profile.get("sparse_zero_uncertain"):
                    relative_applicable = False
                    relative_reason = "sparse_zero_uncertain"
                else:
                    floor = self._relative_reference_floor(metric, key, unit)
                    if abs(reference_value) < floor:
                        relative_applicable = False
                        relative_reason = "near_zero_reference"
                        relative_reasons.append(
                            f"{label}: pourcentage relatif non pertinent car la référence est proche de zéro."
                        )
                    else:
                        relative = absolute / abs(reference_value) * 100.0
            values.append(
                {
                    "key": key,
                    "label": label,
                    "base": base_value,
                    "reference": reference_value,
                    "absolute_change": absolute,
                    "relative_change_percent": relative,
                    "relative_change_applicable": relative_applicable,
                    "relative_change_reason": relative_reason,
                }
            )

        if not values:
            return self._unavailable_source(
                base,
                base_profile,
                reference_profile,
                "Aucune statistique commune comparable.",
            )

        status, reasons = self._comparison_quality(
            metric, base_profile, reference_profile
        )
        reasons.extend(relative_reasons)

        # A relative percentage from a limited comparison is mathematically
        # computable but analytically misleading because one side does not
        # represent the full period reliably. Keep the absolute gap and source
        # values, but suppress the percentage deterministically before rendering
        # or AI interpretation.
        if status == "limited":
            suppressed = False
            for item in values:
                if item.get("relative_change_percent") is not None:
                    suppressed = True
                item["relative_change_percent"] = None
                item["relative_change_applicable"] = False
                if not item.get("relative_change_reason"):
                    item["relative_change_reason"] = "limited_comparison"
            if suppressed:
                reasons.append(
                    "Pourcentage relatif masqué car la comparaison est limitée."
                )

        return {
            "sensor_key": base.get("sensor_key"),
            "entity_id": base.get("entity_id"),
            "metric": metric,
            "unit": unit,
            "comparison_status": status,
            "reasons": reasons,
            "base_quality": base_profile,
            "reference_quality": reference_profile,
            "values": values,
        }

    @staticmethod
    def _unavailable_source(base, base_profile, reference_profile, reason):
        return {
            "sensor_key": base.get("sensor_key"),
            "entity_id": base.get("entity_id"),
            "metric": base.get("metric"),
            "unit": base.get("unit"),
            "comparison_status": "unavailable",
            "reasons": [reason],
            "base_quality": base_profile,
            "reference_quality": reference_profile,
            "values": [],
        }

    @staticmethod
    def _stat_specs(metric: str) -> list[tuple[str, str, tuple[str, ...]]]:
        if metric == "power":
            return [
                ("max", "Pic", ("max", "value")),
                ("p95", "P95", ("p95",)),
                ("mean", "Moyenne", ("mean",)),
            ]
        if metric in {"temperature", "humidity", "voltage", "current", "energy_measurement"}:
            return [
                ("min", "Minimum", ("min", "value")),
                ("mean", "Moyenne", ("mean",)),
                ("max", "Maximum", ("max", "value")),
            ]
        if metric == "energy_total":
            return [("delta", "Consommation", ("delta",))]
        if metric == "runtime":
            return [("delta", "Temps de fonctionnement", ("delta",))]
        if metric == "cycles":
            return [("delta", "Cycles", ("delta",))]
        return []

    @staticmethod
    def _nested_number(data: dict[str, Any], path: tuple[str, ...]) -> float | None:
        value: Any = data
        for key in path:
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        return value

    @staticmethod
    def _relative_reference_floor(metric: str, key: str, unit: str | None) -> float:
        """Minimum meaningful reference magnitude for a relative percentage.

        Percentages against values that round to (or are operationally close to)
        zero are mathematically valid but analytically misleading.  0.2.0-rc.1 keeps
        the absolute gap and suppresses only the relative percentage.
        """
        normalized = str(unit or "").strip().casefold()
        if metric == "power":
            return 0.0001 if normalized == "kw" else 0.1
        if metric in {"energy_total", "energy_measurement"}:
            return 100.0 if normalized == "wh" else 0.1
        if metric == "runtime":
            if normalized in {"s", "sec", "second", "seconds"}:
                return 360.0
            if normalized in {"min", "minute", "minutes"}:
                return 6.0
            return 0.1
        if metric == "cycles":
            return 1.0
        if metric == "current":
            return 0.01
        if metric == "voltage":
            return 1.0
        if metric == "humidity":
            return 0.5
        return 1e-9

    @staticmethod
    def _near_zero_power_signal(statistics: dict[str, Any], unit: str | None) -> bool:
        """Return True only when the entire reported power signal is near zero."""
        threshold = 0.0001 if str(unit or "").strip().casefold() == "kw" else 0.1
        candidates = []
        maximum = ComparisonEngine._nested_number(statistics, ("max", "value"))
        mean = ComparisonEngine._nested_number(statistics, ("mean",))
        p95 = ComparisonEngine._nested_number(statistics, ("p95",))
        for value in (maximum, mean, p95):
            if value is not None:
                candidates.append(abs(value))
        return bool(candidates) and max(candidates) < threshold

    @staticmethod
    def _quality_profile(source: dict[str, Any] | None) -> dict[str, Any]:
        if source is None:
            return {
                "availability": "missing",
                "source_status": "missing",
                "period_coverage_percent": None,
                "sample_density_percent": None,
                "density_applicable": False,
                "counter_mode": None,
                "near_zero_signal": False,
                "sparse_zero_uncertain": False,
                "warnings": [],
            }

        status = source.get("status") or "error"
        analysis = source.get("analysis") or {}
        quality = analysis.get("quality") or {}
        validation = analysis.get("validation") or {}
        statistics = analysis.get("statistics") or {}
        available = status == "ok" and validation.get("valid", True)

        density_applicable = bool(quality.get("density_applicable"))
        density = quality.get("sample_density_percent") if density_applicable else None
        near_zero_signal = (
            source.get("metric") == "power"
            and ComparisonEngine._near_zero_power_signal(statistics, source.get("unit"))
        )
        sparse_zero_uncertain = bool(
            near_zero_signal
            and density is not None
            and density < POWER_DENSITY_PARTIAL_MAX
        )

        return {
            "availability": "available" if available else "unavailable",
            "source_status": status,
            "period_coverage_percent": quality.get("period_coverage_percent"),
            "sample_density_percent": density,
            "density_applicable": density_applicable,
            "counter_mode": statistics.get("mode"),
            "near_zero_signal": near_zero_signal,
            "sparse_zero_uncertain": sparse_zero_uncertain,
            "warnings": list(validation.get("warnings") or []),
        }

    @staticmethod
    def _comparison_quality(metric, base_profile, reference_profile):
        """Classify comparison reliability without discarding any source.

        0.2.0-rc.1 separates period coverage from sample density. Coverage below
        80% is limited; 80-95% is partial; >=95% is representative. For power
        sources, event-driven sampling density is only downgraded when it is very
        sparse (<10%), avoiding the old blanket 80% density threshold.
        """
        reasons = []
        profiles = [("N", base_profile), ("Référence", reference_profile)]

        reconstructed = False
        limited = False
        partial = False
        for label, profile in profiles:
            coverage = profile.get("period_coverage_percent")
            density = profile.get("sample_density_percent")
            mode = profile.get("counter_mode")

            if metric in {"energy_total", "runtime", "cycles"} and mode in {
                "reconstructed",
                "provider_reconstructed",
                "detailed_reconstructed",
            }:
                reconstructed = True
                reasons.append(f"{label}: compteur reconstruit après reset.")

            if coverage is not None:
                coverage = float(coverage)
                if coverage < COVERAGE_PARTIAL_MIN:
                    limited = True
                    reasons.append(
                        f"{label}: couverture de période {coverage:.1f} % ; comparaison limitée."
                    )
                elif coverage < COVERAGE_GOOD_MIN:
                    partial = True
                    reasons.append(
                        f"{label}: couverture de période {coverage:.1f} % ; comparaison partielle mais exploitable avec prudence."
                    )

            if metric == "power" and density is not None:
                density = float(density)
                if density < POWER_DENSITY_LIMITED_MAX:
                    limited = True
                    reasons.append(
                        f"{label}: densité d'échantillonnage extrêmement faible ({density:.1f} %)."
                    )
                elif density < POWER_DENSITY_PARTIAL_MAX:
                    partial = True
                    reasons.append(
                        f"{label}: densité d'échantillonnage faible ({density:.1f} %)."
                    )

            if profile.get("sparse_zero_uncertain"):
                limited = True
                reasons.append(
                    f"{label}: valeur de puissance proche de zéro avec historique très clairsemé ; "
                    "impossible de distinguer un vrai zéro d'un historique insuffisant."
                )

        if limited:
            return "limited", reasons
        if reconstructed:
            return "reconstructed", reasons
        if partial:
            return "partial", reasons
        return "comparable", reasons
