# Validation — HA Reporting 0.2.1

## Scope

This release removes the optional HACS/Home Assistant Core companion integration; updates the app's Supervisor mapping to `app_config`; and aligns package version, headers and documentation. The runtime report engine and web UI are deliberately unchanged.

## Completed local validation

- Check archive integrity and absence of the legacy `custom_components/ha_reporting/` files and `COMPANION-INTEGRATION.md`.
- Check `ha-reporting/config.yaml` has version `0.2.1`, slug `ha_reporting`, ingress enabled and writable `app_config` mounted at `/config`.
- Compile Python sources and verify JavaScript syntax.
- Run Python and JavaScript regression suites.

## On-device verification still needed

- Home Assistant OS on Raspberry Pi 4 (aarch64), current Core and Supervisor: app discovery, build/update, startup and Ingress.
- Verify existing `/config` datasets (catalogues, scheduled jobs, documents) remain available after update.
- Run one daily report and one historical comparison; test optional AI Task, PDF download, VictoriaMetrics reading and Paperless export.
- If the companion was installed, uninstall it separately in Home Assistant Core and check that only the expected native `ha_reporting.run_report` action is removed.

## Local test results

- Python: `python3 -m unittest discover -s tests -p 'test_*.py'` — **187 passed**. Two legacy beta.18 tests were updated to use the current notification helper API; simulated PDF errors and disconnected Supervisor warnings in the logs are intentional test fixtures.
- JavaScript: `node tests/test_ui.cjs` — **118 checks passed**.
- Legacy automation JavaScript checks: `node tests/test_product_ui.cjs` — **16 checks passed**. The isolated test no longer attempts to render a UI with missing DOM/state fixtures; rendering is validated separately.
- JS syntax and shell script syntax were checked with `node --check` and `bash -n`.
- The archive excludes Python bytecode caches (`__pycache__`, `*.pyc`) and the removed Core companion integration.

**Not tested locally:** Supervisor discovery/build or runtime migration on Raspberry Pi 4, real Nabu Casa Ingress access, AI Task responses, network calls to VictoriaMetrics and Paperless. These remain mandatory on-device acceptance tests.
