# Validation — HA Reporting 0.2.0-rc.8

This document records the automated and targeted validation performed for `0.2.0-rc.8`.

## Release scope

RC8 is intentionally limited to two final hardening areas before the planned `0.2.0` stable release:

1. a denser, sortable and collapsible UX for Automations and Documents;
2. stricter semantic validation of AI recommendation evidence, plus a more conservative Automatic context policy.

The deterministic reporting engine, PDF generation, Paperless export, VictoriaMetrics read-only maintenance and Home Assistant notification behavior are otherwise unchanged from RC7.

## AI contract

Schema: `ha-reporting-ai-context-v14`

Selection protocol: `id_only_v5_recommendation_guard`

The model continues to return IDs/actions only. HA Reporting remains responsible for numeric calculations, units, relationship eligibility and final quantitative prose.

RC8 adds a dedicated semantic check for `verify_reconstructed_counter`: the recommendation is accepted only when the selected evidence itself contains reconstructed/reset semantics (`st=reconstructed`, `br=true` or `rr=true`). The same check is applied again during recommendation rendering/merging.

## Automatic context policy

Automatic mode is now conservative:

- Complete only for small ledgers;
- Extended only for medium ledgers;
- Optimized for substantial ledgers.

Explicit Optimized, Extended and Complete selections remain available and unchanged.

## UX validation

The Automations view now includes:

- per-card collapse/expand controls;
- persisted expansion state;
- automatic expansion for active jobs;
- sort by creation date, name, next run, last start, last finish, duration and status;
- persisted ascending/descending direction;
- Collapse all / Expand all.

The Documents view now includes the same list interaction model, with sorting by generation date, name, period start/end, report type and file size.

New automations persist `created_at`. Legacy definitions without that field infer it from the oldest retained execution history when available.

## Automated regression results

### Python

Command:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Result: **179 tests passed**.

Targeted RC8 regression coverage includes:

- reconstructed-counter recommendation accepted when the evidence itself is reconstructed;
- reconstructed-counter recommendation rejected when the evidence is only limited/partial and contains no reconstruction proof;
- conservative Automatic context selection for large reports;
- `created_at` persistence across automation updates;
- legacy automation creation-time inference from retained history.

### JavaScript UI

Command:

```bash
node tests/test_ui.cjs
```

Result: **118 checks passed**.

RC8 UI checks cover the new Automation/Document sort controls, collapse/expand functions, last-finish metadata, list i18n strings and shared sort primitives in addition to the existing regression suite.

## Syntax and build checks

The following checks passed:

```bash
python -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
bash -n ha-reporting/run.sh
```

YAML/JSON metadata parsing also passed. Both add-on metadata and the companion integration manifest report version `0.2.0-rc.8`.

## Compatibility target

The release remains targeted at **Home Assistant OS**, primarily the project's Raspberry Pi 4 `aarch64` reference installation, while also declaring `amd64` support. The reference Home Assistant Core installation is kept current as new Core releases become available.

## Manual validation recommended after upgrade

Before promoting RC8 to stable, run at least:

1. one daily EMHASS report in Optimized mode;
2. one monthly N/N-1 report in Optimized mode;
3. one annual N/N-1 report in Optimized mode;
4. one explicit Extended run if the richer context mode is still desired;
5. Automation list collapse/expand and sorting on desktop and mobile;
6. Document list collapse/expand, sorting and PDF download through Home Assistant / Nabu Casa.

The AI text should still be treated as commentary. The deterministic data and report sections remain the authoritative reference.

## Archive checks

The full release archive and the GitHub web-update archive were both verified with `unzip -t` and reported no compressed-data errors.

The GitHub update package contains **21 changed/new files** relative to `0.2.0-rc.7`, with **no deleted files**, so it stays well below GitHub's 100-file web-upload limit.
