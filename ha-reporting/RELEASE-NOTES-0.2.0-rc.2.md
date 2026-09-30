# HA Reporting 0.2.0-rc.2

`0.2.0-rc.2` is a focused release candidate that hardens AI interpretation after real-world RC1 validation. No broad feature set is added in this release.

## Highlights

- Introduced `ha-reporting-ai-context-v8`.
- Made every N/N-x comparison record explicitly atomic and assigned it a compact `id`.
- Prevented AI providers from mixing the subject, statistic, trend direction, percentage, coverage or absolute gap from different comparison records.
- Required statements about averages to use `values.mean` only; min, max, P95, consumption/delta and other statistics must remain semantically isolated.
- Allowed a relative percentage only when the same statistic object explicitly contains `gap_pct`.
- Explicitly forbade turning an absolute gap such as `0.25 kWh` into an inferred percentage such as `25%` or `250%`.
- Kept coverage values scoped to the exact comparison or deterministic relationship that owns them.
- Preserved all current-period and comparison sources; no partial data is trimmed.
- Kept RC1 deterministic forecast/actual relationships, trend-direction metadata, coverage thresholds, sparse-zero safeguards and Limited comparison behavior unchanged.
- Kept notification behavior unchanged.
- Kept the authenticated same-session Ingress/Nabu Casa PDF download implementation unchanged.

## RC1 validation results carried into this RC

Real RC1 testing confirmed that two generated PDFs could be downloaded successfully through Home Assistant via Nabu Casa, validating the authenticated `fetch()` + Blob download path.

The daily EMHASS report also showed correct deterministic forecast/actual signs and coverage handling. The remaining monthly-report issue was narrower: the local AI model could still borrow information from neighbouring N/N-x records (for example a coverage value from another source or an absolute gap interpreted as a percentage). RC2 targets that failure mode directly.

## Upgrade notes

This release is intended to update cleanly from `0.2.0-rc.1` and earlier beta releases. Existing catalogues, reports, automations, documents and export settings remain compatible.

Recommended validation before promoting to `0.2.0` stable:

1. Run the daily EMHASS report and confirm forecast/actual relationships remain correct.
2. Run a large N/N-x monthly report and confirm AI text does not mix two devices/sources or swap mean/min/max semantics.
3. Confirm a suppressed percentage stays suppressed in the AI text when only an absolute gap is available.
4. Confirm local document download, Paperless export and scheduled automation behavior remain unchanged.

## Validation

Automated checks include Python regression tests, JavaScript UI checks, Python compilation, JavaScript syntax checks, shell syntax validation and ZIP integrity checks. See `VALIDATION-0.2.0-rc.2.md` for details and limitations.
