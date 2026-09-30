# HA Reporting 0.2.0-rc.2 — Validation

## Scope

RC2 is intentionally narrow. It validates AI interpretation hardening after RC1 real-world tests while leaving the statistical engine, notifications, PDF generation, Paperless export and authenticated document-download mechanism unchanged.

The release specifically targets three RC1 monthly-report failure modes:

- mixing information from two different N/N-x comparison records;
- using the wrong named statistic (for example interpreting max/min when describing a mean);
- inventing a percentage from an absolute gap when HA Reporting deliberately suppressed the relative percentage.

## Deterministic AI contract

`ha-reporting-ai-context-v8` keeps every semantic current-period and comparison source. Each N/N-x comparison record has a compact `id` and remains self-describing.

Prompt rules require that:

- one comparative sentence stays inside one comparison `id`;
- a comparison record always refers to one source versus that same source in the reference period;
- average/min/max/P95/delta wording must use the matching named field;
- a relative percentage is permitted only when the same statistic contains `gap_pct`;
- coverage cannot be borrowed from another comparison or relationship;
- cross-source current-period comparison remains allowed only through deterministic `relationships`.

## Automated regression coverage

The regression suite includes dedicated RC2 checks for:

- unique comparison IDs and source isolation;
- authoritative positive/negative trend direction on the exact named statistic;
- temperature mean direction remaining independent from temperature maximum direction;
- near-zero reference handling preserving the absolute gap while omitting `gap_pct`;
- prompt rules that explicitly forbid cross-record field mixing and inferred percentages.

The large lossless-context regression still keeps all 421 current sources and 420 comparison sources under the configured hard character limit with no source omission.

## RC1 real-device validation carried forward

The following were confirmed during RC1 testing on the real Home Assistant OS installation:

- two report PDFs were downloaded successfully through Home Assistant via Nabu Casa;
- the previous `401 Unauthorized` remote-download failure did not recur;
- smartphone notification delivery worked and is therefore intentionally unchanged in RC2;
- daily EMHASS forecast-versus-actual direction and energy comparison were interpreted correctly;
- a large monthly N/N-x report completed with local AI inference and generated a valid PDF.

These real-device observations validate unchanged RC1 paths; they do not replace RC2-specific end-to-end testing of the new AI wording constraints.

## Remaining validation before 0.2.0 stable

1. Generate a fresh daily EMHASS report on RC2.
2. Generate a fresh large monthly N/N-x report on RC2.
3. Verify that the AI does not combine two device/source comparisons in one claim unless a deterministic `relationship` explicitly pairs them.
4. Verify that a mean trend follows `values.mean`, not min/max/P95.
5. Verify that suppressed percentages remain absent from AI commentary.
6. Reconfirm normal PDF download, Paperless export and scheduled automation completion.

## Limitations

AI commentary remains probabilistic. RC2 makes the supplied contract substantially harder to misuse, but deterministic statistics and rendered comparison cards remain the source of truth. Provider-specific model behavior can still vary.

## Validation result for this build

- Python regression tests: **152 passed**.
- JavaScript UI checks: **95 passed**.
- Python bytecode compilation: **passed**.
- JavaScript syntax checks (`app.js`, `i18n.js`): **passed**.
- Shell syntax check (`run.sh`): **passed**.
- Runtime version declarations checked as `0.2.0-rc.2`: **passed**.
