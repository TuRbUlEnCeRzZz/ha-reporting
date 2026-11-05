# Targeted relevance corrections for the 0.2.2 reporting changes

## Scope and baseline

The working checkout started clean at `a90eeab`, which contains the energy-insight implementation. The remote `v0.2.2` release also includes a documentation merge. No release version, tag, saved configuration schema, dependency or lockfile is changed by this patch. After rebasing, the existing package-version test was aligned with the 0.2.2 metadata already changed on main; before that alignment, it was the sole failing test (236 passed, 1 failed). When preparing the PR, the branch was rebased onto `9a15b6b`, where main already declares `0.2.2` in `config.yaml`. This patch does not change release metadata.

Before source changes, all **213 Python tests**, **118 UI checks** and **16 product UI checks** passed. New failing presentation tests were then added before applying the corrections.

The actual weekly PDF/history for **26 October–2 November 2026** was not supplied. `tests/fixtures/weekly_relevance_examples.json` records its provenance explicitly: it reproduces the quoted approximate ratios/counts using synthetic counters. It must not be presented as the original report or its statistical ground truth.

## Audit: causes and contracts

- `analysis/insights.py:add_cycle_facts` joins comparison counters. Its derived energy-impact score previously mixed changes in total usage with changes in consumption per cycle. A large increase in cycle count could therefore inflate the relevance of a nearly unchanged ratio. Positive denominators below one counter increment were also accepted.
- `analysis/ai_report.py:_fact_score` awarded both derived ratios a fixed bonus. A few seconds per operation could rank highly without a meaningful functional impact. A nonzero change was enough to fill the digest.
- `report_digest` already served the PDF overview and mobile notification, but the AI projection, model validation and fallback could choose different appliance facts. This was the main selection inconsistency.
- `_render_ledger_id` always displayed two decimals in kWh/cycle or h/cycle. Rounding could hide the actual difference while retaining a percentage calculated from full precision.
- AI attention deduplication compared complete sentences, so several source/comparison warnings for one appliance could survive. Generic collection advice was not checked against measurable activity.
- In `app.js:addDeviceTo`, loading the category options selected the browser's first option, `refrigeration`. The API already defaults missing categories to `other`; saved categories are explicitly preserved when editing sensors. This identifies a plausible creation-path cause, not proof of how any particular existing catalogue was created.

Existing contracts remain: source/target/fact IDs; the `summary`, `attention`, `recommendations` ID-only AI response; AI Task/WebSocket transport; context profiles and budgets; report/configuration keys; event/service names; notification recipients; and source/comparison quality policies. The context gains only internal selection metadata, configured category metadata, target identity, and explicit start-counter semantics where present. No new user setting is introduced.

The principal regression risks were losing qualified comparisons, joining different targets, losing optional/no-AI behavior, hiding unselected ratios, misclassifying existing devices, and changing numbers through display conversions. Tests cover these boundaries.

## Changes

1. A shared ordered `priority_highlights` selection is built from the full ledger, reused by PDF/mobile, retained across AI projection budgets and enforced during AI selection validation and fallback. At most one appliance observation per stable device identity is selected. PDF can retain three; mobile retains the first two. Empty selection is valid and uses the requested neutral sentence.
2. Selection combines the existing quality/ranking policy with unit-specific presentation guards. Energy needs absolute impact, not percentage alone; duration per operation needs both a meaningful time difference and aggregate effect. These are conservative display heuristics, **not statistical significance tests or universal appliance fault thresholds**. The existing 95% ratio-coverage rule is preserved. Large absolute energy changes remain eligible even with a modest percentage. Temperature and mean-power facts retain unit-aware support; peaks and standalone start counts do not establish energy impact.
3. Derived energy impact now isolates the per-cycle difference over the common smaller cycle count. Original totals, ratios, percentages and historical statistics remain unchanged. Ratios require at least one increment on both sides, compatible units, unambiguous device identity and the same comparison target/period. Missing, partial, reconstructed or inadequate ratio inputs are not converted into invented measurements.
4. Short durations use minutes/seconds; small energy ratios use Wh. Additional bounded display precision can distinguish values that would otherwise round identically. Percentages still use the unrounded values. If display resolution cannot distinguish two short durations, a contradictory percentage is omitted. Explicit start-counter units retain start semantics. Refrigeration ratios stay descriptive and do not generate cycle-efficiency advice; no compressor semantics are inferred from entity names.
5. A material reconstructed energy comparison with representative coverage remains usable as **qualified attention**, consistently in mobile/PDF/AI. It is not promoted into an unqualified performance headline or combined into a per-cycle ratio. Sparse or low-coverage reconstructions remain in the detailed report.
6. Quality alerts for the same device are grouped in the AI presentation; underlying source/comparison warnings are retained. Collection/monitoring advice requires measured activity. The existing recommendation protocol and actions remain unchanged, and no extra AI call is made.
7. The PDF reuses one ledger for overview and detailed derived rows. All validated ratios, including unselected small changes, remain accessible next to the existing comparison cards. Detailed energy rows do not repeat the linked duration sentence. Existing design, charts, source tables, themes and AI/unavailable states are retained.
8. Only new-device creation now selects `other` after loading categories. Existing user classifications and sensor-edit behavior are unchanged. Existing misclassifications require an explicit user edit; there is no migration or name-based reclassification.

## Preserved mechanisms

No changes to provider requests, VictoriaMetrics queries, historical series, statistical aggregation, coverage/density calculations, counter reconstruction, periods/DST, comparison calculations, report storage, scheduler, notification transport/destinations, exports, AI Task/Ollama configuration or dependencies. The renderer and AI consume existing results; they make no additional data or AI requests.

## Validation

