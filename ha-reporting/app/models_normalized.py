from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedSeries:
    provider: str
    catalog_id: str
    device_id: str
    sensor_key: str
    entity_id: str
    metric: str
    unit: str | None
    start: float
    end: float
    step: int
    points: list[tuple[float, Any]]

    def summary(self) -> dict[str, Any]:
        numeric = [
            (ts, value)
            for ts, value in self.points
            if isinstance(value, (int, float))
        ]

        first = self.points[0] if self.points else None
        last = self.points[-1] if self.points else None
        minimum = min(numeric, key=lambda item: item[1]) if numeric else None
        maximum = max(numeric, key=lambda item: item[1]) if numeric else None
        mean = (
            sum(value for _, value in numeric) / len(numeric)
            if numeric else None
        )

        return {
            "provider": self.provider,
            "source": {
                "catalog_id": self.catalog_id,
                "device_id": self.device_id,
                "sensor_key": self.sensor_key,
                "entity_id": self.entity_id,
                "metric": self.metric,
                "unit": self.unit,
            },
            "period": {
                "start": self.start,
                "end": self.end,
                "step": self.step,
            },
            "statistics": {
                "points": len(self.points),
                "first": (
                    {"timestamp": first[0], "value": first[1]} if first else None
                ),
                "last": (
                    {"timestamp": last[0], "value": last[1]} if last else None
                ),
                "min": (
                    {"timestamp": minimum[0], "value": minimum[1]}
                    if minimum else None
                ),
                "max": (
                    {"timestamp": maximum[0], "value": maximum[1]}
                    if maximum else None
                ),
                "mean": mean,
            },
            # Alpha.9 includes a small preview only. The reporting engine can
            # consume the full internal `points` list without flooding the UI.
            "preview": [
                {"timestamp": ts, "value": value}
                for ts, value in self.points[:12]
            ],
        }
