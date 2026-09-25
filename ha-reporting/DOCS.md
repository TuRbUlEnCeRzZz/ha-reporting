# HA Reporting — 0.1.0-alpha.17

First real report-execution milestone.

## Report execution

A planned report can now be executed from its preview.

Execution:
1. freezes the report's resolved period;
2. loads all selected catalogs;
3. loads each enabled device;
4. analyzes every configured source through DataProvider;
5. reuses the metric-aware statistics engine;
6. isolates source failures;
7. aggregates one normalized multi-catalog report result.

The final result contains only source summaries/previews, not all raw points, so
memory remains bounded per queried source.

## Current execution resolution

Alpha.17 uses a 300-second query step, identical to the validated device-analysis
workflow. The step is included explicitly in execution metadata.

Long-period query optimization will be handled before beta so that annual reports
can remain accurate without unnecessary VictoriaMetrics load.

## UI

The report preview now offers:

- `Actualiser la période`
- `Exécuter le rapport`

Executed reports display:
- exact resolved period;
- execution duration;
- device/source status totals;
- catalog -> device -> source hierarchy;
- metric-specific source cards;
- full normalized report JSON.

## Period wording

French labels were also corrected:
- `Mois précédent`
- `Semaine précédente`
- `Année précédente`
etc.

## Next milestone

The normalized executed report is now ready for a comparison engine:
- N vs previous period;
- same period previous year;
- N-x offsets.
