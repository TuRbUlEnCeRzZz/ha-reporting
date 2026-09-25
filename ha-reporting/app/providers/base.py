from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """Raised when a data provider cannot complete a request."""


@dataclass(frozen=True)
class ProviderCapabilities:
    series: bool = False
    first: bool = False
    last: bool = False
    minimum: bool = False
    maximum: bool = False
    mean: bool = False
    sum: bool = False
    max_timestamp: bool = False
    state_duration: bool = False
    state_changes: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {
            "series": self.series,
            "first": self.first,
            "last": self.last,
            "min": self.minimum,
            "max": self.maximum,
            "mean": self.mean,
            "sum": self.sum,
            "max_timestamp": self.max_timestamp,
            "state_duration": self.state_duration,
            "state_changes": self.state_changes,
        }


@dataclass
class ProviderStatus:
    provider_id: str
    configured: bool
    available: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.provider_id,
            "configured": self.configured,
            "available": self.available,
            "message": self.message,
            "details": self.details,
        }


class DataProvider(ABC):
    """Common interface consumed by the reporting engine.

    Provider-specific transport and query details stay behind this boundary.
    Later reporting/statistics code should depend on this class, not directly
    on VictoriaMetrics.
    """

    provider_id: str
    capabilities: ProviderCapabilities

    @abstractmethod
    def health_check(self) -> ProviderStatus:
        raise NotImplementedError

    @abstractmethod
    def get_series(
        self,
        source: dict[str, Any],
        start: float,
        end: float,
        step: int | None = None,
    ) -> list[tuple[float, Any]]:
        raise NotImplementedError

    def get_first(self, source: dict[str, Any], start: float, end: float) -> Any:
        series = self.get_series(source, start, end)
        return series[0][1] if series else None

    def get_last(self, source: dict[str, Any], start: float, end: float) -> Any:
        series = self.get_series(source, start, end)
        return series[-1][1] if series else None

    def get_min(self, source: dict[str, Any], start: float, end: float) -> Any:
        values = [value for _, value in self.get_series(source, start, end)]
        return min(values) if values else None

    def get_max(self, source: dict[str, Any], start: float, end: float) -> Any:
        values = [value for _, value in self.get_series(source, start, end)]
        return max(values) if values else None

    def get_mean(self, source: dict[str, Any], start: float, end: float) -> Any:
        values = [value for _, value in self.get_series(source, start, end)]
        return (sum(values) / len(values)) if values else None

    def get_sum(self, source: dict[str, Any], start: float, end: float) -> Any:
        values = [value for _, value in self.get_series(source, start, end)]
        return sum(values) if values else None

    def get_max_with_timestamp(
        self, source: dict[str, Any], start: float, end: float
    ) -> tuple[float, Any] | None:
        series = self.get_series(source, start, end)
        return max(series, key=lambda item: item[1]) if series else None
