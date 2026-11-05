# HA Reporting 0.2.5 — Audit and validation

## Scope and reference

Baseline: `256f055` on main, containing the merged 0.2.4 changes. The initial working checkout was clean. Before editing production behavior, **248 Python tests passed** and new failing AI/PDF/category regressions were established. Existing JavaScript baseline: 118 UI + 16 product + 6 category checks.

The requested weekly reference is 26 October–2 November 2026, Europe/Zurich, compared with 19–26 October. Reported aggregates are 16 devices, 78/78 sources, 58.80 kWh actual, 51.73 kWh forecast, +13.7% forecast gap, 59.7 kWh reference and -1.53% historical change; comparison counts 39/32/4/3. They remain validation data, never production constants. Existing rounded PDF-excerpt fixtures and synthetic surrounding records are used. The complete 23-page PDF was supplied after the initial implementation and inspected as documented below. The unrounded 78-source execution remains unavailable. The reported 6.22 s deterministic, 71.1 s AI and approximately 78,600-character context are observations, not a controlled benchmark reproduced here.

## Audit findings and risks

1. AI transport already enforces an ID-only selection protocol. It cannot safely accept unrestricted explanations without a larger response-contract change. Most legacy selections repeat facts, quality limitations and monitoring recommendations already available in the deterministic overview. The PDF's exact sentence deletion leaves generic fragments and a large analysis box.
2. `_render_ledger_id` intentionally attaches reliability prose to individual derived ratios. The PDF repeats identical refrigeration/performance caveats for several indicators of the same device/target, even though numbers and coverage are distinct and must remain attached to their indicators.
3. Historical category values are loaded and rendered as configured. The old first-option default (`refrigeration`) was already corrected for new devices in the previous release. No current classifier or category migration was found. Actual user catalogues are unavailable, so a particular ventilation category cannot be attributed conclusively to that historical default versus an explicit choice.
4. A separate reproducible category bug exists: editing a saved unknown category does not offer it in the dropdown; the browser chooses the first known category, and renaming alone can overwrite the saved value. A local selected option now preserves this value. There is no migration or name-based reclassification.

Principal risks addressed: losing legitimate structured legacy responses, crediting fallback as AI interpretation, accepting invented prose/numbers, linking different devices/periods, losing qualifications while deduplicating, changing unknown category values, and accidentally altering deterministic ranking or notifications.

## Implemented behavior

### Complementary AI

Existing `summary`, `attention`, `recommendations`, context modes, schema identifier, transport, timeouts, heartbeats and single `ai_task.generate_data` call remain supported. An **optional** `interpretations` list selects `I*` IDs from compact `interpretation_candidates` and `selection_policy.interpretations`. Old response shapes remain accepted. A valid empty list means no added value.

Candidates reference existing derived facts, rather than copying statistics or asking for new calculations. Only a selected energy/cycle increase paired with a relevant duration/cycle change on the same stable device and target/period is currently offered. Existing duration relevance checks are reused; no ranking rule or threshold is modified. Starts/refrigeration semantics, ambiguity, missing evidence and reconstructed contributors are respected. Evidence plus its source/comparison/contributor dependencies remains available in each context projection.

The current bounded vocabulary distinguishes energy/duration increases from opposing trends. HA Reporting writes the relation, qualified possible operating-condition/load hypotheses and checks. No model-provided number, unit, device name, fault diagnosis or free-form causal assertion enters the PDF. No second model, classifier or additional service call judges the first model.

New valid responses produce complementary `text` or empty `text`, with additive `interpretation_status` metadata (`useful`, `no_added_value`, `invalid_response`). Legacy ID-only responses retain legacy text behavior and deterministic fallback. The PDF revalidates candidate IDs against the current ledger and does not relabel fallback text as an AI contribution. Stored legacy text and technical error diagnostics are preserved, but the PDF shows only verified complementary interpretation or a concise trace. Pending/error/timeout cases retain the deterministic report and a neutral status without raw internal exceptions.

This is deliberately not unrestricted AI prose generation: novel explanations outside the supported relation vocabulary are not shown. That limitation is preferred over changing the safe factual contract or introducing a costly semantic judge. Common words with the overview do not cause rejection; valid evidence-based interpretation survives regardless of lexical overlap.

### PDF and categories

The deterministic overview, selected values and notification are unchanged. Known **exact repeated** refrigeration/performance clauses move into one scoped reliability note naming the affected indicators. Grouping requires the same stable device and comparison target/period. Numerical contributor coverage stays with each indicator; unknown, source-specific, single-use and distinct energy-per-operating-hour wording is preserved. No numerical formatting or conversion function is changed. Existing CSS, charts, source cards, comparison tables and theme palettes remain intact.

