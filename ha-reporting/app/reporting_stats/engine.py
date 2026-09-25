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

        if metric in self.COUNTER_METRICS:
            stats = self._counter_stats(numeric)
        elif metric == "power":
            stats = self._power_stats(numeric)
        else:
            stats = self._gauge_stats(numeric)

        result["statistics"] = stats
        result["status"] = "ok"
        return result

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
