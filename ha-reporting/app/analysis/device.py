from __future__ import annotations

from typing import Any, Callable

from reporting_stats.engine import MetricStatisticsEngine


class DeviceAnalysisEngine:
    """Analyze all usable sources of a device without coupling to a provider.

    `provider_resolver(provider_id)` must return an object exposing:
      - health_check()
      - get_series(source, start, end, step)

    A source failure never aborts the complete device analysis.
    """

    def __init__(self, provider_resolver: Callable[[str], Any]):
        self.provider_resolver = provider_resolver
        self.statistics = MetricStatisticsEngine()

    def analyze(
        self,
        *,
        catalog_id: str,
        catalog_name: str,
        device_id: str,
        device: dict[str, Any],
        default_provider: str,
        start: float,
        end: float,
        step: int,
        retrieval_mode: str = "series",
    ) -> dict[str, Any]:
        sensors = device.get("sensors") or {}
        results = []

        for sensor_key, source_raw in sensors.items():
            source = dict(source_raw or {})
            provider_id = source.get("provider") or default_provider
            metric = source.get("metric") or "state"

            item = {
                "sensor_key": sensor_key,
                "entity_id": source.get("entity_id", ""),
                "metric": metric,
                "unit": source.get("unit"),
                "provider": provider_id,
                "status": "pending",
            }

            # Alpha.11 deliberately avoids pretending that state history is
            # implemented through the numeric VictoriaMetrics mappings.
            if metric == "state":
                item.update(
                    {
                        "status": "unsupported",
                        "message": (
                            "Historique d'état non implémenté pour ce provider "
                            "dans alpha.11"
                        ),
                    }
                )
                results.append(item)
                continue

            try:
                provider = self.provider_resolver(provider_id)
                status = provider.health_check()
                if not status.available:
                    raise RuntimeError(status.message)

                if (
                    retrieval_mode == "provider_rollup"
                    and getattr(provider.capabilities, "report_rollup", False)
                ):
                    rollup = provider.get_report_statistics(
                        source,
                        start,
                        end,
                        quality_step=step,
                    )
                    analysis = self.statistics.analyze_rollup(
                        metric=metric,
                        rollup=rollup,
                        start=start,
                        end=end,
                        step=step,
                        unit=source.get("unit"),
                    )
                    points = []
                    points_count = int(
                        (analysis.get("quality") or {}).get(
                            "received_points", 0
                        ) or 0
                    )
                    source_retrieval_mode = "provider_rollup"

                    if (
                        metric == "runtime"
                        and self._runtime_rollup_needs_fallback(analysis)
                    ):
                        fallback = self._runtime_detailed_fallback(
                            provider=provider,
                            source=source,
                            rollup_analysis=analysis,
                            start=start,
                            end=end,
                            step=step,
                        )
                        if fallback is not None:
                            analysis = fallback["analysis"]
                            points = fallback["points"]
                            points_count = len(points)
                            source_retrieval_mode = "series_fallback"
                            item["fallback"] = {
                                "reason": "runtime_rollup_reconstruction",
                                "start": fallback["start"],
                                "end": fallback["end"],
                                "points": points_count,
                            }
                elif retrieval_mode == "provider_rollup":
                    raise RuntimeError(
                        f"Le provider '{provider_id}' ne supporte pas "
                        "l'analyse optimisée des longues périodes"
                    )
                else:
                    points = provider.get_series(source, start, end, step)
                    analysis = self.statistics.analyze(
                        metric=metric,
                        points=points,
                        start=start,
                        end=end,
                        step=step,
                        unit=source.get("unit"),
                    )
                    points_count = len(points)
                    source_retrieval_mode = "series"

                analysis_status = analysis.get("status")
                if analysis_status == "ok":
                    source_status = "ok"
                    message = None
                elif analysis_status == "invalid":
                    source_status = "invalid"
                    message = "Données présentes mais analyse statistique invalide."
                else:
                    source_status = "no_data"
                    message = "Pas d'historique disponible sur cette période."

                item.update(
                    {
                        "status": source_status,
                        "points": points_count,
                        "retrieval_mode": source_retrieval_mode,
                        "analysis": analysis,
                        "preview": [
                            {"timestamp": ts, "value": value}
                            for ts, value in points[:6]
                        ],
                    }
                )
                if message:
                    item["message"] = message
            except Exception as exc:
                item.update(
                    {
                        "status": "error",
                        "message": str(exc),
                    }
                )

            results.append(item)

        summary = self._summary(results)

        return {
            "catalog": {
                "id": catalog_id,
                "name": catalog_name,
            },
            "device": {
                "id": device_id,
                "name": device.get("name", device_id),
                "category": device.get("category", "other"),
            },
            "period": {
                "start": start,
                "end": end,
                "step": step,
                "duration_seconds": max(0.0, end - start),
                "retrieval_mode": retrieval_mode,
            },
            "summary": summary,
            "sources": results,
        }

    @staticmethod
    def _runtime_rollup_needs_fallback(analysis: dict[str, Any]) -> bool:
        if not analysis or analysis.get("status") == "no_numeric_data":
            return False
        statistics = analysis.get("statistics") or {}
        return (
            statistics.get("mode") == "provider_reconstructed"
            or statistics.get("plausible") is False
        )

    def _runtime_detailed_fallback(
        self,
        provider,
        source,
        rollup_analysis,
        start,
        end,
        step,
    ):
        quality = dict(rollup_analysis.get("quality") or {})
        first_ts = quality.get("first_timestamp")
        last_ts = quality.get("last_timestamp")

        if first_ts is None or last_ts is None:
            return None

        fallback_start = max(float(start), float(first_ts) - step)
        fallback_end = min(float(end), float(last_ts) + step)

        if fallback_end <= fallback_start:
            return None

        points = provider.get_series(
            source,
            fallback_start,
            fallback_end,
            step,
        )
        detailed = self.statistics.analyze(
            metric="runtime",
            points=points,
            start=fallback_start,
            end=fallback_end,
            step=step,
            unit=source.get("unit"),
        )

        if detailed.get("status") == "no_numeric_data":
            return None

        detailed_quality = dict(detailed.get("quality") or {})
        merged_quality = dict(quality)
        merged_quality["received_points"] = detailed_quality.get(
            "received_points", len(points)
        )
        merged_quality["observed_expected_points"] = detailed_quality.get(
            "expected_points",
            merged_quality.get("observed_expected_points", 0),
        )
        merged_quality["sample_density_percent"] = None
        merged_quality["density_applicable"] = False
        merged_quality["gap_count"] = detailed_quality.get("gap_count")
        merged_quality["largest_gap_seconds"] = detailed_quality.get(
            "largest_gap_seconds"
        )
        merged_quality["quality_method"] = (
            "provider_rollup_coverage+series_fallback"
        )
        detailed["quality"] = merged_quality
        detailed["retrieval_mode"] = "series_fallback"

        statistics = detailed.get("statistics") or {}
        resets = int(statistics.get("resets_detected", 0) or 0)
        statistics["mode"] = (
            "detailed_reconstructed" if resets > 0 else "detailed"
        )
        statistics["reconstruction_required"] = resets > 0
        statistics["fallback_window"] = {
            "start": fallback_start,
            "end": fallback_end,
            "duration_seconds": fallback_end - fallback_start,
        }

        validation = detailed.setdefault(
            "validation",
            {"valid": True, "issues": [], "warnings": []},
        )
        validation.setdefault("warnings", []).append(
            "Runtime vérifié par fallback détaillé sur la fenêtre réellement observée."
        )

        return {
            "analysis": detailed,
            "points": points,
            "start": fallback_start,
            "end": fallback_end,
        }

    @staticmethod
    def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
        statuses = {
            "ok": 0,
            "no_data": 0,
            "invalid": 0,
            "unsupported": 0,
            "error": 0,
        }
        metric_counts: dict[str, int] = {}
        fallback_count = 0

        for item in results:
            status = item.get("status")
            if status in statuses:
                statuses[status] += 1
            metric = item.get("metric") or "unknown"
            metric_counts[metric] = metric_counts.get(metric, 0) + 1
            if item.get("retrieval_mode") == "series_fallback":
                fallback_count += 1

        return {
            "sources_total": len(results),
            "sources_ok": statuses["ok"],
            "sources_no_data": statuses["no_data"],
            "sources_invalid": statuses["invalid"],
            "sources_unsupported": statuses["unsupported"],
            "sources_error": statuses["error"],
            "sources_fallback": fallback_count,
            "metrics": metric_counts,
        }
