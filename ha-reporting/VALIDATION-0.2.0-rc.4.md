# HA Reporting 0.2.0-rc.4 — Validation

This release candidate focuses on the selection-only fact-ledger AI boundary introduced after RC3 real-report testing with small local models and Qwen3:8B.

## Automated validation

- **160 Python regression tests passed**.
- **95 JavaScript UI checks passed**.
- All Python files under `ha-reporting/app`, `custom_components` and `tests` compile successfully.
- `ha-reporting/run.sh` passes `bash -n` syntax validation.
- `app.js` and `i18n.js` pass `node --check` syntax validation.
- Full and GitHub-update ZIP archives pass integrity checks; the GitHub update contains **17 files**, below the web uploader 100-file limit.

## RC4-specific regression coverage

The automated suite now verifies that:

1. the AI context uses `ha-reporting-ai-context-v10`;
2. the AI prompt requests JSON ID selection only and forbids free-form report prose;
3. selected comparison facts remain bound to one exact source/device/statistic tuple during deterministic rendering;
4. ordinary power `max` facts cannot be selected as normal summary facts;
5. cumulative `counter_end` facts cannot be selected as period-consumption summary facts;
6. invalid/free-form model output triggers deterministic fallback rendering instead of publishing the model's invented quantitative prose;
7. partial/limited/reconstructed comparison quality remains attached to the deterministically rendered statement;
8. forecast-versus-measured relationships keep their existing full-period coverage gating;
9. the RC3 VictoriaMetrics maintenance analyzer remains read-only and does not access HA Reporting catalogs;
10. no VictoriaMetrics deletion endpoint is exposed.

## Behaviour carried forward

RC4 intentionally keeps the following RC3 behaviour unchanged:

- VictoriaMetrics maintenance inventory under **Settings → Maintenance → VictoriaMetrics**;
- Active / Orphaned / Protected / Indeterminate classification;
- no automatic or manual deletion endpoint;
- authenticated same-session Home Assistant Ingress/Nabu Casa PDF downloads;
- long-running AI WebSocket heartbeat and configurable timeout handling;
- native PDF generation and Paperless export;
- Home Assistant notifications and TTS workflows;
- lossless semantic AI context with no current/comparison source omission.

## Real Home Assistant OS validation still required

Automated tests do not reproduce the user's Home Assistant OS host, local AI model, VictoriaMetrics history, Nabu Casa session or Paperless instance. Before promoting RC4 to `0.2.0`, validate on the real Raspberry Pi 4 installation:

- one daily EMHASS report;
- one large monthly N/N-1 report;
- preferably both the smaller local model and Qwen3:8B for comparison;
- one PDF download through Home Assistant/Nabu Casa;
- VictoriaMetrics maintenance **Analyze**;
- one scheduled automation including AI, PDF, Paperless and notification delivery.

The main acceptance criterion is that every quantitative sentence in the AI block matches one deterministic HA Reporting ledger item or relationship, with no source-name, unit, statistic, coverage, sign or percentage mixing.
