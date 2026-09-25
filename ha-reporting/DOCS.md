# HA Reporting — 0.1.0-alpha.21

Optimized-report reliability hardening.

## Targeted runtime fallback

Long reports still use fast provider-side rollups by default.

If a runtime rollup is reconstructed after resets, or exceeds the physical
duration of the source's actually observed first/last window, HA Reporting now
re-runs only that runtime source through the detailed series engine.

The fallback:
- is limited to the observed history window;
- preserves report-level coverage;
- reuses the already validated runtime reconstruction logic;
- is exposed as `series_fallback` in JSON;
- is counted in the report execution summary.

This keeps annual reports fast without trusting implausible rollup runtime
reconstruction.

## DST-safe elapsed durations

`ResolvedPeriod.duration_seconds` now uses epoch timestamps, so elapsed duration
is correct across CET/CEST changes.

Custom N-x periods also preserve exact elapsed seconds across DST boundaries.

## Metric-aware optimized quality

Provider-rollup sample density is retained for high-rate power sources.

For event-driven Home Assistant sources such as temperature, cumulative energy,
runtime and cycles, fixed 5-minute density is not meaningful and now displays:

`densité n/a`

Period coverage and raw sample count remain available.

## Beta-candidate direction

If annual N and N-1 values validate with alpha.21, the core data/statistics/
report/comparison engine is ready for beta-candidate consolidation.
