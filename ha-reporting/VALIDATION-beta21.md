# HA Reporting 0.1.0-beta.21 — Validation

## Scope

Beta.21 validates the French/English i18n foundation, per-report language persistence, English HTML/AI rendering, Unicode-safe PDF downloads and resilient Home Assistant timezone discovery. Liquid Glass/PDF background work is intentionally outside this release scope.

## Automated checks

Run from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui.cjs
python3 -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
```

Expected results for the beta.21 development archive:

- all Python regression tests pass;
- all JavaScript UI checks pass;
- Python sources compile successfully;
- `app.js` and `i18n.js` pass Node syntax validation.

## Release checks

- `config.yaml`, the runtime banner and the companion integration manifest report `0.1.0-beta.21`.
- `config.yaml` enables `homeassistant_api` and Supervisor API access with `hassio_role: default`.
- `i18n.js` is served by the add-on and loaded before `app.js`.
- the UI exposes **Interface language** and **Default report language** in Settings.
- a report exposes its own **Report language** selector and persists `fr` or `en`.
- report definitions without a language remain valid and resolve to French.
- an English report renders `<html lang="en">`, English report labels and English AI instructions.
- Unicode download filenames produce a Latin-1-safe HTTP header and retain a UTF-8 `filename*` value.
- timezone lookup prefers Supervisor information, caches the value and falls back to Core configuration if required.

## Home Assistant OS smoke test

After rebuilding the add-on on Home Assistant OS:

1. Confirm the startup log contains `HA Reporting 0.1.0-beta.21` and a resolved Home Assistant timezone.
2. Open the Ingress UI and switch **Settings → Interface language** between French and English.
3. Create or edit one report and select English as its report language.
4. Generate the report and verify that report-owned labels and AI sections are English while entity IDs/device names remain unchanged.
5. Download a PDF whose generated filename contains an em dash or accented character and confirm no `502 Bad Gateway` occurs.
6. Verify that repeated navigation between Automations and Settings does not create repeated timezone 502 warnings.
7. Reopen an existing beta.20 report and confirm it still uses French unless explicitly changed.

## Compatibility

No migration is required for beta.20 report YAML files. Missing `language` fields are treated as `fr`. Existing catalogs, documents, automations and export-provider settings are unchanged by the beta.21 language work.
