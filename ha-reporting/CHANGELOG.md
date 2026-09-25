# Changelog

## 0.1.0-alpha.20

- Add DataProvider `report_rollup` capability.
- Add VictoriaMetrics server-side long-period report statistics.
- Automatically use optimized provider rollups for periods longer than 45 days.
- Keep detailed 300-second series mode for short periods.
- Preserve min/max timestamps, mean, P95, counter deltas and quality metadata in optimized reports.
- Add provider-side presence-based density for long periods.
- Mark provider counter reconstruction explicitly.
- Show execution strategy and estimated detailed points avoided in report preview.
- Remove physically meaningless relative-percent temperature comparisons.

## 0.1.0-alpha.19

- Add quality-aware N / N-1 / N-x comparisons.
