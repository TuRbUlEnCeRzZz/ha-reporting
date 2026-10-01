# HA Reporting 0.2.0-rc.5 validation

## Scope

RC5 optimizes the RC4 deterministic fact-ledger architecture for local LLMs. The complete report and internal ledger remain available to HA Reporting, but the AI Task receives a bounded deterministic shortlist rather than the complete ledger.

## AI contract

- Schema: `ha-reporting-ai-context-v11`
- Selection protocol: `id_only_v2_shortlist`
- Model role: select validated evidence IDs only.
- Numeric rendering: deterministic inside HA Reporting.
- Report data retention: complete; shortlist applies only to the model-facing AI context.

### Source identity and deduplication

Validated behavior:

- shared Home Assistant sources are deduplicated primarily by `entity_id` + metric/unit;
- source identity remains tied to the real sensor rather than the first report-device group that references it;
- repeated temperature/humidity sources no longer create duplicate headline facts;
- shared sources can be marked explicitly in the source registry.

### Quality signals

Validated deterministic `Q*` signals:

- `report_source_availability` summarizes total/OK/no-data/error/invalid current-period sources;
- low report availability becomes mandatory evidence, with stronger summary gating below 80% availability;
- `comparison_quality` summarizes comparable/partial/limited/reconstructed/unavailable results for each N/N-x target;
- a target with zero comparable/partial results is marked `no_representative` and becomes mandatory summary/attention evidence.

### Shortlist eligibility

Validated rules include:

- current `mean`, `period_delta` and `integrated_energy_kwh` facts require representative current-period coverage for normal summary eligibility;
- comparison headlines are restricted to comparable/partial `mean` and `period_delta` facts;
- limited/reconstructed/unavailable comparisons remain available as attention evidence but are not normal trend headlines;
- forecast/measured relationships remain deterministic and are eligible for summary only when full-period comparison is supported;
- routine `max`, `p95` and cumulative `counter_end` facts remain in the complete internal ledger but are omitted from the normal LLM shortlist.

### Deterministic rendering

Validated behavior:

- coverage values are rounded before deterministic prose rendering;
- repeated identical attention lines are deduplicated;
- free-form model output cannot change values, signs, units, percentages or source ownership because final quantitative sentences are rendered from validated IDs;
- fallback selection remains deterministic when the AI provider returns malformed/unsupported output.

## Synthetic stress test

A synthetic report was generated with:

- 421 current-period sources;
- 420 N/N-x comparison sets;
- one deliberately low-coverage critical energy source.

Observed RC5 context projection:

| Item | Complete internal ledger | Model shortlist |
| --- | ---: | ---: |
| Sources | 421 | 29 |
| N/N-x comparison sets | 420 | 28 |
| Facts | 2,522 | 28 |
| Serialized context | 304,044 characters | 12,111 characters |

Additional checks:

- model mode: `deterministic_shortlist`;
- `report_data_lossless = true`;
- the deliberately low-coverage critical source remained present through quality evidence;
- all routine report data remained available outside the model-facing projection.

This synthetic benchmark validates payload reduction, not a guaranteed wall-clock speedup. Actual inference time depends on the configured AI provider, hardware, model, context handling and Home Assistant AI Task implementation.

## Automated regression validation

Executed from the RC5 source tree:

```text
PYTHONPATH=ha-reporting/app python -m unittest tests.test_regressions
```

Result:

```text
Ran 167 tests
OK
```

JavaScript/UI regression suite:

```text
node tests/test_ui.cjs
```

Result:

```text
99 JavaScript UI checks passed
```

Additional static checks:

- `node --check ha-reporting/app/app.js` — passed;
- `node --check ha-reporting/app/i18n.js` — passed;
- `bash -n ha-reporting/run.sh` — passed;
- add-on `config.yaml` version — `0.2.0-rc.5`;
- integration `manifest.json` version — `0.2.0-rc.5`.

## VictoriaMetrics maintenance safety

RC5 does not expand the VictoriaMetrics maintenance feature beyond the RC3 read-only foundation:

- no HA Reporting catalog access from the maintenance analyzer;
- no automatic deletion;
- no VictoriaMetrics deletion endpoint;
- analysis/classification remains read-only.

## Features intentionally unchanged

RC5 keeps the already-tested behavior for:

- Home Assistant Ingress / Nabu Casa authenticated PDF downloads;
- notifications;
- PDF rendering;
- Paperless export;
- report statistic computation;
- catalog definitions and report data retention.

## Real Home Assistant OS acceptance tests

Before promoting RC5 to `0.2.0`, validate on the actual Home Assistant OS host:

1. daily forecast/measured report;
2. monthly N/N-1 report;
3. annual report without comparison;
4. annual N/N-1 report with sparse/incomplete reference history;
5. compare `Contexte IA` / shortlist counts and AI Task duration against RC4;
6. confirm source labels, rounded coverage and quality warnings in notification/PDF output.

Automated tests cannot guarantee identical behavior for every ARM build, AI provider, Ollama model, VictoriaMetrics dataset or Home Assistant Core release.
