# Changelog

## 0.1.0-alpha.14

- Ignore VictoriaMetrics Home Assistant metadata `*_str` series.
- Select the actual numeric `*_value` series automatically.
- Prefer exact `<unit>_value` when several numeric candidates exist.
- Preserve explicit ambiguity errors when a safe choice is impossible.
- Fix temperature entities exposing multiple metadata series.

## 0.1.0-alpha.13

- Dynamic VictoriaMetrics source discovery.
- Update-safe alpha version numbering.
