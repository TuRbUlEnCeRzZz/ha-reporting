# HA Reporting

![HA Reporting](logo.png)

**Version 0.1.0-beta.18 — product polish**

HA Reporting turns Home Assistant sensor history into reports, comparisons, optional AI commentary and PDF documents. Reports can run on an internal schedule and be delivered to Paperless-ngx.

> **Personal and experimental project**
>
> This application was originally created for a personal Home Assistant installation. A substantial part of its design, implementation, debugging and documentation was developed with ChatGPT assistance. It is shared in the hope that it may be useful to others. Maintenance may be irregular or stop entirely. There is no guarantee of support, timely fixes, data accuracy or continued compatibility with future Home Assistant releases. Back up your configuration and check report results before relying on them.

## Environment and requirements

- Home Assistant OS, primarily targeting a Raspberry Pi 4 running the 64-bit OS (`aarch64`). The package also declares `amd64` support.
- The intended reference installation keeps Home Assistant Core updated as releases become available. This is a compatibility target, not a claim that every new release has already been tested; see [validation](VALIDATION-beta18.md).
- VictoriaMetrics with the sensor history you want to analyze, reachable from the app. Installing HA Reporting does not populate VictoriaMetrics or import Recorder history.
- Optional: a configured Home Assistant AI Task entity for AI commentary, and a Paperless-ngx installation for document delivery.

No additional database or Companion integration is required for normal use. The interface is currently in French; this README is in English.

## Features

- Catalogues group devices and sensor sources into reusable report inputs.
- Period selection, comparisons, statistics and quality diagnostics; optimized retrieval for long periods and raw-series verification where required.
- Optional AI commentary using Home Assistant AI Tasks. Statistics remain available separately from the AI result.
- Native PDF generation, light/dark themes, local document storage, configurable filenames and duplicate handling.
- Paperless delivery through a shared consume folder or the REST API.
- Internal hourly, daily, weekly, monthly and yearly schedules using the Home Assistant timezone and 24-hour time input.
- Up to 50 persistent execution records per automation, controlled retries, active-job deduplication and interrupted-job recovery after restart.
- Optional persistent Home Assistant notifications with AI commentary when available.

### New in beta.18

Manual execution shows a small “Rapport lancé” message. Automation cards show actual stage outcomes for collection/statistics, AI, PDF, export and notification. The page refreshes every 3 seconds while work is active and every 15 seconds when idle, and pauses when hidden. A network interruption is reported and the page retries automatically. Enabled options, skipped steps, warnings and failures remain distinguishable.

Collection and statistics share one stage because the existing engine retrieves and analyzes each device together. No percentage or completion time is estimated. Installation/build progress belongs to Home Assistant Supervisor; this application only displays report execution progress after it has started.

The app store icon, logo, interface icon and favicon use the same visual identity. The Home Assistant sidebar continues to use the configured Material Design icon.

## Installation on Home Assistant OS

### From a repository

Once this release has been published in the project's Git repository:

1. Open **Settings → Apps** (called **Add-ons** in older interfaces), then the store and its repositories menu.
2. Add `https://github.com/TuRbUlEnCeRzZz/ha-reporting`.
3. Refresh the store and check that the offered version is **0.1.0-beta.18** before installing/updating.
4. Start HA Reporting and open its web interface through Home Assistant Ingress.

This source archive does not itself publish or update the Git repository.

### From the ZIP: local installation

1. Extract `ha-reporting-0.1.0-beta.18.zip` on your computer.
2. Inside the extracted files, locate **`ha-reporting/` containing `config.yaml`, `Dockerfile`, `run.sh` and `app/`**.
3. Copy that app directory into **`/addons/ha-reporting` on your Home Assistant OS installation**, using your existing file transfer method. Do not copy the entire repository there.
4. Refresh the app store. Install the local app, or rebuild your existing local installation, then start it.
5. Confirm beta.18 in the interface. The first build can take time on a Raspberry Pi 4 and needs network access for dependencies.

For an upgrade, back up first and retain the **same installation source and slug**. Switching between a repository installation and a local installation creates a different Supervisor identity and may expose a separate data directory. Do not uninstall the old app merely to update its code.

Beta.18 reads the beta.17 configuration and history without a manual migration. `/config` paths below refer to the app's own persistent configuration mount, not the Home Assistant Core configuration directory.

## First report

1. Open **Sources de données**, configure the VictoriaMetrics address and test it.
2. Create a **Catalogue**, add devices and associate the relevant sensor sources.
3. Open **Rapports**, select catalogues and a period, and configure comparisons if wanted.
4. Execute and inspect a report. Check missing-data and quality warnings before enabling AI.
5. Generate a PDF and find it under **Documents**.
6. Configure delivery and create an automation once manual execution works.

## AI Tasks

Configure an AI Task provider in Home Assistant first. In the report settings, enable AI and select the entity, or use Home Assistant's preferred AI Task entity. The default timeout is 600 seconds; the backend accepts 60–1800 seconds. Model speed and resource use depend on your provider.

