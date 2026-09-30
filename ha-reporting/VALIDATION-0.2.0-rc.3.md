# HA Reporting 0.2.0-rc.3 — Validation

## Scope

RC3 validates two focused changes before the planned 0.2.0 stable release:

1. the `ha-reporting-ai-context-v9` deterministic fact-ledger contract;
2. the first read-only VictoriaMetrics maintenance inventory.

## Automated validation

The following automated checks passed on the build artifact:

- **156 Python regression tests**;
- **95 JavaScript UI checks**;
- Python bytecode compilation for the add-on application and companion integration;
- JavaScript syntax validation for `app.js`;
- shell syntax validation for `run.sh`.

The regression suite includes explicit VictoriaMetrics maintenance protections:

- VictoriaMetrics entity inventory parsing and deduplication;
- active/orphaned/protected/indeterminate classification;
- a guard proving the maintenance analyzer does not call HA Reporting catalog loading;
- a guard proving no VictoriaMetrics maintenance delete route is exposed;
- UI checks confirming analysis-only wording and the Analyze endpoint.

## Maintenance architecture checked

RC3 maintenance analysis:

- reuses only the configured VictoriaMetrics URL;
- calls the VictoriaMetrics Prometheus-compatible `/api/v1/series` endpoint;
- reads the live Home Assistant entity set through the Supervisor/Core states API;
- does not reuse HA Reporting catalogs or report definitions;
- does not mutate VictoriaMetrics;
- has no automatic cleanup task;
- returns a read-only classification result with series counts and metric names.

The initial conservative policy treats absent `sensor` and `binary_sensor` entities as cleanup candidates (`orphaned`). Missing entities from other domains are marked `protected`. Incomplete VictoriaMetrics label metadata is marked `indeterminate`.

## AI contract checked

The v9 context keeps semantic source identity, unit, statistic and comparison identity atomic. Prompt rules require every quantitative statement to originate from exactly one fact or one explicit deterministic relationship. Cross-fact device pairing, unit substitution, unsupported relative percentages and peak-only fault diagnoses are prohibited by the model contract.

## Real-device validation still required

Automated tests cannot fully prove behavior against a real Home Assistant OS host, a live VictoriaMetrics data set or a specific local LLM. Before promoting RC3 to 0.2.0 stable, validate on the target Home Assistant OS installation:

1. daily EMHASS AI report interpretation;
2. large monthly N/N-x AI report interpretation;
3. VictoriaMetrics maintenance inventory counts and classifications;
4. confirmation that no maintenance operation changes VictoriaMetrics data;
5. PDF download through Home Assistant/Nabu Casa;
6. existing Paperless export and notification workflows.

## Result

**Automated RC3 validation: PASSED.**

Promotion to 0.2.0 stable remains dependent on real Home Assistant OS validation of the new fact-ledger interpretation and the maintenance inventory.
