from __future__ import annotations

from typing import Any


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

        for key, label, path in specs:
            base_value = self._nested_number(base_stats, path)
            reference_value = self._nested_number(reference_stats, path)
            if base_value is None or reference_value is None:
                continue
            absolute = base_value - reference_value
            relative = None
            if reference_value != 0:
                relative = absolute / abs(reference_value) * 100.0
            values.append(
                {
                    "key": key,
                    "label": label,
                    "base": base_value,
                    "reference": reference_value,
                    "absolute_change": absolute,
                    "relative_change_percent": relative,
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
        if metric in {"temperature", "humidity", "voltage", "current"}:
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
    def _quality_profile(source: dict[str, Any] | None) -> dict[str, Any]:
        if source is None:
            return {
                "availability": "missing",
                "source_status": "missing",
                "period_coverage_percent": None,
                "sample_density_percent": None,
                "counter_mode": None,
                "warnings": [],
            }

        status = source.get("status") or "error"
        analysis = source.get("analysis") or {}
        quality = analysis.get("quality") or {}
        validation = analysis.get("validation") or {}
        statistics = analysis.get("statistics") or {}
        available = status == "ok" and validation.get("valid", True)

        return {
            "availability": "available" if available else "unavailable",
            "source_status": status,
            "period_coverage_percent": quality.get("period_coverage_percent"),
            "sample_density_percent": quality.get("sample_density_percent"),
            "counter_mode": statistics.get("mode"),
            "warnings": list(validation.get("warnings") or []),
        }

    @staticmethod
    def _comparison_quality(metric, base_profile, reference_profile):
        reasons = []
        profiles = [("N", base_profile), ("Référence", reference_profile)]

        reconstructed = False
        partial = False
        for label, profile in profiles:
            coverage = profile.get("period_coverage_percent")
            density = profile.get("sample_density_percent")
            mode = profile.get("counter_mode")

            if metric in {"energy_total", "runtime", "cycles"} and mode == "reconstructed":
                reconstructed = True
                reasons.append(f"{label}: compteur reconstruit après reset.")

            if coverage is not None and coverage < 95.0:
                partial = True
                reasons.append(f"{label}: couverture de période {coverage:.1f} %.")

            if metric not in {"energy_total", "runtime", "cycles"}:
                if density is not None and density < 80.0:
                    partial = True
                    reasons.append(f"{label}: densité d'échantillonnage {density:.1f} %.")

        if reconstructed:
            return "reconstructed", reasons
        if partial:
            return "partial", reasons
        return "comparable", reasons