- **237 Python tests passed**: the original 213 plus 24 targeted tests.
- **118 UI checks**, **16 product UI checks** and **6 new category behavior checks passed**.
- Python compilation, JavaScript syntax, launcher shell syntax and `git diff --check` passed.
- Existing tests continue to cover no-AI/error fallback, invalid model JSON, PDF generation, notifications/recipients, exports, EMHASS relationships, partial data and reconstructed counters.
- New tests cover zero/negligible selection, absolute versus relative impact, tiny duration changes, per-device diversity, common AI/PDF/mobile priority, display conversions and unrounded percentages, near-zero denominators, null/nonfinite values, explicit starts, category preservation, mismatched target/period identities, grouped warnings, idle advice, qualified reconstruction, and all supported period types with N-2 presentation.
- Two synthetic native PDFs (dark/light) were generated. Text-box checks confirm text fits page widths; first-page images were inspected separately. This is not on-device or full original-report acceptance.

Reproduction in the prepared environment:

```bash
cd /workspace/ha-reporting
export XDG_CACHE_HOME=/workspace/ha-reporting-dev/cache
export PYTHONDONTWRITEBYTECODE=1
/workspace/ha-reporting-dev/venv/bin/python /workspace/ha-reporting-dev/run.py test
node tests/test_ui.cjs
node tests/test_product_ui.cjs
node tests/test_category_defaults.cjs
/workspace/ha-reporting-dev/venv/bin/python validation/insight_relevance.py /tmp/ha-reporting-relevance
```

The local adapter only redirects Home Assistant's absolute `/config` and `/app` paths outside the checkout. Native execution on Home Assistant continues to use its original paths.

The validation script compares against `a90eeab` in separate Python processes, checks exact equality of ledger IDs and numeric facts (`v`, `b`, `r`, `d`, `p`) on identical weekly and 56-device synthetic inputs, benchmarks context+notification+HTML generation (five batches of twenty iterations), and writes metrics, PDFs, HTML and example text outside the repository. This measures presentation cost only, not VictoriaMetrics query latency or Ollama performance. Context growth has an identified purpose: retaining the common selected evidence/contributors and target/category semantics. It is recorded rather than claimed as an optimization.

Measured local medians (seconds per combined context+mobile+HTML iteration):

| Synthetic input | Before | After | AI context before | AI context after |
| --- | ---: | ---: | ---: | ---: |
| Weekly examples | 0.00576 | 0.00697 | 10,770 chars | 11,333 chars |
| 56 devices | 0.27198 | 0.30393 | 36,942 chars | 39,424 chars |

Numeric ledger facts matched exactly. These runs show a small additional presentation cost and approximately 5–7% more context, not an Ollama performance improvement. CPU contention makes these workstation observations unsuitable for predicting Raspberry Pi timings.

## Changed-file inventory

- `ha-reporting/app/analysis/insights.py`: shared relevance selection, physical-unit display helpers, qualified attention and digest.
- `ha-reporting/app/analysis/ai_report.py`: ranking, selection enforcement/projection, activity guards, grouped quality presentation and AI instructions.
- `ha-reporting/app/rendering/html_report.py`: shared ledger and retained detailed ratios.
- `ha-reporting/app/app.js`: neutral category only on new-device creation.
- `tests/test_insight_relevance.py`: targeted presentation/quality/compatibility regressions.
- `tests/test_regressions.py`: align the package-version assertion with the 0.2.2 metadata already changed on main.
- `README.md`, `ha-reporting/README.md`: current package version and targeted correction overview.
- `RELEASE-NOTES-insight-relevance.md`: paste-ready release update.
- `tests/fixtures/weekly_relevance_examples.json`: explicitly synthetic reference examples.
- `tests/test_category_defaults.cjs`: new-device default and preservation of existing category.
- `validation/insight_relevance.py`: reproducible baseline comparison, local benchmark and PDF generation.
- `VALIDATION-insight-relevance.md`: this audit, validation record and remaining limits.

## Example, not production measurements

The synthetic weekly fixture selects **Lave-linge → Lave-vaisselle → Sèche-linge** for the PDF. Mobile keeps the first two. With inadequate washer coverage, the washer loses priority: these names are not hard-coded preferences. Small refrigeration/ventilation ratios remain in the details. A strong, sufficiently covered reconstructed counter can instead receive a qualified attention line.

Example notification:

```text
Énergie
- L'énergie réelle de la période est de 58,80 kWh contre 51,73 kWh prévus ; écart +7,07 kWh (+13,7 %).
- Énergie électrique totale : consommation de période 58,8 kWh contre 59,7 kWh ; écart -0,9 kWh (-1,51 %). (Semaine précédente)

Faits marquants
- Lave-linge : 0,70 kWh/cycle contre 0,44 kWh/cycle (Semaine précédente) (+57,6 %) ; 5 contre 7 cycles. Moins de cycles mais davantage d’énergie totale ; les conditions d’utilisation peuvent l’expliquer, sans cause établie.
- Lave-vaisselle : 1,13 kWh/cycle contre 1,00 kWh/cycle (Semaine précédente) (+13 %) ; 7 contre 7 cycles.

Recommandation
- Vérifier si les conditions d’utilisation ou des cycles plus longs de Lave-linge peuvent expliquer la hausse d’énergie par cycle ; la cause n’est pas établie.
```

## Remaining limits and deliberately deferred work

The real weekly statistics, live Supervisor/Core services, original PDF, Ollama runtime and Raspberry Pi 4 performance were unavailable. Synthetic ratios and workstation timings do not establish production report correctness or model latency. No deployment, tag, version increment, package metadata correction, category migration, new dependency or unrelated integration change was made. Real-data validation should compare the original report's numerical tables before accepting the changed editorial selection.
