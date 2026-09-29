# HA Reporting 0.1.0-beta.25 — Validation

## Scope

Beta.25 validates deterministic cross-source AI relationships on top of the beta.24 lossless self-describing AI context. The deterministic statistics, power integration, document pipeline, scheduler, exports and long-running AI transport remain in place.

The release specifically verifies that HA Reporting performs important forecast-versus-measured arithmetic before the AI Task call instead of asking the language model to infer source pairing or recalculate gaps.

## Automated validation

Executed from the repository root with the add-on application on `PYTHONPATH`:

```bash
PYTHONPATH=ha-reporting/app python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui.cjs
python3 -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
bash -n ha-reporting/run.sh
```

Results:

- **137 Python tests passed**.
- **87 JavaScript UI checks passed**.
- Python compilation passed.
- JavaScript syntax checks passed.
- `run.sh` shell syntax check passed.

## beta.25 regression coverage

The added regression coverage verifies that:

- `ha-reporting-ai-context-v5` preserves self-describing named source values;
- one forecast power source with `integrated_energy_kwh` and one measured cumulative energy source produce an `energy_forecast_vs_actual` relationship;
- the relationship exposes actual energy, forecast energy, absolute gap, relative gap, both coverage values and `full_period_comparison_supported`;
- one forecast power source and one measured power source produce a `power_forecast_vs_actual` relationship containing deterministic mean-power gap plus P95/max context;
- partial source coverage is preserved and marks the relationship as unsuitable for a full-period conclusion instead of removing any source;
- ambiguous energy pairing does not cause HA Reporting to guess: no energy relationship is emitted when more than one candidate measured energy source exists;
- AI instructions require available deterministic energy relationships to be included in the summary and prohibit recalculating their values;
- the beta.24 power-integration and source-semantic tests still pass;
- the beta.23 long-running AI timeout/WebSocket tests still pass;
- package version, Paperless/VictoriaMetrics User-Agent strings and install layout are consistent with beta.25.

## EMHASS reference scenario

A deterministic reference scenario matching the observed daily EMHASS report was exercised with:

- forecast power mean: `287.4 W`;
- forecast power maximum: `428.9 W`;
- integrated forecast energy: `6.89 kWh`;
- forecast coverage: `97.2%`;
- measured power mean: `343.5 W`;
- measured power maximum: `4216.4 W`;
- measured period energy: `8.22 kWh`;
- measured coverage: `100%`.

The generated relationships are:

- energy gap: `+1.33 kWh`;
- relative energy gap: `+19.303%` using forecast energy as the reference;
- mean-power gap: `+56.1 W`;
- relative mean-power gap: `+19.52%`;
- full-period comparison supported: `true`.

This arithmetic is now performed by HA Reporting and supplied to the AI Task as authoritative structured data.

## Manual Home Assistant OS checks recommended

After installing on Home Assistant OS:

1. Confirm the add-on startup banner reports `HA Reporting 0.1.0-beta.25`.
2. Re-run the daily EMHASS report with `p_load_forecast` configured for **Statistics + energy integration**.
3. Confirm the deterministic report still shows approximately `6.89 kWh` integrated forecast energy and the measured values expected for the same `[start, end)` period.
4. Confirm the AI summary includes actual period energy, integrated forecast energy, absolute gap and relative gap when the pairing is unambiguous.
5. Confirm the AI does not replace the energy comparison with only peak-power commentary.
6. Test a partial-coverage report and verify the AI qualifies the relationship instead of presenting it as a reliable full-period result.
7. Re-run a larger monthly report to confirm no current/comparison source is omitted from the lossless context.

## Limitations

Desktop/unit validation does not prove the behavior of every Home Assistant AI Task provider or local model. The language model may still phrase interpretations differently, but beta.25 removes the source-pairing and arithmetic burden for the supported deterministic relationships. If a device contains multiple candidate measured energy or measured power sources, HA Reporting intentionally refuses to guess a relationship; all original source records remain available in the AI context.
