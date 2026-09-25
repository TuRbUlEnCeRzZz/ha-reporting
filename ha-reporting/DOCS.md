# HA Reporting — 0.1.0-alpha.8

First data-provider milestone.

## Architecture

Reporting code must depend on the generic `DataProvider` interface rather than querying VictoriaMetrics directly.

The provider layer now exposes a common conceptual interface for:

- series
- first / last
- min / max
- mean / sum
- max value with timestamp
- future state duration / state changes

## VictoriaMetrics

VictoriaMetrics is the first implemented provider.

The configuration is stored persistently in:

```text
/config/providers.yaml
```

No private/local URL is committed to the public GitHub repository.

Open **Sources de données** in HA Reporting, enter the VictoriaMetrics URL, then use **Tester la connexion**.

The test uses the standard `/api/v1/query` endpoint with a constant query (`1`), so it does not depend on a particular metric being present.

## Initial source mapping

Alpha.8 establishes the first conservative mapping already observed in the Home Assistant/VictoriaMetrics installation:

- power / W -> `W_value`
- energy_total / kWh -> `kWh_value`
- runtime / h -> `h_value`
- cycles -> `cycles_value`

The next milestone will validate this mapping against real catalog sensors and return normalized time-series data.
