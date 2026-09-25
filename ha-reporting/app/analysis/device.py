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
    def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
        statuses = {
            "ok": 0,
            "no_data": 0,
            "invalid": 0,
            "unsupported": 0,
            "error": 0,
        }
        metric_counts: dict[str, int] = {}

        for item in results:
            status = item.get("status")
            if status in statuses:
                statuses[status] += 1
            metric = item.get("metric") or "unknown"
            metric_counts[metric] = metric_counts.get(metric, 0) + 1

        return {
            "sources_total": len(results),
            "sources_ok": statuses["ok"],
            "sources_no_data": statuses["no_data"],
            "sources_invalid": statuses["invalid"],
            "sources_unsupported": statuses["unsupported"],
            "sources_error": statuses["error"],
            "metrics": metric_counts,
        }
