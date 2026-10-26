# HA Reporting 0.2.1 — Supervisor packaging update

## What changed

- Removed the optional Home Assistant Core companion integration (`custom_components/ha_reporting/`) and its standalone installation guide. HA Reporting is now distributed exclusively as a Home Assistant OS app, not as a HACS/Marketplace integration.
- Migrated the Supervisor configuration mapping from the deprecated `addon_config` name to `app_config`, while keeping the container mount at `/config` read/write and the existing app slug `ha_reporting`.
- Updated the app version, runtime banner, User-Agent headers, project docs and regression assertions.

## Preserved behavior

The reporting engine, stored catalogues, internal schedules, AI Task integration, N/N-x comparisons, VictoriaMetrics processing, PDF generation, Paperless exports and notifications are unchanged. No reporting behavior was intentionally altered.

## Upgrade instructions

1. Back up HA Reporting settings and documents as part of a Home Assistant OS backup.
2. Publish this entire source tree to the same Supervisor app repository and refresh the app repository in Home Assistant OS. Install/update **HA Reporting 0.2.1** as an app, not through HACS.
3. Verify that catalogues, report definitions, automation schedules and PDFs under `/config` are intact, then run a real report.
4. If you previously installed the optional HA Reporting Core integration, uninstall it separately using Home Assistant's Devices & services and HACS/Marketplace (or remove `/config/custom_components/ha_reporting` if manually installed), then restart Home Assistant Core. Native `ha_reporting.run_report` service calls stop working; replace them with built-in schedules or a separately authenticated REST workflow.

**Important:** Simply copying this new archive into an existing repository does not remove files already tracked there. Delete the old repository paths `custom_components/ha_reporting/` and `COMPANION-INTEGRATION.md` explicitly. Keep the Supervisor app directory `ha-reporting/`.

## Validation status

Automated checks passed locally (187 Python tests, 118 current UI checks and 16 legacy automation UI checks); details are in `VALIDATION-0.2.1.md`. Real Home Assistant OS/aarch64 installation, Supervisor build and end-to-end PDF/AI/Paperless smoke tests must be performed on an actual Raspberry Pi 4. No production upgrade has been performed by this package.
