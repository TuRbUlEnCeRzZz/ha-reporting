# HA Reporting 0.2.0-rc.7

`0.2.0-rc.7` is the final AI-context control and presentation release candidate planned before 0.2.0 stable. It keeps the deterministic fact-ledger architecture introduced in RC4-RC6 and makes the amount of validated evidence exposed to the LLM configurable without relaxing any numeric safeguards.

## AI context levels

A new **Settings → Artificial intelligence → AI context level** setting provides four global modes:

- **Optimized** — keeps the compact RC6-style shortlist and remains the default for small local models and CPU inference.
- **Extended** — exposes a substantially larger deterministic shortlist to more capable or accelerated models.
- **Complete** — sends the complete deterministic fact ledger when it fits within the application-side safety limit.
- **Automatic** — selects Complete, Extended or Optimized from report complexity.

The selected mode changes only how much validated evidence the model can inspect. Calculations, units, comparison eligibility, explicit cross-source relationships, selected-ID validation and final numeric prose remain controlled by HA Reporting in every mode.

If Complete or Extended would exceed the application safety limit, HA Reporting deterministically falls back to a smaller effective mode. Both the requested and effective levels are recorded in the AI metadata and shown in HTML/PDF context information.

## AI contract v13

RC7 introduces **`ha-reporting-ai-context-v13`** and **`id_only_v4_context_levels`**.

The model still returns IDs only. It never receives authority to calculate a new gap, reinterpret a counter, change a unit or create an unsupported cross-source comparison.

Additional RC7 hardening:

- validated forecast-versus-actual relationships suppress redundant standalone component facts in the final summary;
- forecast/measured display values keep coherent precision when the authoritative deterministic gap contains decimals;
- when an annual N/N-x reference has no representative comparison, current **total electrical energy** is prioritized before individual appliance facts;
- report-wide quality signals and relationship priority from RC5/RC6 remain unchanged.

## Compatibility and unchanged behavior

RC7 keeps the following behavior unchanged:

- authenticated same-session PDF downloads through Home Assistant Ingress / Nabu Casa;
- native PDF generation and local document storage;
- Paperless-ngx exports;
- scheduled automations, notifications and TTS;
- read-only VictoriaMetrics maintenance inventory independent from report catalogs;
- deterministic report statistics and N/N-x comparison quality rules.

The default context level is **Optimized**, so existing installations keep RC6-like AI latency unless the user explicitly chooses another mode.

## Validation

RC7 validation includes Python regression tests, JavaScript UI checks, Python compilation, JavaScript syntax checks, shell syntax validation, YAML/JSON metadata parsing and archive-integrity verification.

See `VALIDATION-0.2.0-rc.7.md` for the detailed validation record.
