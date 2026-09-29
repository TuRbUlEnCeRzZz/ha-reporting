# HA Reporting 0.1.0-beta.26

Beta.26 improves comparison reliability and fixes authenticated PDF downloads through Home Assistant Ingress / Nabu Casa.

## Highlights

- Added `ha-reporting-ai-context-v6` with explicit comparison-reliability rules for AI Task providers.
- Period coverage is now classified as:
  - **>=95%**: representative;
  - **80% to <95%**: partial but usable with caution;
  - **<80%**: limited and unsuitable for a full-period trend claim.
- Added a dedicated **Limited** comparison status to report summaries.
- Removed the old blanket rule that treated ordinary event-driven power histories as partial whenever sampling density was below 80%.
- Very sparse power histories remain protected: density below 10% adds a partial warning and below 2% marks the comparison limited.
- Near-zero reference values no longer generate misleading relative percentages such as `+47098%` or `+54276%`. HA Reporting keeps the absolute difference and all original data, but suppresses only the meaningless percentage.
- Sparse near-zero power histories are explicitly marked as uncertain so the AI does not conclude that a device was truly inactive when the history is too sparse.
- Deterministic forecast-versus-measured relationships now require **>=95% coverage on both sides** before they are described as full-period comparisons.
- Local PDF downloads now stay inside the authenticated Home Assistant Ingress session. The Documents page uses same-origin `fetch()` + Blob download instead of opening the protected document endpoint in a new browser tab, fixing the observed `401 Unauthorized` behavior through Nabu Casa / mobile browsers.

## Data-preservation policy

Beta.26 does **not** remove partial or limited data. Current-period sources, comparison sources and absolute differences remain available. The new rules only change how reliability is classified and when a relative percentage is considered meaningful.

## Upgrade notes

No report, catalogue or automation migration is required. Existing stored data and beta.25 deterministic forecast-versus-measured relationships remain compatible.

After upgrading, re-run a monthly comparison and verify that:

- references near zero show an absolute gap without an exaggerated percentage;
- low-coverage references are marked **Limited**;
- ordinary event-driven power sources with good period coverage are no longer downgraded solely because their density is below 80%;
- sparse zero-valued power histories are flagged as uncertain;
- PDF downloads from **Documents** work without opening a `401 Unauthorized` page.

## Validation

Validation passed with **144 Python tests** and **95 JavaScript UI checks**, plus Python compilation, JavaScript syntax, shell syntax and ZIP integrity checks. Regression coverage includes coverage tiers, the new limited status, near-zero percentage suppression, sparse-zero handling, deterministic relationship coverage, same-session document download behavior and all previous beta.25/beta.24/beta.23 functionality.

See `VALIDATION-beta26.md` for the complete validation record.
