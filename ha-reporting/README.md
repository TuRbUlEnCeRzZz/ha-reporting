# HA Reporting

Home Assistant OS add-on — version **0.1.0-beta.21**.

## What is new in beta.21

Beta.21 establishes the localization architecture before further feature work is added:

- French and English are supported in the Ingress interface;
- the interface language is detected from Home Assistant on first launch and can be changed in **Settings**;
- the selected interface language is stored locally in the browser;
- every report can select its own language independently of the UI language;
- English reports translate renderer-owned labels and request the AI Task response in English;
- existing report definitions remain compatible and default to French when no language is stored;
- the download endpoint now handles Unicode filenames without triggering a proxy `502 Bad Gateway`;
- timezone discovery prefers Supervisor host information, caches successful resolution for one hour and falls back to Home Assistant Core `/api/config` when necessary;
- repository-facing additions and modifications are documented in English from this release onward.

## Language policy

The codebase and maintainer-facing material use English for new work: source comments, docstrings, changelog entries, validation notes, technical documentation and newly introduced internal messages. User-facing text is localized through `app/i18n.js`.

The beta.21 i18n layer deliberately keeps compatibility with the beta.20 UI while the source is migrated: legacy French strings are translated at runtime, while new UI code should use `hrT(messageId)` instead of adding hard-coded labels.

Two separate settings are available:

- **Interface language** controls the HA Reporting Ingress UI;
- **Default report language** is proposed for new reports, and each report can override it with its own **Report language** field.

Supported language codes are currently `fr` and `en`.

## Unicode PDF downloads

Native PDFs remain stored locally before any export. The HTTP download response now sends both an ASCII-compatible `filename=` fallback and an RFC 5987 `filename*=UTF-8''...` parameter. This prevents Python's HTTP header encoder from failing on characters such as an em dash or accented letters while preserving the intended filename in modern browsers.

## Timezone discovery

The add-on now declares Supervisor API access with the default role and reads the Home Assistant OS host timezone from `http://supervisor/supervisor/info`. The resolved timezone is validated with `zoneinfo`; successful resolution is cached for one hour. If Supervisor information is temporarily unavailable, HA Reporting falls back to Home Assistant Core `/api/config`, then to `TZ`/UTC as a last resort. A last-resort fallback is cached for five minutes so HA Reporting can recover without recreating a 15-second warning loop.

## Installation from this development archive

1. Extract the repository archive.
2. Copy the `ha-reporting` subdirectory (the directory containing `config.yaml` and `Dockerfile`) to `/addons/ha-reporting` on Home Assistant OS, or update the same Git-based add-on repository you already use.
3. Refresh the add-on store and rebuild/reinstall the local add-on.
4. Confirm `HA Reporting 0.1.0-beta.21` in the add-on log.
5. Open the Ingress UI and verify **Settings → Languages**.

Do not copy the repository root in place of the add-on directory. The archive contains Supervisor-buildable sources, not a prebuilt OCI image.

## Main components

- `app/main.py`: HTTP API, Home Assistant/Supervisor integration, scheduler and orchestration.
- `app/app.js`: Ingress UI behavior.
- `app/i18n.js`: localized UI messages and beta.20 compatibility translation layer.
- `app/rendering/html_report.py`: HTML/native-PDF report rendering.
- `app/analysis/ai_report.py`: compact AI context and localized AI instructions.
- `custom_components/ha_reporting`: companion Home Assistant integration.

See `DOCS.md` for technical notes and `VALIDATION-beta21.md` for release validation.
