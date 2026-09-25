from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DataQuality:
    expected_points: int
    received_points: int
    coverage_percent: float | None
    first_timestamp: float | None
    last_timestamp: float | None
    gap_count: int
    largest_gap_seconds: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "expected_points": self.expected_points,
            "received_points": self.received_points,
            "coverage_percent": self.coverage_percent,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "gap_count": self.gap_count,
            "largest_gap_seconds": self.largest_gap_seconds,
        }


class MetricStatisticsEngine:
    COUNTER_METRICS = {"energy_total", "runtime", "cycles"}
    GAUGE_METRICS = {"power", "temperature", "humidity", "voltage", "current"}

    def analyze(self, metric, points, start, end, step, unit=None):
        numeric = self._numeric_points(points)
        quality = self._quality(points, start, end, step)

        result = {
            "metric": metric,
            "unit": unit,
            "quality": quality.as_dict(),
            "statistics": {},
            "status": "no_numeric_data",
        }

        if not numeric:
            return result

        if metric == "runtime":
            stats = self._runtime_stats(numeric, start, end)
        elif metric in self.COUNTER_METRICS:
            stats = self._counter_stats(numeric)
        elif metric == "power":
            stats = self._power_stats(numeric)
        else:
            stats = self._gauge_stats(numeric)

        result["statistics"] = stats
        result["validation"] = self._validate(
            metric=metric,
            statistics=stats,
            start=start,
            end=end,
        )
        result["status"] = (
            "ok"
            if result["validation"].get("valid", True)
            else "invalid"
        )
        return result

    @staticmethod
    def _validate(metric, statistics, start, end):
        """Apply conservative plausibility checks without inventing domain limits.

        HA Reporting deliberately avoids arbitrary temperature/humidity ranges:
        a freezer, sauna or industrial sensor may legitimately be outside
        household ranges. Guardrails only enforce invariants that are generally
        true for the metric type.
        """
        issues = []
        warnings = []

        if metric in {"energy_total", "runtime", "cycles"}:
            delta = statistics.get("delta")
            if delta is not None and delta < 0:
                issues.append("La variation d'un compteur cumulatif ne peut pas être négative.")

        if metric == "runtime":
            period_hours = max(0.0, (end - start) / 3600.0)
            delta = statistics.get("delta")
            if delta is not None and delta > period_hours * 1.05 + 0.02:
                issues.append("Le temps de fonctionnement dépasse la durée physique de la période.")
            if statistics.get("anomalies_ignored", 0) > 0:
                warnings.append(
                    f"{statistics.get('anomalies_ignored', 0)} anomalie(s) de compteur ignorée(s)."
                )

        if metric == "cycles":
            delta = statistics.get("delta")
            if delta is not None and abs(delta - round(delta)) > 1e-6:
                warnings.append("Le nombre de cycles n'est pas entier.")

        return {
            "valid": not issues,
            "issues": issues,
            "warnings": warnings,
        }

    @staticmethod
    def _numeric_points(points):
        output = []
        for ts, value in points:
            try:
                value = float(value)
                ts = float(ts)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and math.isfinite(ts):
                output.append((ts, value))
        return output

    @staticmethod
    def _quality(points, start, end, step):
        timestamps = [float(ts) for ts, _ in points]
        expected = int(math.floor((end - start) / step)) + 1 if step > 0 and end >= start else 0
        received = len(points)
        coverage = min(100.0, received / expected * 100.0) if expected else None

        gap_count = 0
        largest_gap = None
        if len(timestamps) >= 2:
            gaps = [
                timestamps[i] - timestamps[i - 1]
                for i in range(1, len(timestamps))
                if timestamps[i] >= timestamps[i - 1]
            ]
            if gaps:
                largest_gap = max(gaps)
                threshold = step * 1.5 if step > 0 else 0
                gap_count = sum(1 for gap in gaps if gap > threshold)

        return DataQuality(
            expected_points=expected,
            received_points=received,
            coverage_percent=coverage,
            first_timestamp=timestamps[0] if timestamps else None,
            last_timestamp=timestamps[-1] if timestamps else None,
            gap_count=gap_count,
            largest_gap_seconds=largest_gap,
        )

    @staticmethod
    def _gauge_stats(points):
        values = [value for _, value in points]
        minimum = min(points, key=lambda item: item[1])
        maximum = max(points, key=lambda item: item[1])
        return {
            "first": {"timestamp": points[0][0], "value": points[0][1]},
            "last": {"timestamp": points[-1][0], "value": points[-1][1]},
            "min": {"timestamp": minimum[0], "value": minimum[1]},
            "max": {"timestamp": maximum[0], "value": maximum[1]},
            "mean": sum(values) / len(values),
        }

    @classmethod
    def _power_stats(cls, points):
        base = cls._gauge_stats(points)
        ordered = sorted(value for _, value in points)
        rank = max(1, math.ceil(0.95 * len(ordered)))
        base["p95"] = ordered[rank - 1]
        return base


    @staticmethod
    def _runtime_stats(points, start, end):
        """Reconstruct runtime conservatively using wall-clock limits."""
        if not points:
            return {}

        tolerance_factor = 1.05
        tolerance_hours = 0.02
        first = points[0]
        accepted_ts, accepted_value = first
        delta = 0.0
        resets = 0
        anomalies = 0
        accepted_points = 1

        for ts, value in points[1:]:
            elapsed_h = max(0.0, (ts - accepted_ts) / 3600.0)
            allowance = elapsed_h * tolerance_factor + tolerance_hours
            diff = value - accepted_value

            if diff >= 0:
                if diff <= allowance:
                    delta += diff
                    accepted_ts, accepted_value = ts, value
                    accepted_points += 1
                else:
                    anomalies += 1
            else:
                if value >= 0 and value <= allowance:
                    resets += 1
                    delta += value
                    accepted_ts, accepted_value = ts, value
                    accepted_points += 1
                else:
                    anomalies += 1

        physical_limit = max(0.0, (end - start) / 3600.0)
        plausible = delta <= physical_limit * tolerance_factor + tolerance_hours

        return {
            "first": {"timestamp": first[0], "value": first[1]},
            "last": {"timestamp": points[-1][0], "value": points[-1][1]},
            "delta": delta if plausible else None,
            "raw_reconstructed_delta": delta,
            "resets_detected": resets,
            "anomalies_ignored": anomalies,
            "accepted_points": accepted_points,
            "physical_limit_hours": physical_limit,
            "plausible": plausible,
        }

    @staticmethod
    def _counter_stats(points):
        first = points[0]
        last = points[-1]
        delta = 0.0
        resets = 0
        previous = first[1]

        for _, value in points[1:]:
            diff = value - previous
            if diff >= 0:
                delta += diff
            else:
                resets += 1
                delta += max(0.0, value)
            previous = value

        return {
            "first": {"timestamp": first[0], "value": first[1]},
            "last": {"timestamp": last[0], "value": last[1]},
            "delta": delta,
            "resets_detected": resets,
        }
