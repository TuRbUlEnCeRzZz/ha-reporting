# Energy interpretation improvements — audit and validation

## Baseline and scope

Baseline: `f2833f6054fb7dd21f6b5290ff3de13696a50def` (0.2.1), retrieved from
`TuRbUlEnCeRzZz/ha-reporting`. The initial workspace contained no source checkout.
This repository implements a Supervisor app/add-on, rather than a
`custom_components` integration. No Home Assistant installation was changed.

Before edits, 187 Python tests, 118 JavaScript UI checks and 16 product UI checks
passed. Python 3.12 was used in an isolated `/tmp/ha-venv` environment, with the
existing runtime dependencies PyYAML, websocket-client and WeasyPrint (70.0).
There are no new application dependencies or changes to the Dockerfile.

## Architecture audit

- `providers/victoriametrics.py` retrieves series and rollups. It is unchanged.
- `reporting_stats/engine.py` computes counters, coverage, density, power
  integration and runtime transition diagnostics. It is unchanged.
- `analysis/device.py` performs raw runtime verification and reconstruction
  fallback. It is unchanged, including its provider request behavior.
- `periods/engine.py` resolves timezone-aware half-open intervals. It is unchanged.
- `comparisons/engine.py` retains comparable, partial, limited, reconstructed and
  unavailable classifications. It is unchanged.
- `analysis/ai_report.py` already uses a deterministic ledger and an ID-only model
  selection protocol. Values and prose are produced locally, not by the model.
- `main.py` already separates AI execution from statistics/PDF generation and
  delivers persistent, notify-entity and TTS notifications. Only notification
  message composition changed.
- `rendering/html_report.py` builds the shared HTML/PDF representation;
  `pdf_report.py` renders it with WeasyPrint. The PDF engine is unchanged.

The 0.2.1 version, stored definitions, provider settings, report periods,
AI entity/options/context levels, HTTP routes, services, events, notification
identities/recipients and delivery calls have not been edited. Existing tests
exercise normalization of old configurations and automation delivery; this is
not an end-to-end compatibility certification on Home Assistant OS.

## Changes and decisions

1. Fact ranking now resolves comparison facts to their source before scoring.
   Source energy units are normalized for ranking only. Absolute energy impact
   adds up to 400 points (8/kWh, capped at 50 kWh); changes below 0.1 kWh lose
   100 points. Relative changes retain their existing capped contribution.
   Coverage and comparison quality still affect the score. Zero consumption and
   unchanged comparisons remain in the report data, but are not summary evidence.
2. `analysis/insights.py` adds energy/cycle and runtime/cycle comparison facts.
   Joining requires known catalog/device IDs, one unambiguous counter per metric,
   matching target/period, at least 95% coverage on both periods, comparable
   wording policy, valid/nonshared sources, no reset/reconstruction flags, finite
   nonnegative values, and positive cycle denominators on both periods. Missing
   or unsupported units suppress the derived claim. Counter density is not
   arbitrarily treated as continuous sampling density. Existing counter quality
   classifications remain authoritative. These new ratios are never rounded
   before presentation and never modify the input report.
3. Derived facts carry their contributors, which remain in the projected context.
   Energy/cycle facts can include a simultaneous runtime/cycle change. Higher
   consumption with fewer cycles gets cautious explanatory wording. No efficiency
   or appliance-fault diagnosis is inferred from these ratios.
4. A validated total-meter historical comparison is mandatory alongside its
   forecast relationship when available. The first configured comparison target
   is used; the code does not invent a previous period. Repeated appliance facts
   are limited in the small AI summary budget. The existing response keys,
   four-ID summary limit and context profiles are preserved. A guarded optional
   `check_cycle_usage` action is additive to the existing action vocabulary.
5. The prompt distinguishes history, forecast, source quality and physical
   behavior. Generic advice is emitted at most once across purely generic advice
   groups. The local fallback can recommend checking operating conditions when
   energy/cycle increases by at least 20%.
6. Source density below the existing 10% partial threshold prevents a power fact
   or a forecast pairing from supporting an unqualified full-period conclusion.
   The values remain present and the warning names density/source validity.
   `detailed_reconstructed` now retains reconstructed semantics in the AI ledger,
   matching the comparison engine. Reset warnings explicitly concern measurement.
7. Fixed a demonstrated ledger identity defect: forecast relationships used
   sensor-key suffix matching despite device-local source IDs already being
   available. Distinct devices with identical sensor keys now retain their own
   energy and power relationship IDs. A regression test reproduces the collision.
8. Mobile notifications use deterministic data from the existing execution cache:
   energy, at most two appliance facts, one significant source-failure warning,
   and one justified action. No empty section or copied AI essay, no truncation,
   no extra network request, no new delivery call. A report without usable digest
   data retains the short success/AI-status fallback.
9. The PDF has a deterministic overview when useful, including when AI fails.
   Sentences already present in completed AI text are omitted from the overview
   to avoid repetition. AI prose can separate synthesis and appliance highlights.
   The runtime verification count now explains that it counts raw-history checks;
   its arithmetic is unchanged. Long quality/AI comments can wrap and split.
   Existing dark styling, source cards, comparisons, graphs and warnings remain.

