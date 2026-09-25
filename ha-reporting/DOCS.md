# HA Reporting — 0.1.0-alpha.14

VictoriaMetrics numeric-series resolver.

A Home Assistant numeric entity can expose several VictoriaMetrics series using
the same labels. For a temperature entity this can include:

- `°C_device_class_str`
- `°C_friendly_name_str`
- `°C_state_class_str`
- `°C_value`

Only the `*_value` series contains the numeric sensor history.

Alpha.14 therefore:
1. ignores metadata `*_str` series;
2. keeps only numeric `*_value` candidates;
3. uses the only numeric candidate when unique;
4. if several numeric candidates remain, prefers exact `<unit>_value`;
5. still returns an explicit ambiguity error when selection cannot be made safely.

The resolver is generic and applies to temperature, humidity, voltage, current
and future numeric Home Assistant sensors following the same VM convention.
