# HA Reporting — 0.1.0-alpha.19

Quality-aware N / N-x comparison engine.

## Report comparison configuration

Reports can now request two explicit comparison families:

- **Previous periods**: N-1, N-2, N-3… periods of the report type.
- **Previous years**: the same date window one, two, three… years earlier.

The units are intentionally explicit. `N-1 period` is never silently treated as
`N-1 year`.

For a complete August 2026 monthly report:

- N-1 period = July 2026
- N-2 periods = June 2026
- N-1 year = August 2025

For a partial current period, both start and end are shifted so that elapsed
positions remain comparable (e.g. 1–25 September -> 1–25 August).

Custom periods use their exact duration for previous-period comparisons.

## Comparison statistics

Metric-aware comparison fields:

- power: peak, P95, mean
- temperature/humidity/voltage/current: min, mean, max
- energy: period delta
- runtime: period runtime
- cycles: period cycles

Each comparable field contains:

- N value
- reference value
- absolute difference
- relative difference (%) when reference != 0

## Quality-aware comparison status

Every source comparison is classified descriptively as:

- `comparable`
- `partial`
- `reconstructed`
- `unavailable`

Rules currently used:

- missing/no-data/invalid source -> unavailable
- reconstructed cumulative counter -> reconstructed
- period coverage below 95% -> partial
- for gauge metrics, sample density below 80% -> partial

Counter density is not used as an automatic partial criterion when direct
first-to-last delta is available; period coverage remains relevant.

The reasons and the N/reference quality metadata stay in normalized JSON.

## Execution

One report execution now runs N plus every configured comparison period and then
passes normalized results to the provider-independent ComparisonEngine.

The preview estimates the number of source queries before execution.

## Next milestone

Alpha.20 can consolidate the comparison UX/semantics and begin the reusable HTML
report-rendering layer once real N/N-x data has been validated.