The automation can inherit the report's AI setting or force AI on/off. A failed AI analysis is recorded as a warning and does not necessarily prevent PDF generation. AI commentary can be incorrect; it does not replace the deterministic statistics or your own review.

The request is sent through Home Assistant's internal WebSocket API. An AI provider may run locally or send report context to a cloud service. Review that provider's privacy policy and configuration. Model reasoning options are configured on the AI Task integration; HA Reporting does not promise to override them per request.

## Paperless-ngx

Open **Documents → Destinations d’export** and choose a delivery mode:

- **Consume folder:** make Paperless's consume directory available under the app's `/share` mount, for example `/share/paperless_consume`. On HA OS, configure the network storage for Share use, ensure permissions allow writing, and test the folder. HA Reporting writes a temporary file and renames it after copying. No Paperless API token is needed.
- **API:** configure the Paperless URL and token, then test the connection. Use a trusted endpoint and appropriate credentials.

An export requires PDF generation. A successful consume-folder delivery means the file was deposited; it does **not** confirm Paperless indexing. API submission likewise depends on Paperless processing. The local PDF remains available if delivery fails. Check the document's export result before retrying to avoid duplicate ingestion.

## Internal automations

In **Automatisations**, select a report, schedule, AI setting, PDF theme, destinations, notification and retry policy. You can run the same pipeline manually with **Exécuter maintenant**.

Schedules use Home Assistant's timezone. Invalid calendar dates, such as February 31, are skipped. The scheduler reserves a time slot before launching it and checks periodically. This is not a real-time scheduling service and does not guarantee catch-up for every schedule missed while stopped.

Retries apply to global failures. A completed run with warnings, such as a delivery failure after PDF creation, is not automatically repeated. Jobs interrupted by an app restart are recorded as interrupted and can be retried according to the configured policy. An external side effect may already have happened before an interruption; check destinations before manually rerunning.

Definitions and history are stored in `/config/automations.json`; PDFs in `/config/documents`. Monitor disk space: the 50-entry history limit is not a PDF retention policy.

The optional Companion is retained in `custom_components/ha_reporting/` for advanced Home Assistant automations using `ha_reporting.run_report`. It is not needed for internal scheduling. See [Companion documentation](../COMPANION-INTEGRATION.md) and [technical documentation](DOCS.md) for existing APIs and events.

## Security and privacy

- Use the Home Assistant Ingress entry point. This package does not publish a host port. The app is not designed as an independently authenticated public web service; do not expose its internal HTTP port to the internet.
- The app uses the Supervisor-provided credential to access Home Assistant APIs. Never share that credential, Paperless tokens or private endpoint addresses in bug reports.
- Reports, filenames, diagnostics and AI prompts can reveal household activity. Limit included sensors to the data you need.
- AI sends a compact report context to the configured AI Task provider. Paperless export sends the generated PDF to the configured destination. Those transfers are optional and depend on your configuration.
- Local configuration includes connection settings and may include secrets. App storage and backups are not a dedicated encrypted secret vault. Protect backups and shared folders accordingly.
- PDF files and automation history remain local until an export is requested. Remove unneeded documents yourself and check available storage.

## Limitations and validation

The app is experimental. Sensor naming, availability, history retention, counter resets and provider behavior affect results. Large reports and local AI can be slow on a Raspberry Pi. Dependencies are installed during the Supervisor build; upstream changes can affect future builds.

Beta.18 keeps the beta.17 calculation engine, PDF templates, scheduler/retry policy and Companion contract. Its new progress fields are additive. Runtime jobs are held in memory; terminal progress is persisted with automation history. There is no cancel button in this release.

Automated tests and their limits are documented in [VALIDATION-beta18.md](VALIDATION-beta18.md). Desktop checks do not establish that an ARM Supervisor build or your live HA/AI/Paperless installation has passed. Run an end-to-end scheduled report on your Raspberry Pi after upgrading.

## Roadmap

- Long-term observation of schedules, retries, resource usage and document delivery.
- PDF visual improvements: typography, spacing, charts and pagination.
- Possible EMHASS catalogue/report presets after standard sensor reporting has been evaluated. **No EMHASS-specific integration or development is included in beta.18.**
- Further UI improvements based on actual use.

These are possible directions, not delivery or maintenance commitments.

## Development

Run `python -m unittest discover -s tests` and `node tests/test_ui.cjs`, plus the beta.18 checks in `tests/test_product_ui.cjs`. Python needs PyYAML, websocket-client and WeasyPrint (including its system libraries). See the validation document for the environment used for this release.

Branding sources are in `ha-reporting/branding/`. The PNG files follow the [Home Assistant presentation guidance](https://developers.home-assistant.io/docs/apps/presentation/). Installation guidance: [local apps](https://developers.home-assistant.io/docs/apps/tutorial/) and [repositories](https://www.home-assistant.io/common-tasks/os/#installing-a-third-party-app-repository).
