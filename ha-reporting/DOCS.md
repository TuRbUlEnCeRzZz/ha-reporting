# HA Reporting — 0.1.0-alpha.11

First complete-device analysis milestone.

## Complete device analysis

Expand a catalog and click **Analyser** on a device.

HA Reporting now:

1. loads every configured source of the device;
2. resolves the provider for each source;
3. queries each supported source independently;
4. applies metric-aware statistics;
5. keeps failures isolated;
6. returns one normalized device-level result.

A failed or unsupported source does not abort the whole device analysis.

## Current metric behavior

Supported numeric sources:
- power
- energy_total
- runtime
- cycles
- temperature
- humidity
- voltage
- current

`state` is explicitly marked as unsupported in alpha.11 rather than being silently misinterpreted as a numeric series.

## Device UI

Each source card shows:
- metric type;
- entity ID;
- main business statistic;
- supplemental statistic;
- observed sample density;
- number of points;
- detected gaps.

The page also provides:
- total sources;
- successfully analyzed sources;
- unsupported sources;
- errors;
- complete device JSON behind a collapsible section.

## Diagnostic wording

The former quality coverage value is presented as **observed sample density** in device analysis.

A low density is not automatically an error. It can be caused by:
- Home Assistant restarts;
- connectivity interruptions;
- provider gaps;
- a naturally sparse/event-driven source.

This diagnostic is intentionally retained because it can reveal inconsistencies without asserting their cause.

## Next step

The next milestone can begin turning this multi-source device result into a reusable report definition and period/comparison engine.
