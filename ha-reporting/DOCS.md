# HA Reporting — 0.1.0-alpha.20

Long-period scalability + comparison semantics.

## Automatic execution strategy

HA Reporting now chooses between two retrieval modes:

### Detailed series
Used for periods up to 45 days.

The existing 300-second series workflow remains unchanged and is still used for
interactive/device analysis and short reports.

### Provider rollup
Used automatically for periods longer than 45 days.

Instead of transferring every 5-minute result to the add-on, HA Reporting asks
the DataProvider to calculate report primitives on the provider side.

VictoriaMetrics alpha.20 rollups use server-side MetricsQL functions for:
- first / last + timestamps;
- minimum / maximum + timestamps;
- mean;
- P95 for power;
- sample count;
- presence duration for data-quality estimation;
- resets / decreases / increase for cumulative counters.

The normalized report/statistics/comparison layers do not depend on MetricsQL.

## Why this matters

A 365-day period at 300 seconds represents 105,120 detailed positions per
source. Long reports no longer need to transfer all of these points just to
calculate a handful of report statistics.

The report preview shows:
- planned mode (`Détaillé` or `Optimisé`);
- estimated detailed points avoided when optimized.

## Quality on optimized reports

Long-period rollups retain:
- first/last timestamps;
- period coverage;
- provider-side presence-based sample density;
- raw sample count.

Exact gap count/largest gap are intentionally unavailable in rollup mode and are
displayed as unknown rather than fabricated.

## Counters

When no reset is detected, direct first-to-last delta remains preferred.

When VictoriaMetrics detects resets on a long period, alpha.20 can use a
provider-side reconstructed increase. The result is explicitly marked
`provider_reconstructed` and carries a warning so it is not confused with a
direct counter delta.

## Comparison semantics

Relative percentages are no longer calculated for temperature.

For Celsius/Fahrenheit-style temperature comparisons HA Reporting now reports:
- N;
- reference;
- absolute delta in °C/°F.

A relative percentage is intentionally omitted because the zero point of these
scales is arbitrary.

## Architecture

The DataProvider interface now advertises `report_rollup`.

This keeps the optimization modular: future providers can implement their own
server-side report statistics without changing the report/comparison engines.
