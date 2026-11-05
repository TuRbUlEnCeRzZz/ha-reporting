# HA Reporting 0.2.4 validation

## Baseline and diagnostic evidence

Base: `c5ff5a3` (main, package 0.2.3). Before changes: 237 Python tests executed, **236 passed and 1 failed**. The pre-existing packaging test expected 0.2.2 although config.yaml declared 0.2.3. JavaScript baseline: 118 UI + 16 product + 6 category checks passed. New failing behavior tests were added before the presentation changes. The package-version expectation now matches the explicitly requested 0.2.4.

The supplied PDF confirms why only ventilation was selected: `add_cycle_facts` required full-period wording, comparable status and >=95% coverage for both energy and cycle counters. Washer energy coverage was 91.9% / 86.7%, dishwasher 81.2% / 86.3%, and dryer approximately 87% / 86.9%. These are classified partial/exploitable by the existing comparison engine but were excluded before ratio ranking. `meaningful_change` also rejected partial totals. `qualified_attention` required >=95% and therefore excluded TV energy (93.3% / 87.9%) despite its reconstructed +102% comparison. Lowering every relevance threshold would not correct this eligibility mismatch.

The missing overview is a separate display defect: `_energy_overview` removed each sentence already found in the completed AI text, then returned an empty section. It now remains authoritative; exact repetitions are removed from the PDF's AI display instead of deleting the overview. Stored AI text is unchanged.

## Boundaries and changes

- The existing comparison engine's 80% exploitable/95% representative tiers, status labels, coverage, density and reconstruction algorithms are unchanged. Only presentation eligibility changes. Partial observed ratios carry a qualification and the minimum coverage of **all contributors**, including cycle counts, across both periods. They do not prove full-period performance or efficiency.
- Invalid, unavailable, limited, sparse-zero, ambiguous, shared or reconstructed contributors remain excluded from combined ratios. Unknown coverage is insufficient. Stable device identity and matching target ID/period are required; denominators below one cycle are rejected. Refrigeration energy per operating hour is descriptive and requires at least one observed operating hour on both sides.
- Ranking retains absolute impact, relative change, quality and device diversity. Opposing total/per-cycle trends receive an explanatory-context preference; ordinary ratio existence is not enough. No appliance names are preferred in production. Counts and mean duration help describe ventilation activity without diagnosing timer drift. Totals declining with cycle counts do not prove efficiency.
- Full-ledger priorities still feed PDF, AI projection/validation/fallback and mobile. At most three distinct appliance observations are retained. Qualified mobile ratios use concise wording. Material reconstructed energy stays in qualified attention; its original quality and numbers remain accessible in detail.
- Generic collection advice is rejected where an existing selected energy/cycle observation supports a concrete check. AI instructions distinguish observations, uncertainty and supported actions; programs/load/temperature are hypotheses, never measured facts. The existing ID-only JSON response contract is deliberately retained: the model cannot invent free-form numerical or causal commentary.
- The PDF reuses the same ledger for overview, AI display deduplication and detailed ratios. It retains its styles, charts, comparisons, themes and no-AI behavior. Qualified contributor warnings already covered in the summary are not repeated as the same comparison alert; other warnings remain available.
- No new dependency, setting, service, event, recipient or provider request. Package version, launcher banner and outgoing User-Agent strings are aligned to 0.2.4. No release/tag is published.

## Reference fixture limits

`tests/fixtures/report_023_excerpt.json` transcribes the supplied PDF's rounded values and aggregate header/counts (16 devices, 78/78 sources; 39 comparable, 32 partial, 4 limited, 3 reconstructed). Individual regression inputs are an **excerpt**, with synthetic surrounding records, not all original 78 sources. The fixture includes displayed 58.80 kWh / 51.73 kWh / 59.7 kWh, +13.7% forecast gap and -1.53% historical change.

The unrounded values/series are unavailable. For example, subtracting the rounded displayed energy gives 7.07 rather than the PDF's 7.06, and recomputing historical percentages gives -1.51 rather than -1.53. Production calculations have not been changed to force those rounded results. A regression explicitly checks that an authoritative stored percentage is rendered rather than recomputed from rounded display values. Generated examples calculated from rounded excerpt inputs must not be described as an exact original-report replay.

## Executed validation