No useful AI selection produces only a compact source/duration/context trace, without an empty interpretation heading or generic commentary. Technical errors remain stored for diagnostics rather than printed in the PDF.

Existing configured categories remain visible and unchanged. New devices still default to `other`. Unknown historical categories are included as a selected dropdown option when editing. No user choice is overwritten or inferred from a device name. Incorrect saved ventilation categories require explicit user correction through the existing editor.

### Context and performance

The complete context contains distinct source/fact/comparison evidence and safety qualifications. Rather than deleting fields or changing legacy types to achieve an arbitrary size target, this patch adds small candidate ID/evidence references only. Candidate support may retain a needed duration fact in a shortlist. Full and projected modes retain their existing budgets and overflow behavior. No duplicate full narrative is sent as candidate content. No new historical query, statistical calculation or model call is introduced.

## Executed checks

- **270 Python tests passed**: 248 existing plus 13 complementary-AI and 9 scoped-PDF tests. Three old PDF expectations were updated for the explicitly requested behavior: unvalidated legacy prose becomes trace only, raw errors stay in diagnostics, and discarded long prose no longer forces extra pages. Existing layout bounds and native PDF assertions remain.
- **147 JavaScript checks passed**: 118 UI, 16 product and 13 category checks (7 new).
- Python compilation, JavaScript/shell syntax and `git diff --check` passed.
- Mocked WebSocket cases exercise useful, valid-empty, legacy and invalid replies and assert exactly one service call. Existing transport/timeouts/heartbeat/error, disabled-AI, configuration, export and notification tests remain passing.
- Every context mode retains priorities and candidate evidence. Tests reject fabricated/unknown IDs, free text, wrong shapes, mismatched periods, negligible duration changes and false AI credit for fallback.
- Category tests reproduce the unknown-category rename bug before the fix, then verify known/custom/unknown categories, HTML escaping, default selection and save behavior.
- `validation/release025.py` loads baseline code from `256f055` in separate processes. **The entire deterministic ledger, digest and notification compare exactly equal** before/after for rounded excerpt, simulated relation, refrigeration and expanded inputs. `analysis/insights.py`, providers' algorithms, statistics, periods, comparisons and notification transport are unchanged; version-only User-Agent changes are explicit.
- Native PDFs were rendered in dark/light themes, on a simulated useful interpretation, a grouped-note case and an expanded report. Text-box checks found no text outside page widths. First-page useful/trace behavior and a grouped-note detail page were visually inspected. Normal pagination was retained; the expanded PDF has 17 pages. These are generated fixtures, not the user's original 23-page report.

Reproduction in this prepared environment:

```bash
cd /workspace/ha-reporting
export XDG_CACHE_HOME=/workspace/ha-reporting-dev/cache
export PYTHONDONTWRITEBYTECODE=1
/workspace/ha-reporting-dev/venv/bin/python /workspace/ha-reporting-dev/run.py test
node tests/test_ui.cjs
node tests/test_product_ui.cjs
node tests/test_category_defaults.cjs
/workspace/ha-reporting-dev/venv/bin/python validation/release025.py /tmp/ha-reporting-025
```

The local adapter only redirects Home Assistant absolute paths outside the checkout. Actual Home Assistant production paths are unchanged. Validation outputs stay outside the repository.

## Controlled local measurements

Five batches of ten identical calls were used for context preparation and HTML rendering; medians are shown as **0.2.4 / 0.2.5**. These measure presentation/context preparation, not historical statistical computation or model inference.

| Fixture | Context preparation (ms) | HTML rendering (ms) | Context characters |
| --- | ---: | ---: | ---: |
| excerpt | 1.77 / 1.77 | 2.08 / 1.99 | 12,492 / 12,544 |
| relation | 1.06 / 0.92 | 0.72 / 0.69 | 6,597 / 6,716 |
| notes | 0.80 / 0.82 | 0.70 / 0.85 | 6,621 / 6,673 |
| expanded | 7.49 / 7.08 | 6.87 / 7.70 | 34,439 / 34,491 |

Native PDF fixture timings ranged from approximately 0.6 to 9.6 seconds (2–17 pages) in the recorded run; different fixture sizes are not a before/after PDF speed benchmark. A separate native PDF with AI disabled was also generated successfully. Full deterministic acquisition/statistical timing and Ollama response timing were not measured: the actual services/data were unavailable. No improvement over the reported 71.1-second Ollama execution is claimed. The small additive context references have a defined purpose; no arbitrary size target, field-type change or loss of quality evidence is introduced.

