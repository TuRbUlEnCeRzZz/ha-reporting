# HA Reporting 0.1.0-beta.24 — Validation

## Scope

beta.24 validates three related changes without altering the existing report scheduling/export pipeline:

1. generic power-to-energy integration as an optional source processing mode;
2. correct distinction between Home Assistant energy measurements and cumulative energy counters;
3. the self-describing, lossless `ha-reporting-ai-context-v4` contract.

## Automated validation

The final source tree was validated with:

```sh
python3 -m unittest discover -s tests -v
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
node tests/test_ui.cjs
python3 -m compileall -q ha-reporting/app custom_components/ha_reporting
bash -n ha-reporting/run.sh
```

Expected final results:

- **134 Python regression tests passed**;
- **87 JavaScript UI/i18n checks passed**;
- Python compilation succeeds;
- JavaScript syntax checks succeed;
- `run.sh` syntax check succeeds.

## beta.24 regression coverage

The added/updated regression checks verify that:

- a power rollup integral is converted from W·s to kWh correctly;
- detailed power history uses Home Assistant state semantics (the last value is held until the next change) and produces a consistent time-weighted mean and integrated energy;
- `derive_energy` is persisted only for `power` sources and is exposed in the analyzed report source;
- Home Assistant `state_class: measurement` energy sensors are auto-detected as `energy_measurement`, while cumulative energy remains `energy_total`;
- AI context v4 keeps `max`, `p95`, `mean`, `period_delta`, `counter_end` and `integrated_energy_kwh` as explicit named fields;
- partial current/comparison sources remain present and no source-omission path has been reintroduced;
- the AI prompt contains the v4 semantic rules that prohibit swapping max/mean values or presenting `counter_end` as period consumption;
- the source picker contains the state-class and processing controls, and FR/EN translations exist for the new power-integration UI.

## Manual Home Assistant OS checks recommended

On the reference Raspberry Pi 4 / Home Assistant OS installation:

1. Rebuild/install beta.24 and confirm the startup banner shows `HA Reporting 0.1.0-beta.24`.
2. Edit the EMHASS catalogue source `p_load_forecast` and select **Statistics + energy integration**.
3. Re-run the 05:30 → 05:30 daily EMHASS report.
4. Confirm the `p_load_forecast` card still shows peak/P95/mean and additionally shows **Integrated energy** in kWh.
5. Compare integrated energy against the existing VictoriaMetrics calculation for the same exact period. A value near the previous ~6.88 kWh reference is expected for the observed test period, but the live result is authoritative.
6. Re-run AI analysis and verify that forecast max/P95/mean are not swapped and forecast values are not described as measured electrical power.
7. Verify that cumulative electrical energy is described using the period delta, not the ending counter reading.
8. Add or inspect a Home Assistant kWh sensor with `state_class: measurement` and confirm the source picker proposes `energy_measurement` rather than `energy_total`.
9. Run at least one monthly report with partial historical sources to confirm that AI context v4 retains those sources and remains within the configured model context.

## Known boundary

HA Reporting does not know the tokenizer/context size of every AI Task provider. beta.24 therefore never removes report sources to satisfy the application-side preferred size. The provider may still reject an otherwise lossless request if its token context is too small; in that case, increase the provider context or use a model with a larger context rather than silently discarding report data.