- **248 Python tests passed** (237 existing, 11 new; two old expectations updated for explicitly requested partial-ratio/overview behavior, packaging/User-Agent expectations aligned with the release).
- **140 JavaScript checks passed**: 118 UI, 16 product, 6 category checks.
- Python compilation, JavaScript/shell syntax and whitespace checks passed.
- Existing coverage includes counter reconstruction, statistics, temperature/power, DST/periods, N/N-x, no-AI/invalid AI fallback, EMHASS, saved configuration, notification destinations and exports.
- New tests cover PDF-derived partial inputs, contributor coverage, inadequate quality, reconstructed TV attention, observed energy per operating hour/zero runtime, ventilation counts/stable duration, concise notifications, unchanged inputs, exact overview deduplication, rounded-input percentage preservation and shared priority across optimized/extended/complete/automatic contexts.
- Native dark/light PDFs generated: five pages each for the excerpt fixture. Text-box checks found no text outside page widths. The dark first page was visually inspected and the overview is present ahead of AI analysis. This does not validate the complete original PDF or every device on Home Assistant.
- Existing **non-derived numeric ledger facts** matched the 0.2.3 baseline exactly on identical excerpt/expanded inputs. Added qualified ratios and editorial selection are intentionally different.

Reproduction in this environment:

```bash
cd /workspace/ha-reporting
export XDG_CACHE_HOME=/workspace/ha-reporting-dev/cache
export PYTHONDONTWRITEBYTECODE=1
/workspace/ha-reporting-dev/venv/bin/python /workspace/ha-reporting-dev/run.py test
node tests/test_ui.cjs
node tests/test_product_ui.cjs
node tests/test_category_defaults.cjs
/workspace/ha-reporting-dev/venv/bin/python validation/release024.py /tmp/ha-reporting-024
```

The local runner redirects Home Assistant absolute paths outside the repository. It does not change production paths. The validation script uses separate baseline/current Python processes, five batches of twenty identical context+mobile+HTML iterations, and writes outputs outside the checkout.

Local presentation medians (seconds per combined iteration; optimized AI context):

| Input | 0.2.3 | 0.2.4 | Context before | Context after |
| --- | ---: | ---: | ---: | ---: |
| Excerpt | 0.00567 | 0.00695 | 11,261 chars | 12,492 chars |
| Expanded excerpt | 0.03208 | 0.04788 | 36,147 chars | 34,173 chars |

The extra excerpt context contains newly usable qualified evidence, rather than a second copy of the full report. No extra history/AI requests are made. These workstation observations do not predict Raspberry Pi/Ollama performance or establish an AI latency improvement. Complete-context mode is covered by contract tests, not a live inference benchmark.

## Example selection and notification

On the excerpt, shared appliance priorities are dishwasher (opposing total/per-cycle trends), washer (large energy/cycle increase), then dryer (lower total with fewer cycles). TV/PC is qualified reconstructed attention. This is not a claim that every source in the full 78-source report has been ranked from unrounded data. Quality or input changes can change this order; an empty selection remains valid.

The generated notification and PDFs are produced by `validation/release024.py`. Example highlights:

```text
Faits marquants
- Lave-vaisselle : 1,09 kWh/cycle contre 0,96 kWh/cycle (+13,1 %) ; 7 contre 11 cycles ; ratio observé partiel, couverture ≥81,2 %.
- Lave-linge : 0,70 kWh/cycle contre 0,44 kWh/cycle (+57,6 %) ; 5 contre 7 cycles ; ratio observé partiel, couverture ≥86,7 %.
```

## Deliberately unchanged / residual risks

Existing ventilation categories come from saved catalogues. New-device creation already defaults to `other`; no name-based classifier or migration is added, and explicit user choices are not overwritten. Correct these existing categories manually if inappropriate.

`Runtimes verified: 0` counts completed raw-history verification of suspect provider runtime rollups, not available runtime measurements. The provided PDF is compatible with no such verification being required. Without execution diagnostics this does not prove which rollups were examined. The mechanism remains unchanged.

Live Supervisor/Core, actual Ollama responses/timeouts, original raw histories, the complete original 78-source result and Raspberry Pi/ARM builds are not available. No on-device acceptance or deployment is claimed. Partial ratios can be biased by different missing intervals even when both coverages exceed 80%; they remain observed, qualified ratios, never efficiency diagnoses. The ID-only AI contract is preserved rather than replaced with a new free-form explanation architecture. Passing tests do not guarantee absence of regressions on the user's installation.

## File inventory

Production/presentation: `analysis/insights.py`, `analysis/ai_report.py`, `rendering/html_report.py` under `ha-reporting/app`.

Version alignment: `ha-reporting/config.yaml`, `ha-reporting/run.sh`, `ha-reporting/app/providers/victoriametrics.py`, `ha-reporting/app/exporters/paperless.py`.

Regression/validation: `tests/test_release024.py`, `tests/fixtures/report_023_excerpt.json`, `tests/test_energy_insights.py`, `tests/test_regressions.py`, `validation/release024.py`.

Documentation: both README files, `ha-reporting/CHANGELOG.md`, root/add-on `RELEASE-NOTES-0.2.4.md` and root/add-on `VALIDATION-0.2.4.md`.
