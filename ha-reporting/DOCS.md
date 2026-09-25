# HA Reporting — 0.1.0-alpha.10

First metric-aware statistics milestone.

## Metric-aware calculations

Power:
- first / last
- minimum / maximum
- mean
- peak timestamp
- P95

Energy total / Runtime / Cycles:
- first / last
- delta over the selected period
- simple counter-reset detection

Temperature / Humidity / Voltage / Current:
- first / last
- minimum / maximum
- mean

## Data-quality diagnostics

Every normalized series now includes:
- expected points
- received points
- coverage percentage
- first / last timestamp
- gap count (> 1.5 × requested step)
- largest gap in seconds

This deliberately turns the real-source test view into a diagnostic tool.

## Next step

The next milestone can analyze a complete device at once (for example Vinothèque: power + energy + compressor runtime + cycles + state) instead of one source at a time.
