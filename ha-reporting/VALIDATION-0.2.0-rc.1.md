# HA Reporting 0.2.0-rc.1 — Validation

## Scope

This release candidate validates the targeted changes introduced after beta.26:

- deterministic AI trend direction for full-period N/N-x comparisons;
- suppression of relative percentages for `limited` comparisons;
- prevention of current-period cross-source gap claims when HA Reporting has not validated a full-period relationship;
- preservation of beta.26 Ingress/Nabu Casa download behavior;
- package/version consistency for `0.2.0-rc.1`.

## Automated checks

- **147 Python regression tests passed**.
- **95 JavaScript UI checks passed**.
- Python modules compile successfully.
- `app.js` and `i18n.js` pass Node syntax checks.
- `run.sh` passes `bash -n`.
- YAML/JSON package metadata is parsed by the regression suite.
- ZIP integrity is checked after packaging.

## Targeted regression coverage

### Deterministic direction

Validated full-period comparison values now expose `trend_direction` as `increase`, `decrease` or `unchanged`. Regression coverage verifies that a positive dryer-style mean-power gap produces `increase` and that the AI instructions explicitly treat this direction as authoritative.

### Limited comparisons

When comparison quality is `limited`, all relative percentages are suppressed before rendering or AI serialization. Base/reference values and the absolute gap remain available. A 4.51 kWh vs 0.43 kWh comparison with only 7.1% reference coverage is therefore kept as an absolute 4.08 kWh gap without a `+945%` headline.

### Partial forecast coverage

A forecast/measured relationship with insufficient full-period coverage remains available as two source values plus coverage metadata, but `absolute_gap_*`, `relative_gap_*` and `trend_direction` are omitted. The relationship carries `comparison_policy: coverage_insufficient_for_period_gap`.

### AI context

`ha-reporting-ai-context-v7` remains lossless with respect to report statistics: current and comparison sources are not trimmed. The AI prompt explicitly forbids cross-source comparisons unless HA Reporting emitted a relationship and forbids reversing `trend_direction`.

### Document downloads

The beta.26 frontend path remains unchanged: the document is fetched through the current authenticated Ingress session and converted to a local Blob. Automated UI checks verify the function uses `fetch()` and does not use `window.open()`.

**Important:** automated desktop tests cannot prove that a live Nabu Casa/Companion authentication flow works on every device. A real remote/mobile download is intentionally part of the release-candidate acceptance test.

## Recommended Home Assistant OS acceptance test

On the actual Home Assistant OS installation:

1. Confirm the add-on log reports `HA Reporting 0.2.0-rc.1`.
2. Confirm existing catalogues/reports/automations are still present.
3. Run the daily EMHASS report and inspect the AI summary.
4. Run the large monthly N/N-x report and verify a positive deterministic gap is never described as a decrease.
5. Verify `limited` comparisons do not display relative percentages.
6. From Home Assistant through Nabu Casa/mobile, download a generated PDF and confirm it opens or downloads without `401 Unauthorized`.
7. Confirm the same PDF can still be exported to and opened from Paperless-ngx.

## Limitations

- AI output remains model-generated text. The RC reduces ambiguity and makes key comparison facts deterministic, but it cannot guarantee perfect natural-language phrasing from every AI provider.
- Local AI inference time depends on the selected model, CPU/GPU resources and context size.
- Desktop regression tests do not replace a live Home Assistant OS/Supervisor/Ingress/Nabu Casa test.
