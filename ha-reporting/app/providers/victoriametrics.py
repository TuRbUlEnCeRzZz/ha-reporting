import json
import math
from decimal import Decimal, ROUND_CEILING
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
        report_rollup=True,
        raw_series=True,
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
                "User-Agent": "HA-Reporting/0.1.0-beta.8",
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

    def instant_query(
        self,
        expression: str,
        evaluation_time: float | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"query": expression}
        if evaluation_time is not None:
            params["time"] = evaluation_time
        return self._request_json("/api/v1/query", params)

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

    @staticmethod
    def _escape_label_value(value: Any) -> str:
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    @classmethod
    def numeric_selector_for_source(cls, source: dict[str, Any]) -> str:
        """Return a selector that resolves to the numeric value series only."""
        entity_id = cls._escaped_entity_label(source)
        metric_name = cls._metric_name_for_source(source)

        if metric_name:
            return (
                f'{metric_name}{{db="homeassistant",domain="sensor",'
                f'entity_id="{entity_id}"}}'
            )

        unit = str(source.get("unit") or "").strip()
        if unit:
            numeric_name = cls._escape_label_value(f"{unit}_value")
            return (
                f'{{__name__="{numeric_name}",db="homeassistant",domain="sensor",'
                f'entity_id="{entity_id}"}}'
            )

        raise ProviderError(
            "Statistiques optimisées impossibles: unité absente et nom de métrique "
            f"VictoriaMetrics inconnu pour {source.get('entity_id')}"
        )

    @staticmethod
    def _rollup_union(parts: list[tuple[str, str]]) -> str:
        return " or ".join(
            f'label_set({expression},"hr_stat","{name}")'
            for name, expression in parts
        )

    @classmethod
    def report_rollup_expression(
        cls,
        source: dict[str, Any],
        start: float,
        end: float,
        quality_step: int = 300,
    ) -> str:
        selector = cls.numeric_selector_for_source(source)
        first_ms, end_ms = cls._millisecond_bounds(start, end)
        window = f"{max(1, end_ms - first_ms)}ms"
        metric = str(source.get("metric") or "")
        max_interval = max(1, int(round(quality_step * 1.5)))

        common = [
            ("first", f"first_over_time({selector}[{window}])"),
            ("first_ts", f"tfirst_over_time({selector}[{window}])"),
            ("last", f"last_over_time({selector}[{window}])"),
            ("last_ts", f"tlast_over_time({selector}[{window}])"),
            ("count", f"count_over_time({selector}[{window}])"),
            (
                "present_duration",
                f"duration_over_time({selector}[{window}],{max_interval})",
            ),
        ]

        if metric in {"energy_total", "runtime", "cycles"}:
            common.extend(
                [
                    ("resets", f"resets({selector}[{window}])"),
                    ("decreases", f"decreases_over_time({selector}[{window}])"),
                    ("increase", f"increase_prometheus({selector}[{window}])"),
                ]
            )
            if metric == "runtime":
                common.extend([
                    ("descent", f"descent_over_time({selector}[{window}])"),
                    ("min", f"min_over_time({selector}[{window}])"),
                ])
        else:
            common.extend(
                [
                    ("min", f"min_over_time({selector}[{window}])"),
                    ("min_ts", f"tmin_over_time({selector}[{window}])"),
                    ("max", f"max_over_time({selector}[{window}])"),
                    ("max_ts", f"tmax_over_time({selector}[{window}])"),
                    ("mean", f"avg_over_time({selector}[{window}])"),
                ]
            )
            if metric == "power":
                common.append(
                    ("p95", f"quantile_over_time(0.95,{selector}[{window}])")
                )

        return cls._rollup_union(common)

    @staticmethod
    def _parse_rollup_result(payload: dict[str, Any]) -> dict[str, float]:
        result = ((payload.get("data") or {}).get("result") or [])
        output: dict[str, float] = {}

        for series in result:
            labels = series.get("metric") or {}
            stat = labels.get("hr_stat")
            raw_value = (series.get("value") or [None, None])[1]
            if not stat or raw_value is None:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue

            if stat in output:
                raise ProviderError(
                    f"Plusieurs séries numériques correspondent au rollup '{stat}'"
                )
            if not math.isfinite(value):
                raise ProviderError(f"Rollup non fini: {stat}")
            output[str(stat)] = value

        return output

    def get_report_statistics(
        self,
        source: dict[str, Any],
        start: float,
        end: float,
        quality_step: int = 300,
    ) -> dict[str, Any]:
        expression = self.report_rollup_expression(
            source,
            start,
            end,
            quality_step,
        )

        first_ms, end_ms = self._millisecond_bounds(start, end)
        # VM timestamps have millisecond precision. The lookbehind interval is
        # (evaluation-window, evaluation], exactly [ceil(start), ceil(end)) in ms.
        evaluation_time = str(Decimal(end_ms - 1) / 1000)
        payload = (
            self.instant_query(expression, evaluation_time=evaluation_time)
            if end_ms > first_ms else {"data": {"result": []}}
        )
        statistics = self._parse_rollup_result(payload)
        if source.get("metric") == "runtime" and statistics.get("count", 0) > 0:
            required = {"first", "last", "first_ts", "last_ts", "resets", "decreases", "min", "descent"}
            if not required.issubset(statistics):
                raise ProviderError("Rollup runtime incomplet")
            if not float(start) <= statistics["first_ts"] <= statistics["last_ts"] < float(end):
                raise ProviderError("Rollup runtime hors période")

        return {
            "provider": self.provider_id,
            "retrieval_mode": "provider_rollup",
            "query_time": evaluation_time,
            "period": {
                "start": float(start),
                "end": float(end),
                "quality_step": int(quality_step),
            },
            "values": statistics,
        }

    @staticmethod
    def _millisecond_bounds(start, end):
        if not (math.isfinite(float(start)) and math.isfinite(float(end))) or end <= start:
            raise ProviderError("Période invalide")
        return tuple(
            int((Decimal(str(value)) * 1000).to_integral_value(rounding=ROUND_CEILING))
            for value in (start, end)
        )

    RAW_POINT_LIMIT = 200_000
    RAW_BYTE_LIMIT = 32 * 1024 * 1024
    RAW_LINE_LIMIT = 1024 * 1024

    def get_raw_series(self, source, start, end):
        """Read original samples, never a five-minute query_range approximation.

        Limits fail closed rather than returning a silently truncated history.
        Multiple JSONL rows with the same labels belong to the same series.
        """
        if not self.configured:
            raise ProviderError("VictoriaMetrics n'est pas configuré")
        first_ms, end_ms = self._millisecond_bounds(start, end)
        if first_ms >= end_ms:
            return []
        params = {
            "match[]": self.numeric_selector_for_source(source),
            "start": str(Decimal(first_ms) / 1000),
            "end": str(Decimal(end_ms - 1) / 1000),
            "max_rows_per_line": 5000,
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/v1/export?{urllib.parse.urlencode(params)}",
            headers={"Accept": "application/stream+json", "User-Agent": "HA-Reporting/0.1.0-beta.8"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                def lines():
                    size = 0
                    while True:
                        line = response.readline(self.RAW_LINE_LIMIT + 1)
                        if not line:
                            return
                        size += len(line)
                        if len(line) > self.RAW_LINE_LIMIT or size > self.RAW_BYTE_LIMIT:
                            raise ProviderError("Export runtime trop volumineux; vérification interrompue")
                        yield line
                return self._parse_raw_export(lines(), first_ms, end_ms)
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"Export runtime VictoriaMetrics HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProviderError("Export runtime VictoriaMetrics indisponible") from exc

    @classmethod
    def _parse_raw_export(cls, lines, first_ms, end_ms):
        points = {}
        identity = None
        received = 0
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                labels = row["metric"]
                values, timestamps = row["values"], row["timestamps"]
                if not isinstance(labels, dict) or not labels.get("__name__", "").endswith("_value"):
                    raise ValueError("Série non numérique")
                if len(values) != len(timestamps):
                    raise ValueError("Timestamps et valeurs de tailles différentes")
                label_key = tuple(sorted(labels.items()))
                if identity is not None and label_key != identity:
                    raise ValueError("Plusieurs séries numériques correspondent à l'export")
                identity = label_key
                for timestamp, raw in zip(timestamps, values):
                    received += 1
                    if received > cls.RAW_POINT_LIMIT:
                        raise ValueError("Limite de points runtime dépassée")
                    ts, value = float(timestamp), float(raw)
                    if not math.isfinite(ts) or not math.isfinite(value) or ts != int(ts):
                        raise ValueError("Échantillon brut invalide")
                    if not first_ms <= ts < end_ms:
                        continue
                    if ts in points and points[ts] != value:
                        raise ValueError("Valeurs contradictoires au même timestamp")
                    points[ts] = value
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise ProviderError(f"Export runtime invalide: {exc}") from exc
        return [(ts / 1000, value) for ts, value in sorted(points.items())]

    def get_series(
        self,
        source: dict[str, Any],
        start: float,
        end: float,
        step: int | None = None,
    ) -> list[tuple[float, Any]]:
        requested_step = step or 300
        preferred_expression = self.expression_for_source(source)

        query_end = math.nextafter(float(end), -math.inf)
        payload = self.range_query(
            preferred_expression,
            start,
            query_end,
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
                query_end,
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
            ts = float(timestamp)
            if float(start) <= ts < float(end):
                output.append((ts, parsed))

        output.sort(key=lambda item: item[0])
        return output