## Illustrative outcomes

With simulated existing energy/cycle and duration/cycle increases, selecting `I1` yields:

> Lave-linge : La durée moyenne observée des cycles augmente également. Un fonctionnement plus long peut contribuer à la hausse de l’énergie par cycle. Des modes d’utilisation ou des charges différents sont des hypothèses, pas des causes mesurées ; comparer les conditions d’utilisation et les durées avant de conclure.

This is a mocked selection rendered from validated relations, not a captured live Ollama answer. Partial evidence adds a reservation. The opposite-duration relation explicitly says longer cycles alone cannot explain the contrast.

An empty list, generic legacy monitoring or an invalid answer does not create an interpretation paragraph. The PDF keeps the overview plus “AI Task · [configured entity] · [duration] · No validated complementary interpretation” (localized). Error details remain in stored diagnostics. No-AI configuration omits this trace entirely.

## Supplied complete reference PDF — follow-up inspection

The subsequently attached `71ed1dab-1189-4c8c-9cb0-240216fb7e9d.pdf` matches the described reference: 23 A4 pages, generated 5 November 2026 at 16:20, Europe/Zurich period 26 October–2 November, footer 6.22 s calculation / 71.1 s AI, and complete-mode context 78.6 k characters. SHA-256: `79af4e8e2088bcae02653459d8208f9febe0beba866ae8e6780b2d9a4dacd45d`. No PDF or full household source list is copied into the repository.

Text extraction confirms the deterministic overview and its existing priority order (dishwasher, washer, dryer), qualified TV reconstruction, and legacy AI section dominated by mean forecast-power difference, coverage warnings and generic TV monitoring. Detailed ratio rows repeat the exact reliability clauses targeted by the scoped-note correction. Ventilation SdB, Ventilation SdB Parents, Ventilation WC séparés and Ventilateur plafond display the configured `refrigeration` value. This confirms the presentation, but cannot establish whether the original saved choice was explicit or inherited from the historical default.

The washer displays energy/cycle +57.9% and duration/cycle +16.2% (1.19 versus 1.03 hours), with minimum contributor coverage 86.7%. This is the kind of existing qualified relation supported by the complementary interpretation mechanism. The dishwasher duration/cycle change is +5.35%, so the existing duration relevance guard avoids turning every small increase into an extra interpretation. These observations do not change any calculation, ranking or threshold.

The PDF also confirms why rounded values are not substitutes for internal results: it displays dishwasher 0.97 kWh/cycle and +12.6%, whereas calculations from rounded totals in the synthetic excerpt produce 0.96 and +13.1%. The report's displayed source percentages are recorded as documentary evidence, not forced into production calculations. Likewise, ventilation duration 4 min 34 s / 4 min 25 s has an authoritative displayed +3.25%; it must not be recomputed from those rounded durations. No original-result replay or live AI validation is inferred from inspecting the PDF.

## Remaining limits

No live Supervisor/Core/Ollama, actual model compliance, Raspberry Pi/ARM build or original unrounded histories were validated. The supplied complete reference PDF was inspected, but was not regenerated from its original execution data. Partial ratios retain their original limitations, including different missing intervals. There is no guarantee of faster Ollama inference or a particular page-count reduction. Legacy-only models may produce no new `I*` selections; they remain compatible and the deterministic report remains available. The bounded interpretation vocabulary is intentionally limited, and no general free-form hypothesis evaluator is implemented.

Passing tests do not guarantee absence of regressions on an actual installation. Version 0.2.5 is prepared locally, with no remote publication, tag or deployment.

## File inventory

- Production AI: `ha-reporting/app/analysis/ai_report.py`.
- PDF presentation: `ha-reporting/app/rendering/html_report.py`.
- Category edit preservation: `ha-reporting/app/app.js`.
- Version-only metadata: `ha-reporting/config.yaml`, `ha-reporting/run.sh`, `ha-reporting/app/providers/victoriametrics.py`, `ha-reporting/app/exporters/paperless.py`.
- Tests: `tests/test_ai_complement025.py`, `tests/test_pdf_notes025.py`, `tests/test_category_defaults.cjs`, `tests/test_energy_insights.py`, `tests/test_regressions.py`.
- Reproducible validation: `validation/release025.py`.
- Documentation: both README files, `ha-reporting/CHANGELOG.md`, root/add-on `RELEASE-NOTES-0.2.5.md` and root/add-on `VALIDATION-0.2.5.md`.
