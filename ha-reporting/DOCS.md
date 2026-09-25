# HA Reporting — 0.1.0-alpha.15

Metric-specific analysis cards + generic guardrails.

## Metric-specific cards

Device analysis no longer uses the generic "Complément" layout.

### Temperature / Humidity / Voltage / Current
- Minimum + timestamp
- Mean
- Maximum + timestamp

### Power
- Peak + timestamp
- P95
- Mean

### Energy total
- Period consumption
- Counter at start
- Counter at end
- Reset count

### Runtime
- Runtime during period
- Duty cycle (% of selected period)
- Ignored counter anomalies
- Reset count

### Cycles
- Cycles during period
- Counter at start
- Counter at end
- Reset count

## Generic statistical guardrails

The statistics engine now exposes a `validation` object.

Conservative invariants only are enforced:
- cumulative counter deltas must not be negative;
- runtime cannot exceed wall-clock duration;
- runtime ignored anomalies are surfaced as warnings;
- non-integer cycle deltas are flagged as warnings.

HA Reporting intentionally does not impose arbitrary temperature or humidity
ranges because valid domains can differ widely (freezer, room, oven, industrial
sensor, etc.).

## Next milestone

With catalogs, provider retrieval, normalization, statistics, diagnostics and
device analysis now stable enough, alpha.16 can start the report-definition and
period/comparison engine.
