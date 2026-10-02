# HA Reporting 0.2.0-rc.8

`0.2.0-rc.8` is the final UX and AI-selection hardening release candidate planned before `0.2.0` stable. It keeps the deterministic fact-ledger architecture and configurable AI context levels from RC7, while making large Automation and Document lists easier to use and tightening recommendation/evidence consistency.

## Automation UX

Automation cards can now be **collapsed and expanded**. The expansion state is stored locally in the browser, so the list keeps the user's preferred density across page changes and reloads.

A currently running automation is always kept expanded so live pipeline progress, warnings and diagnostics remain visible.

The Automations page now supports persisted sorting by:

- creation date;
- name;
- next run;
- last start;
- last finish;
- duration;
- status.

Ascending/descending order is available, together with **Collapse all** and **Expand all** actions. Running automations remain pinned above inactive cards.

New automation definitions now persist a `created_at` timestamp. Existing definitions created before RC8 keep working unchanged; when possible, HA Reporting derives an approximate creation time from the oldest retained execution history instead of inventing a migration timestamp.

## Document UX

The Documents page now uses the same compact list behavior as Automations:

- collapsible/expandable document cards;
- persisted per-document expansion state;
- Collapse all / Expand all;
- ascending/descending sorting;
- persisted sort preference.

Documents can be sorted by generation date, name, period start, period end, report type or file size. The default remains newest generated document first.

## Conservative Automatic AI context

The six-report Optimized/Extended A/B test showed that Extended context can surface additional secondary observations, but on a local 8B CPU model it can substantially increase latency and introduce more low-priority noise.

RC8 therefore makes **Automatic** context selection deliberately conservative:

- small ledgers may use **Complete**;
- medium ledgers may use **Extended**;
- substantial monthly/annual ledgers prefer **Optimized** unless a larger mode is explicitly selected.

This does not remove Extended or Complete. Users with a more capable model or faster hardware can still select either mode manually.

## AI recommendation evidence guard

RC8 introduces **`ha-reporting-ai-context-v14`** and **`id_only_v5_recommendation_guard`**.

The ID-only model contract remains unchanged in principle: the model selects validated evidence IDs and recommendation actions, while HA Reporting owns calculations, units, comparison eligibility and final quantitative prose.

A new semantic guard now rejects `verify_reconstructed_counter` unless the selected evidence itself proves reconstructed/reset handling (`st=reconstructed`, `br=true` or `rr=true`). Reset information from another metric belonging to the same device can no longer be borrowed to justify a reconstructed-counter recommendation.

The guard is applied both when validating the model response and when rendering/merging recommendations, providing defense in depth.

## Compatibility and unchanged behavior

RC8 keeps the following behavior unchanged:

- authenticated PDF downloads through Home Assistant Ingress / Nabu Casa;
- deterministic statistics and N/N-x comparison rules;
- native PDF generation and local storage;
- Paperless-ngx export;
- Home Assistant persistent, notify and TTS notifications;
- read-only VictoriaMetrics maintenance independent from report catalogues;
- AI context levels Optimized, Extended, Complete and Automatic;
- deterministic fact-ledger calculations and numeric rendering.

## Validation

RC8 validation includes Python regression tests, JavaScript UI checks, Python compilation, JavaScript syntax checks, shell syntax validation, YAML/JSON metadata parsing, release-version consistency checks and archive-integrity verification.

See `VALIDATION-0.2.0-rc.8.md` for the detailed validation record.
