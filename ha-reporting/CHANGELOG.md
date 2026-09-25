# Changelog

## 0.1.0-alpha.13

- Fix Home Assistant update detection by returning to the single incremental
  alpha sequence (`alpha.12` -> `alpha.13`).
- Include the VictoriaMetrics dynamic numeric-source discovery fix originally
  prepared as `alpha.12.1`.
- Temperature and other numeric metrics can now be discovered by Home Assistant
  entity labels when no exact VictoriaMetrics metric-name mapping is known.
- Keep exact known mappings as the preferred fast path.
- Reject ambiguous multi-series matches explicitly.

## 0.1.0-alpha.12

- Non-destructive sensor editing.
- Runtime hardening.
