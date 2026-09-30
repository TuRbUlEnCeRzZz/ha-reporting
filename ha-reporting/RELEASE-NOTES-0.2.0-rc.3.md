# HA Reporting 0.2.0-rc.3

`0.2.0-rc.3` is the final release-candidate hardening step currently planned before 0.2.0 stable. It focuses on deterministic AI interpretation and introduces the first read-only VictoriaMetrics maintenance inventory.

## Highlights

- Introduces `ha-reporting-ai-context-v9`, a deterministic atomic fact ledger for AI interpretation.
- Keeps every semantic current-period and N/N-x value while preventing the model from legitimately mixing statistics, sources, units or comparison identities.
- Requires every quantitative AI statement to be grounded in one atomic fact or one explicit HA Reporting relationship.
- Prevents unsupported cross-device comparisons, invented percentages, unit changes and peak-only diagnoses such as overload, bad calibration, bad sensor placement or hardware faults.
- Adds **Settings → Maintenance → VictoriaMetrics** as a standalone diagnostic module.
- Uses the existing VictoriaMetrics connection and the live Home Assistant entity set directly.
- Does **not** read, reuse or depend on HA Reporting catalogs.
- Inventories Home Assistant-labelled VictoriaMetrics history and classifies entries as **Active**, **Orphaned**, **Protected** or **Indeterminate**.
- Uses a conservative cleanup-candidate policy: missing `sensor` and `binary_sensor` entities can be flagged as orphaned; missing entities from other domains remain protected.
- Displays the number of VictoriaMetrics series and metric names associated with each entity for inspection.
- Provides an **Analyze** action only. RC3 exposes no deletion endpoint and performs no automatic VictoriaMetrics cleanup.
- Keeps the authenticated same-session Ingress/Nabu Casa PDF download flow unchanged after successful real-device validation.
- Keeps notifications, PDF generation, Paperless export, long-running AI handling and report statistics unchanged.

## VictoriaMetrics maintenance safety model

The maintenance inventory is intentionally isolated from reporting data and catalogs. It compares:

1. entity identifiers found in VictoriaMetrics historical series; and
2. entities currently returned by Home Assistant Core.

The feature is diagnostic only. No VictoriaMetrics series is deleted, rewritten or compacted by RC3.

## Upgrade notes

The update is intended to be compatible with `0.2.0-rc.2` and earlier beta releases. Existing catalogs, reports, automations, documents, provider settings and exports remain compatible.

After upgrading on Home Assistant OS, validate at least:

- one daily EMHASS report;
- one large N/N-x monthly report;
- **Settings → Maintenance → VictoriaMetrics → Analyze**;
- one PDF download through Home Assistant/Nabu Casa.

See `VALIDATION-0.2.0-rc.3.md` for automated validation details and remaining real-device validation points.
