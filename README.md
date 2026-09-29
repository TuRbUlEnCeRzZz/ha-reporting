# HA Reporting

![HA Reporting](ha-reporting/logo.png)

**Current development version: 0.1.0-beta.25**

HA Reporting is a reporting engine for **Home Assistant OS**. It turns Home Assistant sensor history stored in VictoriaMetrics into structured reports, period comparisons, optional AI commentary and locally generated PDF documents.

Reports can be created manually or executed on an internal schedule, stored locally, exported to Paperless-ngx, and followed by Home Assistant notifications or TTS.

> **Personal and experimental project**
>
> HA Reporting was originally created for a personal Home Assistant installation. A substantial part of its design, implementation, debugging and documentation has been developed with ChatGPT assistance. It is shared in the hope that it may be useful to others. Maintenance may be irregular or stop entirely. There is no guarantee of support, timely fixes, data accuracy or continued compatibility with future Home Assistant releases. Back up your configuration and verify report results before relying on them.

## Environment and requirements

- **Home Assistant OS**, primarily developed and used on a **Raspberry Pi 4** running the 64-bit OS (`aarch64`). The add-on also declares `amd64` support.
- The reference installation keeps **Home Assistant Core updated as new releases become available**. This is the compatibility target, not a guarantee that every new Core release has already been tested with HA Reporting.
- **VictoriaMetrics** containing the Home Assistant sensor history you want to analyze and reachable from the add-on.
- Optional: a configured Home Assistant **AI Task** entity for AI commentary.
- Optional: **Paperless-ngx** for automatic PDF delivery.
- Optional: Home Assistant `notify.*`, `tts.*` and `media_player.*` entities for automation notifications.

Installing HA Reporting does **not** populate VictoriaMetrics and does not import Home Assistant Recorder history. No additional database is required by HA Reporting itself.

## Main features

### Data catalogues

The **Data** page organizes the devices, sensors and metrics that HA Reporting can analyze. Catalogues are reusable groups of devices and their associated sources, so the same data definition can be used by several reports.

The current engine supports the metric families used by the project, including energy, power, runtime, cycles and temperature. User-owned names and Home Assistant entity IDs are preserved as-is.

### Reports and comparisons

A report definition selects one or more catalogues, a period and optional comparison periods. Reports can be duplicated and adapted without rebuilding the data catalogue.

The reporting engine provides:

- detailed and long-period statistics;
- N/N-x comparisons;
- quality and missing-data diagnostics;
- optimized provider-side rollups for long periods;
- targeted raw-series verification or fallback when required;
- time-aware power statistics and raw-sample peak detection where available;
- a configurable start-of-day time, useful for periods such as **05:30 → 05:30**.

### Optional AI analysis

Reports can request commentary through Home Assistant **AI Tasks**. HA Reporting sends a compact, already calculated statistical context rather than raw VictoriaMetrics samples.

The deterministic statistics remain available independently of AI. An AI failure is recorded without automatically invalidating the statistical report.

The AI provider can be local or cloud-based depending on the Home Assistant AI Task configuration. Review the provider's privacy policy before enabling it.

### HTML and native PDF reports

HA Reporting renders structured reports containing summaries, detailed data, comparisons, quality information and optional AI commentary.

Native PDFs are generated locally by the add-on with WeasyPrint. Generated documents are stored under the add-on's persistent `/config/documents` directory and are available from the **Documents** page.

PDF filenames are configurable, duplicate handling is supported, and HTTP downloads are UTF-8-safe for filenames containing accented or other non-ASCII characters.

### Paperless-ngx export

Generated PDFs can be delivered to Paperless-ngx using either:

- a **consume folder** mounted below `/share` — recommended when available and requiring no Paperless API token; or
- the **Paperless REST API** with URL and token.

A failed export does not destroy the locally generated PDF. Export destinations are configured from **Settings → Export destinations**.

### Internal automations

HA Reporting includes its own scheduler, so normal scheduled reporting does not require a separate Home Assistant automation.

Supported schedules include hourly, daily, weekly, monthly and yearly execution. An automation can run the complete pipeline:

**data/statistics → optional AI → native PDF → local storage → export → notification**

Automations support controlled retries, active-job deduplication, interrupted-job recovery and persistent execution history.

Notification methods currently include:

- Home Assistant persistent notifications;
- `notify.*` entities, including compatible mobile notification services;
- TTS using a `tts.*` entity together with a `media_player.*` target.

### French and English

Beta.21 introduces the first HA Reporting internationalization layer.

- The Ingress interface supports **French (`fr`)** and **English (`en`)**.
- The initial interface language is detected from Home Assistant when possible and can be changed in **Settings → Languages**.
- The interface preference is stored locally in the browser.
- The **default report language** is configured separately from the interface language.
- Every report can override the default and generate renderer-owned content and AI instructions in French or English.
- User-owned names such as report names, catalogue names, device names and entity IDs are not translated.

From beta.21 onward, new and modified maintainer-facing repository content is written in **English**. See [CONTRIBUTING.md](CONTRIBUTING.md).

