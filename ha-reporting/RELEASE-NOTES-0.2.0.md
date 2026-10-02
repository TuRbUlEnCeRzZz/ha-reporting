# HA Reporting 0.2.0

`0.2.0` is the first stable HA Reporting release. It is a direct promotion of `0.2.0-rc.8` with **no functional runtime changes**. The stable package keeps the RC8 reporting engine, UI behavior, AI fact-ledger contract, scheduler, PDF pipeline, VictoriaMetrics maintenance and export behavior unchanged.

## Stable baseline

The stable release includes the full feature set hardened across the release-candidate series:

- deterministic statistics and N/N-x comparisons backed by VictoriaMetrics;
- native HTML/PDF report generation and authenticated downloads through Home Assistant Ingress / Nabu Casa;
- local document storage and Paperless-ngx export;
- internal scheduled automations with retries, execution history and Home Assistant notifications;
- French and English UI/report support;
- read-only VictoriaMetrics maintenance independent from reporting catalogues;
- collapsible, sortable Automations and Documents views;
- configurable AI context levels: **Optimized, Extended, Complete and Automatic**;
- deterministic AI fact ledger with ID-only selection and HA Reporting-owned numeric prose.

## AI safety and context behavior

`0.2.0` keeps **`ha-reporting-ai-context-v14`** with the **`id_only_v5_recommendation_guard`** protocol.

HA Reporting remains responsible for calculations, units, comparison eligibility, forecast/measured relationships and final quantitative sentences. The language model selects validated evidence IDs and recommendation actions only.

Automatic context selection remains deliberately conservative: substantial monthly and annual ledgers prefer **Optimized**, while users with a more capable model or faster hardware can explicitly select Extended or Complete.

The reconstructed-counter recommendation guard remains active: `verify_reconstructed_counter` is accepted only when the selected evidence itself proves reconstructed/reset handling.

## Final RC8 field validation

The final monthly N/N-1 RC8 run used the **Automatic** context mode and resolved to **Optimized**. It completed with:

- 78/78 sources available;
- 0 sources without data;
- 0 invalid/error sources;
- 34 selected facts out of 268;
- 23.9 k characters sent to the AI Task out of the 220 k application guard;
- correct forecast-versus-actual energy and mean-power relationships;
- reconstructed-counter recommendations attached only to reconstructed evidence;
- near-zero-reference ventilation guidance rendered without a false reconstructed-counter recommendation.

This final field run supports promotion of RC8 to stable without changing runtime logic.

## Compatibility

HA Reporting remains targeted at **Home Assistant OS**, primarily the project's Raspberry Pi 4 `aarch64` reference installation, while also declaring `amd64` support. The reference Home Assistant Core installation is kept current as new Core releases become available.

## Upgrade notes

No migration is required from `0.2.0-rc.8` to `0.2.0`. Existing catalogues, reports, documents, automations, settings and AI-context preferences are preserved.

As with previous releases, back up configuration and verify at least one end-to-end report after updating. AI commentary should be treated as commentary; deterministic report data remains authoritative.

## Validation

The stable build passes the same Python and JavaScript regression suites as RC8, together with syntax, metadata and archive-integrity checks. Version-consistency assertions were updated for `0.2.0`.

See `VALIDATION-0.2.0.md` for the detailed stable validation record.
