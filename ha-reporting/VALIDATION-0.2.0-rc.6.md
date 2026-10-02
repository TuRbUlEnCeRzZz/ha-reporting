# Validation — HA Reporting 0.2.0-rc.6

## Scope

RC6 is intentionally small. It validates three stabilization changes on top of RC5:

1. semantic `kWh` rendering for `integrated_energy_kwh` facts;
2. mandatory inclusion of validated forecast-versus-actual relationships in deterministic AI summaries;
3. merging of duplicate recommendation actions that target the same real source.

No report data, statistics engine, PDF layout, Paperless workflow, notification transport or VictoriaMetrics maintenance behavior is intentionally changed.

## Automated regression tests

Command:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Result:

```text
Ran 170 tests
OK
```

RC6 adds dedicated regression coverage for:

- rendering integrated forecast energy as `kWh` instead of inheriting the power source unit;
- mandatory summary injection of validated energy and mean-power forecast relationships even when the model omits them;
- deterministic rendering of those relationships with forecast/measured gaps;
- merging data-quality and reconstructed-counter recommendations for one source into a single bullet.

Expected warnings produced by tests that deliberately run without a Home Assistant Supervisor token or simulate an unavailable export provider remain non-failing test fixtures.

## JavaScript UI checks

Command:

```bash
node tests/test_ui.cjs
```

Result:

```text
99 JavaScript UI checks passed
```

## Static checks

The following commands completed successfully:

```bash
python -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
bash -n ha-reporting/run.sh
```

`ha-reporting/config.yaml` and `custom_components/ha_reporting/manifest.json` were also parsed successfully.

## AI contract

- Schema: `ha-reporting-ai-context-v12`
- Selection protocol: `id_only_v3_relationship_priority`
- Full fact ledger: retained internally
- Model-facing payload: deterministic RC5-style shortlist
- Quantitative prose: rendered by HA Reporting only
- Validated current-period forecast relationships: mandatory summary evidence
- Unsupported/partial forecast relationships: attention-only, with no synthetic full-period gap

## Real-world acceptance criteria

Before promoting to `0.2.0`, verify on the Home Assistant OS host:

- daily integrated forecast energy is shown as `kWh`;
- daily/monthly current-period forecast-versus-actual energy and mean-power relations are present when coverage is representative;
- incomplete historical forecast comparisons remain explicitly limited;
- monthly and annual shortlist latency remains close to RC5 behavior;
- duplicate recommendation bullets for one source are merged without hiding either data-quality or reset guidance;
- PDF download through Home Assistant / Nabu Casa remains functional.
