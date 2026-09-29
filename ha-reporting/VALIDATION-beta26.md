# HA Reporting 0.1.0-beta.26 — Validation

## Scope

Beta.26 validates comparison-reliability rules and Home Assistant Ingress-safe PDF downloads on top of the beta.25 deterministic AI relationship layer.

The release keeps the lossless data policy: no current-period source or comparison source is removed because of poor coverage, low density or a near-zero reference. Instead, the comparison engine classifies reliability and suppresses only relative percentages that would be analytically misleading.

## Automated validation

Executed from the repository root:

```bash
PYTHONPATH=ha-reporting/app python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui.cjs
python3 -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
bash -n ha-reporting/run.sh
```

Results:

- **144 Python tests passed**.
- **95 JavaScript UI checks passed**.
- Python compilation passed.
- JavaScript syntax checks passed.
- `run.sh` shell syntax check passed.

## beta.26 regression coverage

The added regression coverage verifies that:

- >=95% period coverage remains representative;
- 80-95% coverage is classified as partial;
- <80% coverage is classified as limited;
- event-driven power histories with useful density (for example ~30%) are not automatically marked partial solely because density is below 80%;
- power density below 10% adds a partial reliability warning and below 2% marks the comparison limited;
- an all-near-zero power signal with sparse history is marked `sparse_zero_uncertain`;
- relative percentages are suppressed when a reference is too close to zero while absolute gaps remain present;
- sparse-zero comparisons also suppress relative percentages instead of presenting an uncertain `-100%` result;
- the comparison target summary counts the new `sources_limited` status;
- `ha-reporting-ai-context-v6` tells the AI how to interpret coverage tiers, near-zero references and sparse-zero uncertainty;
- deterministic forecast-versus-measured relationships require >=95% coverage on both sides before `full_period_comparison_supported` is true;
- the Documents download path uses same-origin `fetch()` + Blob handling and no longer opens the protected PDF endpoint in a new tab;
- French/English i18n includes the new Limited status and download-error message;
- package version, Paperless/VictoriaMetrics User-Agent strings and install layout are consistent with beta.26.

## Monthly-report reference cases

The observed monthly report motivated several specific safeguards:

- **Ventilation WC**: relative changes were extremely large because the reference was effectively zero. beta.26 keeps the absolute difference but suppresses the percentage when the reference falls below the metric-aware floor.
- **Ventilation SdB Parents**: a reference around `0.05 kWh` no longer yields a misleading several-hundred-percent headline; the absolute energy difference remains available.
- **Ceiling fan**: a reference with about `7.1%` coverage is classified as limited, so the AI may describe the available values but must not present the percentage as a reliable full-period trend.
- **Office PC zero values**: a near-zero power result with approximately `1%` sample density is marked uncertain rather than treated as confirmed inactivity.
- **Dishwasher / ordinary appliance power**: event-driven densities around 10-40% no longer make a high-coverage period partial by themselves.

## Manual Home Assistant OS checks recommended

After installing on Home Assistant OS:

1. Confirm the startup banner reports `HA Reporting 0.1.0-beta.26`.
2. Open **Documents** from the Home Assistant mobile app / Nabu Casa and download a generated PDF. Confirm the file downloads instead of opening a `401 Unauthorized` page.
3. Re-run the monthly N/N-1 report and confirm the comparison summary now includes **Limited** sources when appropriate.
4. Verify that near-zero references display the absolute difference without giant relative percentages.
5. Verify that a low-density, zero-valued power source is described as uncertain rather than definitely inactive.
6. Verify that high-coverage event-driven power histories are no longer downgraded only because density is below the previous 80% threshold.
7. Re-run the daily EMHASS report and confirm the 97.2% forecast coverage is treated as representative/full-period for deterministic relationships.

## Limitations

Desktop/unit validation cannot reproduce every Home Assistant Companion, browser, Nabu Casa or reverse-proxy behavior. The same-session Blob download is designed specifically to avoid losing the Ingress authentication context, but it should still be verified on the target mobile installation.

Comparison thresholds are intentionally explicit rather than inferred from device type. They improve interpretation of the observed report set without deleting data; future releases may expose threshold tuning if wider real-world use shows a need for it.
