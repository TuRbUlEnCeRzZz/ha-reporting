# HA Reporting 0.1.0-beta.22 — Validation

## Scope

Beta.22 validates the lossless AI context normalization path for large reports. The deterministic statistics engine, report definitions, FR/EN language behavior, PDF generation, exports and automation pipeline remain compatible with beta.21.

## Automated checks

Run from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui.cjs
python3 -m compileall -q ha-reporting/app custom_components/ha_reporting
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
bash -n ha-reporting/run.sh
```

Expected results for the final beta.22 development archive:

- 125 Python regression tests pass;
- 75 JavaScript UI checks pass;
- Python sources compile successfully;
- `app.js` and `i18n.js` pass Node syntax validation;
- `run.sh` passes shell syntax validation.

## AI context checks

- AI Task input uses the `ha-reporting-ai-context-v3` lossless normalized schema;
- raw previews and raw series remain absent from the model-facing context;
- every current-period source is retained, including partial-coverage sources;
- every comparison source is retained;
- the synthetic large-report regression keeps 421 current sources and 420 comparison sources with zero omissions;
- that synthetic context is reduced from roughly 493k characters in the beta.21 compact representation to roughly 48k characters in v3 while preserving all semantic source/comparison rows;
- comparison wording policy, coverage and reconstruction semantics remain represented;
- the preferred operating target remains 50,000 characters and the hard safety guard remains 60,000 characters;
- contexts are no longer source-trimmed to reach 50,000 characters;
- if a lossless v3 context exceeds 60,000 characters, the AI stage fails explicitly rather than silently dropping data;
- completed AI metadata records schema, final/original sizes, lossless mode and current/comparison source counts;
- the UI and generated HTML/PDF can display `AI context: current / limit` plus the no-source-omitted diagnostic.

## Release checks

- `config.yaml`, runtime banner, HTTP user agents, interface subtitle and companion integration manifest report `0.1.0-beta.22`;
- no migration is required for beta.21 report/catalog/automation/export configuration;
- the repository README and new beta.22 maintainer documentation remain in English;
- French and English report language behavior remains covered by the existing regression suite.

## Home Assistant OS smoke test

After rebuilding the add-on on the Raspberry Pi 4 Home Assistant OS host:

1. Confirm the startup log contains `HA Reporting 0.1.0-beta.22`.
2. Run the monthly home-automation report that previously produced an AI context of approximately 106,724 characters.
3. Confirm the AI stage no longer fails with `Contexte IA trop volumineux` when the lossless v3 context fits below 60,000 characters.
4. Confirm the completed AI card shows the final context size, `normalisé depuis` / `normalized from` when applicable, and `aucune source omise` / `no source omitted`.
5. Check that partial-coverage sources are still represented in the AI interpretation and that comparison cautions remain correct.
6. Generate the PDF/export and verify the rest of the automation pipeline still completes normally.

## Compatibility

Beta.22 changes only the AI-facing semantic serialization and diagnostics. Existing persisted configuration does not require a schema migration. The 60,000-character hard guard remains a final safety boundary; the 50,000-character value is a preferred target only and no longer causes source omission.