## What is new in beta.25

Beta.25 focuses on **deterministic cross-source AI analysis**. Beta.24 made every source self-describing; beta.25 goes one step further by calculating the important forecast-versus-measured relationships inside HA Reporting before the AI Task is called.

- introduces **`ha-reporting-ai-context-v5`** while preserving every current and comparison source, including partial data;
- adds a `relationships` section containing deterministic cross-source comparisons when source pairing is unambiguous inside one report device;
- for an integrated forecast power source and a measured period-energy counter, precomputes actual energy, forecast energy, absolute gap and relative gap;
- for one forecast power source and one measured power source, precomputes mean-power gap and carries P95/max values as secondary context;
- includes forecast and measured coverage in every relationship and marks whether a full-period comparison is supported;
- explicitly instructs the AI to prioritize period-energy forecast accuracy over isolated power peaks;
- requires the AI summary to include the integrated forecast energy and its deterministic gap when an `energy_forecast_vs_actual` relationship is available;
- keeps all arithmetic in HA Reporting so the language model does not need to infer source pairing or recalculate percentages;
- keeps beta.24 power integration, lossless source records and Home Assistant `state_class` handling unchanged;
- keeps beta.23 long-running AI timeout support unchanged.

These relationships are provider-agnostic. EMHASS is a useful real-world example, but the logic is not tied to EMHASS entity IDs: relationships are emitted only when HA Reporting can identify one forecast power source and one unambiguous measured counterpart within the same report device.

## Installation on Home Assistant OS

### From the Git repository

1. In Home Assistant, open **Settings → Apps** (called **Add-ons** in older interfaces).
2. Open the app store and its repositories menu.
3. Add:

   `https://github.com/TuRbUlEnCeRzZz/ha-reporting`

4. Refresh the store and verify that the offered version is **0.1.0-beta.25** before installing or updating.
5. Start HA Reporting and open its interface through Home Assistant Ingress.

### From the ZIP: local installation

1. Extract `ha-reporting-0.1.0-beta.25.zip` on your computer.
2. Inside the extracted repository, locate the **`ha-reporting/`** directory containing `config.yaml`, `Dockerfile`, `run.sh` and `app/`.
3. Copy that directory to **`/addons/ha-reporting`** on Home Assistant OS using your existing file-transfer method. Do not copy the whole repository into `/addons/ha-reporting`.
4. Refresh the app store and rebuild/reinstall the local add-on.
5. Start it and confirm **HA Reporting 0.1.0-beta.25** in the add-on log.

The first build can take some time on a Raspberry Pi 4 because dependencies are installed by Supervisor.

For upgrades, keep the same installation source and slug. Switching between a repository installation and a local installation can create a different Supervisor identity and therefore expose a different persistent data directory.

Paths beginning with `/config` in this project refer to **HA Reporting's own persistent add-on configuration mount**, not the Home Assistant Core `/config` directory.

## Creating a first report

1. Open **Settings → Data sources**, configure the VictoriaMetrics address and test the provider.
2. Open **Data**, create a catalogue, add devices and associate the relevant Home Assistant/VictoriaMetrics sources.
3. Open **Reports**, create a report, select one or more catalogues and choose its period and comparisons.
4. Select the report language and enable AI only if you want AI commentary.
5. Run the report and inspect quality or missing-data warnings.
6. Generate a native PDF and verify it under **Documents**.
7. Configure **Settings → Export destinations** if you want Paperless-ngx delivery.
8. Create an entry under **Automations** once manual execution works as expected.

## AI Tasks

Configure an AI Task provider in Home Assistant first. In the report settings, enable AI and select the desired entity, or use Home Assistant's preferred AI Task entity where supported.

The AI timeout is configured per report. Beta.25 keeps the beta.23 behavior: a 10-minute default, values from 60 seconds up to 2 hours, and presets up to 90 minutes and 2 hours for slow local inference. Model speed and memory use depend entirely on the selected provider and model.

HA Reporting communicates with Home Assistant for AI execution and keeps AI processing separate from the deterministic statistics. A slow or failed model should therefore not erase already calculated report data.

AI commentary can be wrong or over-interpret limited history. Treat it as commentary, not as a replacement for the measurements and statistics shown in the report.

### AI context normalization

Beta.25 uses **`ha-reporting-ai-context-v5`**. The context remains lossless with respect to the semantic report data sent to AI: no current-period or comparison source is removed, including partially covered sources. Raw time-series samples are still intentionally excluded.

The v4 self-describing source records remain intact: power values are labelled `max`, `p95` and `mean`; cumulative counters expose `period_delta` separately from `counter_end`; and an integrated power source exposes `integrated_energy_kwh`. Beta.25 adds deterministic `relationships` when forecast and measured sources can be paired unambiguously inside the same report device. HA Reporting calculates the corresponding energy and mean-power gaps before the AI call, so the model does not need to infer pairing or redo arithmetic.

The preferred operating size is 90,000 characters and the application-side safety guard is 220,000 characters. HA Reporting does **not** trim sources to meet either value. If the lossless context exceeds the application guard, the AI stage reports an explicit error. The AI provider/model still has its own token context limit, which remains authoritative and may be lower.

