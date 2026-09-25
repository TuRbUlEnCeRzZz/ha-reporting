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
                "User-Agent": "HA-Reporting/0.1.0-alpha.17",
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
    def _metric_name_for_source(source: dict[str, Any]) -> str | None:
        """Return a known exact VM metric name when HA Reporting knows it.

        Unknown metric types deliberately return None. They are resolved through
        the entity labels instead of failing. This keeps the provider usable for
        temperature, humidity, voltage/current and future numeric sensors even
        when the VictoriaMetrics metric-name convention is not yet known.
        """
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

        return None

    @staticmethod
    def _escaped_entity_label(source: dict[str, Any]) -> str:
        entity_id = source.get("entity_id")
        if not entity_id:
            raise ProviderError("Source sans entity_id")

        entity_id = str(entity_id)
        if "." in entity_id:
            entity_id = entity_id.split(".", 1)[-1]

        return entity_id.replace("\\", "\\\\").replace('"', '\\"')

    @classmethod
    def label_selector_for_source(cls, source: dict[str, Any]) -> str:
        entity_id = cls._escaped_entity_label(source)
        return (
            f'{{db="homeassistant",domain="sensor",'
            f'entity_id="{entity_id}"}}'
        )

    @classmethod
    def expression_for_source(cls, source: dict[str, Any]) -> str:
        """Build the preferred query expression.

        Known HA/VM metric conventions use an exact metric name. Unknown numeric
        metrics fall back to a label-only selector so adding a new sensor type to
        a catalog does not require a provider-code change.
        """
        selector = cls.label_selector_for_source(source)
        metric_name = cls._metric_name_for_source(source)

        if metric_name:
            return metric_name + selector

        return selector

    @staticmethod
    def _series_name(series: dict[str, Any]) -> str:
        metric = series.get("metric") or {}
        return str(metric.get("__name__") or "<sans nom>")

    @classmethod
    def _select_single_series(
        cls,
        result: list[dict[str, Any]],
        source: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Select the numeric value series and ignore HA metadata series."""
        if not result:
            return None

        value_series = [
            series
            for series in result
            if cls._series_name(series).endswith("_value")
        ]

        if not value_series:
            names = sorted({cls._series_name(series) for series in result})
            raise ProviderError(
                "Aucune série numérique '*_value' trouvée pour "
                f"{source.get('entity_id')}. Séries trouvées: {', '.join(names)}"
            )

        if len(value_series) == 1:
            return value_series[0]

        unit = str(source.get("unit") or "").strip()
        if unit:
            expected_name = f"{unit}_value"
            exact_unit_matches = [
                series
                for series in value_series
                if cls._series_name(series) == expected_name
            ]
            if len(exact_unit_matches) == 1:
                return exact_unit_matches[0]

        names = sorted({cls._series_name(series) for series in value_series})
        raise ProviderError(
            "Plusieurs séries numériques VictoriaMetrics correspondent à "
            f"{source.get('entity_id')}: {', '.join(names)}"
        )

    def get_series(
        self,
        source: dict[str, Any],
        start: float,
        end: float,
        step: int | None = None,
    ) -> list[tuple[float, Any]]:
        requested_step = step or 300
        preferred_expression = self.expression_for_source(source)

        payload = self.range_query(
            preferred_expression,
            start,
            end,
            requested_step,
        )
        result = (payload.get("data") or {}).get("result") or []

        # If a known exact metric name did not produce data, fall back to the
        # entity labels. This makes the provider resilient to VM naming changes.
        exact_name = self._metric_name_for_source(source)
        if not result and exact_name:
            fallback_expression = self.label_selector_for_source(source)
            payload = self.range_query(
                fallback_expression,
                start,
                end,
                requested_step,
            )
            result = (payload.get("data") or {}).get("result") or []

        series = self._select_single_series(result, source)
        if series is None:
            return []

        values = series.get("values") or []
        output = []
        for timestamp, value in values:
            try:
                parsed: Any = float(value)
            except (TypeError, ValueError):
                parsed = value
            output.append((float(timestamp), parsed))
        return output

