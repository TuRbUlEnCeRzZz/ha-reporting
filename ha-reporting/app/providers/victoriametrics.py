import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .base import DataProvider, ProviderCapabilities, ProviderError, ProviderStatus


class VictoriaMetricsProvider(DataProvider):
    provider_id = "victoria_metrics"

    capabilities = ProviderCapabilities(
        series=True,
        first=True,
        last=True,
        minimum=True,
        maximum=True,
        mean=True,
        sum=True,
        max_timestamp=True,
        state_duration=False,
        state_changes=False,
    )

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = (base_url or "").strip().rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def _request_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise ProviderError("VictoriaMetrics n'est pas configuré")

        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}{path}?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "HA-Reporting/0.1.0-alpha.8",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"VictoriaMetrics HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"Connexion VictoriaMetrics impossible: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ProviderError("Délai de connexion VictoriaMetrics dépassé") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError("Réponse VictoriaMetrics non JSON") from exc

        if payload.get("status") != "success":
            raise ProviderError(payload.get("error") or "VictoriaMetrics a retourné une erreur")

        return payload

    def instant_query(self, expression: str) -> dict[str, Any]:
        return self._request_json("/api/v1/query", {"query": expression})

    def range_query(
        self,
        expression: str,
        start: float,
        end: float,
        step: int = 300,
    ) -> dict[str, Any]:
        return self._request_json(
            "/api/v1/query_range",
            {
                "query": expression,
                "start": start,
                "end": end,
                "step": step,
            },
        )

    def health_check(self) -> ProviderStatus:
        if not self.configured:
            return ProviderStatus(
                provider_id=self.provider_id,
                configured=False,
                available=False,
                message="URL non configurée",
                details={"capabilities": self.capabilities.as_dict()},
            )

        try:
            # A constant expression validates the MetricsQL/Prometheus API
            # without depending on the presence of a particular user metric.
            payload = self.instant_query("1")
            data = payload.get("data") or {}
            return ProviderStatus(
                provider_id=self.provider_id,
                configured=True,
                available=True,
                message="Connexion réussie",
                details={
                    "url": self.base_url,
                    "result_type": data.get("resultType"),
                    "capabilities": self.capabilities.as_dict(),
                },
            )
        except ProviderError as exc:
            return ProviderStatus(
                provider_id=self.provider_id,
                configured=True,
                available=False,
                message=str(exc),
                details={
                    "url": self.base_url,
                    "capabilities": self.capabilities.as_dict(),
                },
            )

    @staticmethod
    def _metric_name_for_source(source: dict[str, Any]) -> str:
        # Alpha.8 establishes the abstraction only. The mapping is deliberately
        # conservative and mirrors the metric names already observed in the
        # user's VictoriaMetrics installation.
        metric = source.get("metric")
        unit = source.get("unit")

        if metric == "power" or unit == "W":
            return "W_value"
        if metric == "energy_total" or unit == "kWh":
            return "kWh_value"
        if metric == "runtime" or unit == "h":
            return "h_value"
        if metric == "cycles" or unit == "cycles":
            return "cycles_value"

        raise ProviderError(
            f"Aucun mapping VictoriaMetrics défini pour metric={metric!r}, unit={unit!r}"
        )

    @classmethod
    def expression_for_source(cls, source: dict[str, Any]) -> str:
        metric_name = cls._metric_name_for_source(source)
        entity_id = source.get("entity_id")
        if not entity_id:
            raise ProviderError("Source sans entity_id")

        # HA entity IDs are controlled by the user's own HA installation.
        # Escape quote/backslash defensively before embedding the label value.
        entity_id = str(entity_id).replace("\\", "\\\\").replace('"', '\\"')
        return (
            f'{metric_name}{{db="homeassistant",domain="sensor",'
            f'entity_id="{entity_id.split(".", 1)[-1]}"}}'
        )

    def get_series(
        self,
        source: dict[str, Any],
        start: float,
        end: float,
        step: int | None = None,
    ) -> list[tuple[float, Any]]:
        expression = self.expression_for_source(source)
        payload = self.range_query(expression, start, end, step or 300)
        result = (payload.get("data") or {}).get("result") or []
        if not result:
            return []

        # The expected source is a single HA entity time series.
        values = result[0].get("values") or []
        output = []
        for timestamp, value in values:
            try:
                parsed: Any = float(value)
            except (TypeError, ValueError):
                parsed = value
            output.append((float(timestamp), parsed))
        return output
