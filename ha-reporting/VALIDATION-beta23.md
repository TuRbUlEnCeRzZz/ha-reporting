# HA Reporting 0.1.0-beta.23 — Validation

## Scope

Beta.23 validates long-running local AI analysis. It keeps the beta.22 lossless `ha-reporting-ai-context-v3` serialization, deterministic statistics, FR/EN behavior, PDF generation, exports and automation pipeline unchanged while extending AI Task timeout handling to two hours.

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

Expected results for the final beta.23 archive:

- **126 Python regression tests pass**;
- **81 JavaScript UI checks pass**;
- Python sources compile successfully;
- `app.js` and `i18n.js` pass Node syntax validation;
- `run.sh` passes shell syntax validation.

## AI timeout checks

- backend validation accepts `ai_analysis.timeout_seconds` from 60 through 7,200 seconds;
- 7,201 seconds is rejected;
- the default remains 600 seconds;
- a configured 5,400-second timeout is passed through to the AI Task worker;
- the editor exposes practical timeout presets up to 7,200 seconds;
- 5,400 seconds is shown as `1 h 30 min` and 7,200 seconds as `2 h`;
- a persisted custom timeout inside the supported range is preserved when editing a report;
- browser-side monitoring keeps the configured timeout plus a 30-second margin;
- WebSocket heartbeat behavior remains active during long generations;
- timeout errors are formatted in the selected report language.

## Compatibility checks

- no migration is required for beta.22 report, catalogue, automation, export or language settings;
- existing report timeout values remain valid;
- beta.22 lossless AI context normalization is unchanged and still retains partial-coverage sources and comparisons;
- PDF generation and export continue even when an AI stage ends with a timeout warning;
- repository-facing beta.23 documentation and release notes are in English.

## Home Assistant OS smoke test

After rebuilding the add-on on the Raspberry Pi 4 Home Assistant OS host:

1. Confirm the startup log contains `HA Reporting 0.1.0-beta.23`.
2. Edit the large monthly home-automation report and set the AI timeout to **1 h 30 min (5,400 s)**.
3. Run the report with the same local AI Task entity that previously required about 50 minutes.
4. Confirm the AI stage remains `running` beyond the former 20-minute limit instead of returning a timeout warning.
5. Confirm the Ingress page can be left and reopened while the server-side AI job continues.
6. Confirm the completed AI result is added to the report, followed by PDF generation/export/notification as configured.
7. Confirm the beta.22 no-source-omitted AI-context diagnostic remains present.

## Provider cancellation note

When HA Reporting reaches its configured timeout it closes the WebSocket connection. Home Assistant or a downstream provider may still continue the already-started generation if cancellation does not propagate. Beta.23 therefore extends the timeout range but does not claim provider-side cancellation support.
