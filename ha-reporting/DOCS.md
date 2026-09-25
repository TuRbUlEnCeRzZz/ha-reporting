# HA Reporting — 0.1.0-alpha.9

First real catalog -> DataProvider -> VictoriaMetrics -> normalized-series milestone.

## Provider save feedback

`Tester la connexion` and `Enregistrer` now have distinct feedback:

- Test -> `Connexion VictoriaMetrics réussie`
- Save -> `Configuration enregistrée · VictoriaMetrics connecté`
- A configuration can still be saved while VictoriaMetrics is temporarily unavailable.

## Real series test

Open **Sources de données** and use **Test d'une source réelle**.

Choose:

1. a catalog;
2. a device;
3. a sensor;
4. a period (1 h, 6 h, 24 h, 7 days).

HA Reporting resolves the source from the persistent catalog, calls the generic `DataProvider`, queries VictoriaMetrics, then returns a normalized result.

The UI displays:

- number of points;
- first value;
- last value;
- mean;
- maximum;
- a JSON preview of the normalized result.

## Normalized structure

The internal result separates:

- provider;
- source identity and metric;
- period;
- statistics;
- time-series points.

This structure is deliberately provider-independent so later statistics/reporting code does not depend directly on VictoriaMetrics.

## Scope

Alpha.9 is a data retrieval/normalization milestone, not yet the final statistics engine.

The next step can introduce metric-aware calculations (energy delta/increase, power peak timestamp, runtime/cycle differences, etc.) on top of normalized provider data.
