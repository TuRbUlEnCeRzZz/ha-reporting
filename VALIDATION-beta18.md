# Validation — HA Reporting 0.1.0-beta.18

Date: 2026-09-27

## Baseline

Built from the supplied local `ha-reporting-0.1.0-beta.17.zip`, not from the alpha.22 workspace.
Baseline SHA-256: `431629b4b08da766ff1327c29ad2c67da026c4814691df2e952ab11c1ece3263`.

The baseline passed 118 Python tests and 42 JavaScript checks in this desktop environment before release validation. No production Home Assistant configuration was modified.

## Completed checks

- **126 Python tests passed**: the 118 existing cases plus 8 product-polish cases.
- **58 JavaScript checks passed**: 42 existing checks plus 16 beta.18 checks.
- Python compilation for app and optional Companion; JavaScript syntax; shell syntax: passed.
- YAML and JSON parse checks, version consistency and required PNG sizes: passed.
- Native PDF generation is exercised by the existing test suite using WeasyPrint.
- PNG handler responses were tested for a nested Ingress-style path and PNG content type.
- Desktop browser inspection with synthetic data: logo loads under a nested path, manual launch shows the toast, the launch button is disabled while active, and polling reaches the terminal display without manual refresh.
- A 390-pixel viewport check identified overflowing action buttons; wrapping was corrected and the repeated check showed no horizontal overflow (document width 375 px within a 390 px viewport).
- ZIP integrity and exact extracted-file hashes are checked when packaging; caches and temporary files are excluded.

### New behavioral coverage

Actual success/skipped/warning/failure stage outcomes; PDF failure leaves later stages unexecuted; AI/export warnings do not trigger a whole-pipeline retry; terminal progress survives losing the in-memory job cache; live snapshots do not leak mutable state; interrupted jobs do not show stale successful progress; the standalone AI preview still calculates missing statistics; no technical alert on manual launch; duplicate click guard; active/idle polling; hidden-page pause; transient fetch failure recovery; concurrent refresh coalescing; successful launch followed by failed refresh; ambiguous launch timeout does not automatically resubmit.

## Scope and compatibility

Collection and statistics are shown together because the existing engine performs both per device. This is stage tracking, not an estimated percentage. Legacy job status names are unchanged. Terminal progress is added to the existing version-2 automation storage and history. Existing definitions require no manual migration.

Byte comparisons against the baseline confirm that statistical analysis, period/comparison engines, AI transport, PDF rendering, Paperless provider and Dockerfile are unchanged. The optional Companion files are retained. Changed baseline files are listed in `validation/changed-files.txt` in the repository root.

No EMHASS-specific development is included. Home Assistant installation progress remains under Supervisor control.

## Test environment and limits

Local Linux desktop; Python 3.14, PyYAML, websocket-client 1.9.2, WeasyPrint 70.0; Node from the bundled desktop runtime. External services are mocked in automated pipeline tests. The visual preview uses synthetic data and is not a live HA run.

**Not performed:** Supervisor/ARM container build, installation on Raspberry Pi 4, live VictoriaMetrics / Home Assistant AI Tasks / Paperless delivery, or long-term scheduler observation. No Docker executable was available. This release is locally tested, not certified on-device.

## On-device acceptance after upgrading

1. Back up and update the same beta.17 installation source. Verify version beta.18 and retained catalogues, reports, automations and history.
2. Run one automation manually. Observe toast, collection/statistics, AI, PDF, delivery and notification as configured. Check the local PDF and Paperless result.
3. Repeat with AI/export/notification disabled; those steps should show disabled.
4. Check a scheduled run in the Home Assistant timezone, including its history entry.
5. Temporarily close/reopen the interface during a run; it should reconnect to the current state. Check persistence after an app restart.
6. Continue longer-term observation on HA OS / Raspberry Pi 4 with current Core releases. Review compatibility again after future Core updates.

## Reproduce locally

```sh
python -m unittest discover -s tests
node tests/test_ui.cjs
node tests/test_product_ui.cjs
python -m compileall -q ha-reporting/app custom_components
node --check ha-reporting/app/app.js
bash -n ha-reporting/run.sh
```

The Python environment needs PyYAML, websocket-client, WeasyPrint and its system libraries. Use an isolated environment and temporary test storage.
