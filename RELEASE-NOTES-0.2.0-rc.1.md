# HA Reporting 0.2.0-rc.1

`0.2.0-rc.1` is the first release candidate for the planned 0.2.0 stable milestone. It focuses on locking down AI interpretation and comparison reliability rather than adding broad new features.

## Highlights

- Added `ha-reporting-ai-context-v7`.
- Added authoritative `trend_direction` metadata (`increase`, `decrease`, `unchanged`) for validated full-period N/N-x statistics so an AI provider cannot legitimately reverse the direction of a deterministic comparison.
- Restricted current-period cross-source comparisons to deterministic HA Reporting `relationships`; the AI is explicitly instructed not to invent comparisons between unrelated totals, means, peaks or energies.
- When forecast/measured coverage is insufficient for a full-period comparison, HA Reporting preserves both values and their coverage but no longer exposes an absolute or relative performance gap. This prevents partial forecast energy from being compared directly with a complete measured period.
- Suppressed relative percentages for `limited` comparisons while preserving the base value, reference value and absolute difference.
- Kept beta.26 comparison-quality tiers, sparse-zero safeguards and near-zero reference handling.
- Kept the beta.26 same-session Ingress/Nabu Casa PDF download implementation (`fetch()` + local Blob) unchanged for release-candidate validation.
- Preserved every current and comparison source in the AI context; no partial data is trimmed.

## Why this RC exists

The beta.26 monthly-report validation exposed two remaining interpretation risks: a local AI model reversed the sign of a deterministic dryer comparison, and a partially covered EMHASS forecast was compared against a complete measured month. The RC moves both decisions further into HA Reporting's deterministic layer.

## Upgrade notes

This release is intended to update cleanly from `0.1.0-beta.26`. Existing catalogues, reports, automations, documents and export settings remain compatible.

Recommended validation before promoting to `0.2.0`:

1. Run a daily EMHASS report and confirm forecast/measured relationships are correct.
2. Run a large N/N-x monthly report and confirm deterministic increase/decrease directions are not reversed by the AI.
3. Confirm limited comparisons show absolute gaps without misleading relative percentages.
4. Download at least one PDF from the Home Assistant mobile/remote path through Nabu Casa and confirm no `401 Unauthorized` page appears.
5. Confirm Paperless-ngx export and local document storage still work.

## Validation

Automated release-candidate checks include Python regression tests, JavaScript UI checks, Python compilation, JavaScript syntax checks, shell syntax validation and ZIP integrity checks. See `VALIDATION-0.2.0-rc.1.md` for details and limitations.