Categories are user-owned catalog fields (`catalog/loader.py`, device
create/update in `main.py`), not inferred by the renderer. No catalog was supplied
that demonstrates a mistaken category assignment. Automatic reclassification
would change user configuration, so it was intentionally not implemented.

## Reproduction and results

```sh
PYTHONDONTWRITEBYTECODE=1 XDG_CACHE_HOME=/tmp/ha-cache \
  /tmp/ha-venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node tests/test_ui.cjs
node tests/test_product_ui.cjs
/tmp/ha-venv/bin/python -m compileall -q ha-reporting/app
node --check ha-reporting/app/app.js
node --check ha-reporting/app/i18n.js
git diff --check
PYTHONDONTWRITEBYTECODE=1 XDG_CACHE_HOME=/tmp/ha-cache \
  /tmp/ha-venv/bin/python validation/energy_insights.py /tmp/ha-energy-insights
```

The final Python count is 213 passing tests (187 existing + 26 new).
All 134 JavaScript checks pass; syntax, compilation and whitespace checks pass.
New tests cover normal/zero/missing/nonfinite values, zero references, partial
and reconstructed counters, repeated resets, invalid sources, ambiguous joins,
missing history/forecast, unit conversion, source density, historical versus
forecast selection, contextual recommendations, malformed model output, source
identity collisions, notification delivery count/recipients, AI-unavailable PDF,
large reports, long-comment page-width bounds, English output, duplicate prose and Zurich 23/25/168-hour periods.
Existing tests retain the numerical runtime snapshot and reconstruction checks,
timeouts, transport failures, configuration defaults and other report periods.

The reference example is a **synthetic scenario**, not a replay of the unavailable
78-source history or original PDF. It checks 58.80 kWh versus 51.73 kWh (+13.667%,
presented +13.7%), 59.7 kWh previously (-1.50754%), and 3.49/5 versus 3.10/7
kWh/cycle (0.698 versus 0.442857…, +57.61%). The supplied rounded totals imply
about -1.51%, not exactly -1.53%. No production constant forces either percentage.
The original precision/history is needed to explain that small discrepancy.

Local synthetic rendering observations (single sequential run, not a Pi benchmark):

| Case | Pages | Wall time | CPU time |
| --- | ---: | ---: | ---: |
| Baseline renderer, same synthetic input/AI text | 2 | 0.604 s | 0.602 s |
| Updated renderer | 2 | 0.522 s | 0.522 s |
| Updated renderer, 62 devices | 22 | 6.291 s | 6.291 s |

Peak RSS for the process rendering all three documents was 130,468 KiB. The
mobile text was 655 characters and the stress-case optimized context 10,698
characters. This fixture cannot establish an improvement over the real
65,800-character/52-second model run. No new model call was added.

Generated artifacts in this workspace: `/workspace/ha-artifacts/{before,after}.pdf`,
`many-devices.pdf`, `analysis.txt`, `notification.txt`, `metrics.json` and their
HTML inputs. The renderer comparison intentionally uses identical AI prose to
isolate layout changes. First-page and multipage samples were rasterized with
system Poppler and visually inspected: no overlap or table/card overflow in the
inspected samples. This is not a proof for every possible user text. Native
WeasyPrint still reports existing unsupported CSS declarations; fault-injection
tests intentionally log failures. No new application error was observed outside
those expected test paths.

## Remaining limits and deployment validation

- No real Raspberry Pi, Supervisor/Core service calls, installed Home Assistant
  entities, VictoriaMetrics database, Ollama model or original weekly PDF/history
  was available. Real-model latency, physical-memory behavior, actual notification
  display and production logs remain unverified.
- Multiple resets of the named freezer/office PC/living-room TV-PC cannot be
  independently replayed without their source history. The reconstruction
  implementation and existing regression snapshots are unchanged and pass.
- Ambient-temperature causal analysis and automatic refrigeration fault/efficiency
  diagnosis are deliberately absent. Existing temperature facts stay available;
  ambiguous shared ambient sensors are not joined speculatively.
- Derived comparisons require good, unambiguous historical counterparts. Partial,
  reconstructed and reference-free readings remain in detailed statistics rather
  than becoming unqualified per-cycle comparisons. Older saved executions without
  device IDs still render but do not receive speculative cross-source ratios.
- Total energy is identified through an explicit forecast/actual pairing or the
  existing `total_active_energy` meter convention. Overlapping appliance meters
  are never summed to invent a home total. Other arbitrary total-meter names
  without a pairing may have no dedicated mobile energy block.
- The four-ID AI summary contract and configured context budgets remain in place;
  the PDF/mobile deterministic shortlist is not an invitation to larger prompts.
  Very long user-owned names can still make a notification longer; it is selected
  by complete observations rather than forcibly cut at a character boundary.
- Changes are local to this checkout; no deployment, release or remote push was
  performed. Validate on the actual installation before treating this test result
  as a production compatibility guarantee.
