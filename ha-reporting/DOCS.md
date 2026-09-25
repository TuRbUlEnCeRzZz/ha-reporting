# HA Reporting — 0.1.0-alpha.13

Hotfix for VictoriaMetrics source discovery.

## What was fixed

Alpha.12 still required a hardcoded VictoriaMetrics metric name for every HA Reporting metric type.
That meant a newly added temperature source failed with:

`Aucun mapping VictoriaMetrics défini pour metric='temperature', unit='°C'`

Alpha.12.1 removes that limitation for numeric sensors.

## Query strategy

Known mappings still use exact metric names first:

- power -> `W_value`
- energy_total -> `kWh_value`
- runtime -> `h_value`
- cycles -> `cycles_value`

For other numeric metrics, HA Reporting now queries VictoriaMetrics by Home Assistant labels:

`{db="homeassistant",domain="sensor",entity_id="..."}`

If an exact known mapping returns no data, HA Reporting also falls back to this label selector.

If exactly one series matches, it is used.
If several different series match the same entity labels, HA Reporting stops with an explicit ambiguity error instead of choosing silently.

This allows temperature, humidity, voltage/current and future numeric sensors to work without adding a new hardcoded metric-name mapping for each type.