The completed AI result records the final context size, the earlier compact-context size, the normalization mode, relationship count and a `context_lossless` flag.

## Paperless-ngx

Open **Settings → Export destinations** and choose a delivery mode.

### Consume folder

Make the Paperless consume directory available below the add-on's `/share` mount, for example:

`/share/paperless_consume`

HA Reporting writes the file atomically so Paperless should only see the final PDF once copying is complete. No Paperless API token is required for this mode.

### REST API

Configure the Paperless URL and API token, then test the destination from HA Reporting.

A successful consume-folder copy confirms that the file was deposited, not that Paperless has finished indexing it. Likewise, API submission is followed by Paperless's own processing. Check the destination before manually retrying a failed or interrupted run to avoid duplicate ingestion.

## Internal automations and notifications

In **Automations**, select a report, schedule, AI behavior, PDF theme, export destinations, notification methods and retry policy. The same pipeline can also be started manually.

Schedules use the Home Assistant timezone. Beta.21 resolves that timezone through Supervisor when possible and caches it to avoid repeated API traffic. Invalid calendar dates are skipped.

Retries apply to global job failures. A completed run with warnings, such as a failed export after successful PDF creation, is not automatically treated as if the whole report had failed.

Automation definitions and execution history are stored in `/config/automations.json`. Up to 50 execution records are retained per automation. This history limit is **not** a PDF retention policy, so monitor the storage used by `/config/documents`.

The optional companion integration remains available under `custom_components/ha_reporting/` for advanced Home Assistant-side workflows using HA Reporting services. Internal scheduling does not require it.

## Security and privacy

- Use the Home Assistant **Ingress** entry point. HA Reporting is not designed to expose its internal HTTP server directly to the public internet.
- The add-on uses Supervisor-provided credentials to access Home Assistant APIs. Never publish those credentials, Paperless tokens or private endpoint addresses in logs or bug reports.
- Reports, filenames, diagnostics and AI prompts can reveal household activity. Include only the sensors you actually need.
- AI sends a compact report context to the configured AI Task provider. Whether that leaves your local network depends on the provider you configured in Home Assistant.
- Paperless export transfers the generated PDF to the configured destination only when requested.
- Configuration and backups may contain connection information or secrets. Protect them accordingly.
- Local PDFs and automation history remain on the Home Assistant host until you export or delete them.

## Limitations and validation

HA Reporting is experimental. Report accuracy depends on the quality and retention of the underlying Home Assistant/VictoriaMetrics history, sensor semantics, resets, missing samples and provider behavior.

Large reports and local AI inference can be slow on a Raspberry Pi 4. Supervisor builds also depend on upstream packages and system libraries.

Beta.24 has automated Python and JavaScript regression coverage, but automated desktop tests do not prove that every Home Assistant OS, ARM build, AI provider, VictoriaMetrics dataset or Paperless installation behaves identically. After upgrading, run at least one end-to-end report on the actual Home Assistant OS host before relying on scheduled delivery.

See [VALIDATION-beta24.md](VALIDATION-beta24.md) for the release validation notes and [ha-reporting/DOCS.md](ha-reporting/DOCS.md) for technical details.

## Repository layout

```text
ha-reporting/
├── ha-reporting/                  # Home Assistant OS add-on
│   ├── app/                       # Backend, UI, reporting and providers
│   ├── branding/                  # Branding sources
│   ├── config.yaml                # Supervisor add-on metadata
│   ├── Dockerfile
│   ├── DOCS.md                    # Technical documentation
│   └── CHANGELOG.md
├── custom_components/
│   └── ha_reporting/              # Optional Home Assistant companion integration
├── tests/                         # Regression tests
├── CONTRIBUTING.md                # Development and language policy
└── repository.yaml                # Home Assistant add-on repository metadata
```

## Development

Maintainer-facing development uses English from beta.21 onward. User-facing strings that are intended to be translated must go through the i18n layer and provide both French and English values.

Before preparing a release, run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui.cjs
python3 -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the repository language policy and [ha-reporting/CHANGELOG.md](ha-reporting/CHANGELOG.md) for release history.

## Roadmap

Possible future directions include:

- continuing the migration from the beta.20 compatibility translation layer to explicit message IDs throughout the UI;
- additional languages beyond French and English;
- additional export and notification destinations;
- continued PDF/layout improvements and reporting diagnostics;
- further validation with larger installations and longer histories;
- optional presets for common reporting use cases. EMHASS data can already be reported through normal sensors, but there is no dedicated EMHASS integration in beta.25; the new power-integration option is provider-agnostic.

These are possible directions, not delivery or maintenance commitments.

## Documentation

- [Technical documentation](ha-reporting/DOCS.md)
- [Changelog](ha-reporting/CHANGELOG.md)
- [beta.25 validation](VALIDATION-beta25.md)
- [beta.25 GitHub release notes](RELEASE-NOTES-beta25.md)
- [Contributing](CONTRIBUTING.md)
