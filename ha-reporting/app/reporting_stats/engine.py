from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DataQuality:
    expected_points: int
    observed_expected_points: int
    received_points: int
    period_coverage_percent: float | None
    sample_density_percent: float | None
    first_timestamp: float | None
    last_timestamp: float | None
    gap_count: int
    largest_gap_seconds: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "expected_points": self.expected_points,
            "observed_expected_points": self.observed_expected_points,
            "received_points": self.received_points,
            "period_coverage_percent": self.period_coverage_percent,
            "sample_density_percent": self.sample_density_percent,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "gap_count": self.gap_count,
            "largest_gap_seconds": self.largest_gap_seconds,
        }


class MetricStatisticsEngine:
    COUNTER_METRICS = {"energy_total", "runtime", "cycles"}
    GAUGE_METRICS = {"power", "temperature", "humidity", "voltage", "current"}

    def analyze(self, metric, points, start, end, step, unit=None):
        numeric = self._numeric_points(points, start, end)
        quality = self._quality(numeric, start, end, step)

        quality_dict = quality.as_dict()
        quality_dict["density_applicable"] = metric == "power"
        if metric != "power":
            quality_dict["sample_density_percent"] = None

        result = {
            "metric": metric,
            "unit": unit,
            "quality": quality_dict,
            "statistics": {},
            "status": "no_numeric_data",
        }

        if not numeric:
            return result

        if metric == "runtime":
            stats = self._runtime_stats(numeric, start, end)
        elif metric in {"energy_total", "cycles"}:
            stats = self._counter_stats(numeric, metric)
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
        result["status"] = "ok" if result["validation"]["valid"] else "invalid"
        return result

    @staticmethod
    def _validate(metric, statistics, start, end):
        issues = []
        warnings = []

        if metric in {"energy_total", "runtime", "cycles"}:
            delta = statistics.get("delta")
            if delta is not None and not math.isfinite(delta):
                issues.append("La variation du compteur doit être finie.")
            if delta is not None and delta < 0:
                issues.append("La variation d'un compteur cumulatif ne peut pas être négative.")
            if delta is None:
                issues.append("La variation du compteur n'a pas pu être déterminée de manière fiable.")

        if metric == "runtime":
            if statistics.get("negative_values", 0) > 0 or statistics.get("minimum_value", 0) < 0:
                issues.append("Un compteur runtime ne peut pas contenir de valeurs négatives.")
            period_hours = max(0.0, (end - start) / 3600.0)
            physical_limit = statistics.get(
                "physical_limit_hours",
                period_hours,
            )
            delta = statistics.get("delta")
            if delta is not None and delta > physical_limit * 1.05 + 0.10:
                issues.append(
                    "Le temps de fonctionnement dépasse la durée physique "
                    "de la fenêtre réellement observée."
                )
            if statistics.get("anomalies_ignored", 0) > 0:
                warnings.append(
                    f"{statistics.get('anomalies_ignored', 0)} anomalie(s) de compteur runtime ignorée(s)."
                )
            if statistics.get("mode") == "provider_reconstructed":
                warnings.append(
                    "Runtime reconstruit côté provider après détection de reset."
                )

        if metric in {"energy_total", "cycles"}:
            if statistics.get("reconstruction_required"):
                warnings.append(
                    f"Variation reconstruite à partir de {statistics.get('resets_detected', 0)} reset(s) détecté(s)."
                )
            if statistics.get("anomalies_ignored", 0) > 0:
                warnings.append(
                    f"{statistics.get('anomalies_ignored', 0)} baisse(s) de compteur jugée(s) non plausible(s) et ignorée(s)."
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

    def analyze_rollup(
        self,
        metric,
        rollup,
        start,
        end,
        step,
        unit=None,
    ):
        values = dict((rollup or {}).get("values") or {})
        quality = self._quality_from_rollup(
            metric,
            values,
            start,
            end,
            step,
        )

        result = {
            "metric": metric,
            "unit": unit,
            "quality": quality,
            "statistics": {},
            "status": "no_numeric_data",
            "retrieval_mode": "provider_rollup",
        }

        if not values or values.get("count", 0) <= 0:
            return result

        if metric in {"energy_total", "runtime", "cycles"}:
            statistics = self._counter_stats_from_rollup(
                metric,
                values,
                start,
                end,
            )
        else:
            statistics = self._gauge_stats_from_rollup(metric, values)

        result["statistics"] = statistics
        result["validation"] = self._validate(
            metric=metric,
            statistics=statistics,
            start=start,
            end=end,
        )
        result["status"] = (
            "ok" if result["validation"].get("valid", True) else "invalid"
        )
        return result

    @staticmethod
    def _quality_from_rollup(metric, values, start, end, step):
        duration = max(0.0, float(end) - float(start))
        expected = (
            int(math.ceil(duration / step))
            if step > 0 and duration > 0
            else 0
        )

        received = max(0, int(round(values.get("count", 0) or 0)))
        first_ts = values.get("first_ts")
        last_ts = values.get("last_ts")

        coverage = 0.0 if duration > 0 else None
        density = None
        observed_expected = 0

        density_applicable = metric == "power"

        if (
            first_ts is not None
            and last_ts is not None
            and duration > 0
            and step > 0
        ):
            observed_start = max(float(start), float(first_ts))
            observed_end = min(float(end), float(last_ts) + step)
            observed_span = max(0.0, observed_end - observed_start)
            coverage = min(100.0, observed_span / duration * 100.0)
            observed_expected = (
                int(math.ceil(observed_span / step))
                if observed_span > 0
                else 0
            )

            # Only the high-rate power stream uses fixed-step presence density.
            # Event-driven HA sensors legitimately publish only on state change.
            present_duration = values.get("present_duration")
            if (
                density_applicable
                and present_duration is not None
                and observed_span > 0
            ):
                density = min(
                    100.0,
                    max(0.0, float(present_duration)) / observed_span * 100.0,
                )

        return {
            "expected_points": expected,
            "observed_expected_points": observed_expected,
            "received_points": received,
            "period_coverage_percent": coverage,
            "sample_density_percent": density,
            "density_applicable": density_applicable,
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
            "gap_count": None,
            "largest_gap_seconds": None,
            "quality_method": (
                "provider_rollup_presence"
                if density_applicable
                else "provider_rollup_coverage"
            ),
        }

    @staticmethod
    def _gauge_stats_from_rollup(metric, values):
        statistics = {
            "first": {
                "timestamp": values.get("first_ts"),
                "value": values.get("first"),
            },
            "last": {
                "timestamp": values.get("last_ts"),
                "value": values.get("last"),
            },
            "min": {
                "timestamp": values.get("min_ts"),
                "value": values.get("min"),
            },
            "max": {
                "timestamp": values.get("max_ts"),
                "value": values.get("max"),
            },
            "mean": values.get("mean"),
        }
        if metric == "power":
            statistics["p95"] = values.get("p95")
        return statistics

    @staticmethod
    def _counter_stats_from_rollup(metric, values, start, end):
        first = values.get("first")
        last = values.get("last")
        first_ts = values.get("first_ts")
        last_ts = values.get("last_ts")
        resets = max(0, int(round(values.get("resets", 0) or 0)))
        decreases = max(0, int(round(values.get("decreases", 0) or 0)))
        provider_increase = values.get("increase")

        direct_delta = None
        if first is not None and last is not None:
            direct_delta = float(last) - float(first)

        if resets > 0 or (direct_delta is not None and direct_delta < 0):
            delta = (
                float(provider_increase)
                if provider_increase is not None
                else None
            )
            mode = "provider_reconstructed"
        elif direct_delta is not None:
            delta = direct_delta
            mode = "direct"
        else:
            delta = None
            mode = "undetermined"

        statistics = {
            "first": {"timestamp": first_ts, "value": first},
            "last": {"timestamp": last_ts, "value": last},
            "delta": delta,
            "direct_delta": direct_delta,
            "reconstructed_delta": (
                float(provider_increase)
                if provider_increase is not None
                else None
            ),
            "mode": mode,
            "reconstruction_required": mode == "provider_reconstructed",
            "resets_detected": resets,
            "negative_transitions": decreases,
            "anomalies_ignored": max(0, decreases - resets),
            "aggregation_source": "provider_rollup",
            "total_descent": values.get("descent"),
            "minimum_value": values.get("min", min(first or 0, last or 0)),
        }

        if metric == "runtime":
            report_limit = max(
                0.0,
                (float(end) - float(start)) / 3600.0,
            )
            if first_ts is not None and last_ts is not None:
                observed_limit = max(
                    0.0,
                    (float(last_ts) - float(first_ts)) / 3600.0,
                )
            else:
                observed_limit = report_limit

            plausible = (
                delta is not None
                and delta <= observed_limit * 1.05 + 0.10
            )
            statistics["physical_limit_hours"] = observed_limit
            statistics["report_period_limit_hours"] = report_limit
            statistics["plausible"] = plausible

        return statistics

    @staticmethod
    def _numeric_points(points, start, end):
        # Deduplicate, sort and enforce the report contract [start,end).
        by_timestamp = {}
        for ts, value in points:
            try:
                value = float(value)
                ts = float(ts)
            except (TypeError, ValueError):
                continue
            if not (math.isfinite(value) and math.isfinite(ts)):
                continue
            if ts < start or ts >= end:
                continue
            by_timestamp[ts] = value
        return sorted(by_timestamp.items(), key=lambda item: item[0])

    @staticmethod
    def _quality(points, start, end, step):
        timestamps = [float(ts) for ts, _ in points]
        duration = max(0.0, end - start)

        expected = (
            int(math.ceil(duration / step))
            if step > 0 and duration > 0
            else 0
        )
        received = len(timestamps)

        first_ts = timestamps[0] if timestamps else None
        last_ts = timestamps[-1] if timestamps else None

        observed_expected = 0
        period_coverage = 0.0 if duration > 0 else None
        sample_density = None

        if timestamps and step > 0 and duration > 0:
            observed_start = max(start, first_ts)
            observed_end = min(end, last_ts + step)
            observed_span = max(0.0, observed_end - observed_start)

            period_coverage = min(100.0, observed_span / duration * 100.0)
            observed_expected = (
                int(math.ceil(observed_span / step))
                if observed_span > 0
                else 0
            )
            if observed_expected > 0:
                sample_density = min(100.0, received / observed_expected * 100.0)

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
            observed_expected_points=observed_expected,
            received_points=received,
            period_coverage_percent=period_coverage,
            sample_density_percent=sample_density,
            first_timestamp=first_ts,
            last_timestamp=last_ts,
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

        physical_limit = max(0.0, (points[-1][0] - points[0][0]) / 3600.0)
        plausible = delta <= physical_limit * tolerance_factor + tolerance_hours
        negative_transitions = []
        transition_count = 0
        rounding_count = 0
        descent = 0.0
        for (prev_ts, prev), (ts, value) in zip(points, points[1:]):
            if value < prev:
                drop = prev - value
                descent += drop
                # Diagnostic only. This does not forgive a reset or relax any
                # physical allowance. 0.0005 h is half of a 0.001 h quantum.
                candidate = 0 < drop <= 0.0005 + 1e-12 and value > 0.02
                transition_count += 1
                rounding_count += int(candidate)
                if len(negative_transitions) < 20:
                    negative_transitions.append({
                        "previous_timestamp": prev_ts, "timestamp": ts,
                        "previous_value": prev, "value": value, "drop_hours": drop,
                        "rounding_compatible": candidate,
                    })

        return {
            "first": {"timestamp": first[0], "value": first[1]},
            "last": {"timestamp": points[-1][0], "value": points[-1][1]},
            "delta": delta if plausible else None,
            "raw_reconstructed_delta": delta,
            "resets_detected": resets,
            "anomalies_ignored": anomalies,
            "accepted_points": accepted_points,
            "negative_values": sum(value < 0 for _, value in points),
            "transition_diagnostics": {
                "negative_transitions": transition_count,
                "total_descent_hours": descent,
                "rounding_compatible_transitions": rounding_count,
                "examples": negative_transitions[:20],
                "examples_truncated": transition_count > 20,
                "rounding_tolerance_hours": 0.0005,
                "classification_only": True,
            },
            "physical_limit_hours": physical_limit,
            "plausible": plausible,
        }

    @staticmethod
    def _counter_stats(points, metric):
        first = points[0]
        last = points[-1]

        reconstructed_delta = 0.0
        resets = 0
        anomalies = 0
        negative_transitions = 0
        previous = first[1]

        def looks_like_reset(previous_value, current_value):
            if previous_value <= 0 or current_value < 0:
                return False
            absolute_floor = 2.0 if metric == "cycles" else 0.5
            relative_floor = abs(previous_value) * 0.10
            return current_value <= max(absolute_floor, relative_floor)

        for _, value in points[1:]:
            diff = value - previous
            if diff >= 0:
                reconstructed_delta += diff
            else:
                negative_transitions += 1
                if looks_like_reset(previous, value):
                    resets += 1
                    reconstructed_delta += max(0.0, value)
                else:
                    anomalies += 1
            previous = value

        direct_delta = last[1] - first[1]

        if resets > 0:
            delta = reconstructed_delta
            mode = "reconstructed"
        elif direct_delta >= 0:
            # Prefer first->last for monotonic cumulative counters; this is
            # robust to missing intermediate samples.
            delta = direct_delta
            mode = "direct"
        else:
            delta = None
            mode = "undetermined"

        return {
            "first": {"timestamp": first[0], "value": first[1]},
            "last": {"timestamp": last[0], "value": last[1]},
            "delta": delta,
            "direct_delta": direct_delta,
            "reconstructed_delta": reconstructed_delta,
            "mode": mode,
            "reconstruction_required": resets > 0,
            "resets_detected": resets,
            "negative_transitions": negative_transitions,
            "anomalies_ignored": anomalies,
        }
