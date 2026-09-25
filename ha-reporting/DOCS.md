# HA Reporting — 0.1.0-alpha.16

Report definitions + period engine.

## Reports are now persistent objects

Definitions are stored in:

`/config/reports/*.yaml`

A report currently contains:
- stable ID;
- display name;
- one or more catalogs;
- period definition.

Report definitions can be created, edited, previewed and deleted from the UI.

## Period engine

Supported shortcuts:
- day;
- week (Monday start);
- month;
- quarter;
- semester;
- year;
- custom start/end.

For standard periods, a report can target:
- the current period (start -> now);
- the previous complete period.

All shortcuts are resolved into explicit timezone-aware bounds:

`[start, end)`

The Home Assistant configured timezone is used.

## Report preview / planning

Alpha.16 deliberately does not execute VictoriaMetrics queries for a whole report yet.

Preview resolves:
- exact start/end;
- timezone;
- selected catalogs;
- enabled devices;
- source counts;
- normalized report-plan JSON.

This separates period/scope correctness from the heavier report execution stage.

## Next stage

The next stage can execute this normalized report plan through DataProvider and
produce a multi-catalog report result. Comparison N/N-1/N-x can then operate on
the same resolved-period abstraction.
