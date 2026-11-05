# HA Reporting 0.2.5 — Complementary AI interpretation and clearer reports

This consolidation release preserves the deterministic statistics, selected highlights and mobile notification introduced in 0.2.4.

- **AI as a complement:** AI Task can select verified relations between existing energy/cycle and duration/cycle observations. HA Reporting validates the evidence and renders cautious hypotheses and concrete checks, rather than accepting invented numbers, device names or fault diagnoses.
- **No filler:** if no useful interpretation is selected, the PDF keeps a concise source/duration/context trace instead of a second statistical summary. Legacy structured responses and deterministic fallback remain compatible. New responses may include an optional `interpretations` ID list; no setting or additional AI call is required.
- **Less repetitive PDF detail:** repeated known reliability clauses are grouped per device and comparison period. Each indicator keeps its numbers, units, coverage and specific qualifications. Charts, comparison tables and the dark design are preserved.
- **Historical category protection:** editing a device whose saved category no longer appears in the category list now preserves its exact value. Existing ventilation categories are not silently reclassified; correct them explicitly when appropriate.

No new dependency, mandatory setting or history request. Historical calculations, missing-data handling, quality classifications, reconstruction, derived indicators, ranking, N/N-x/EMHASS comparisons, saved options and notification recipients remain unchanged.

Validation: **270 Python tests and 147 JavaScript checks passed**. Deterministic ledger, digest and notification snapshots matched 0.2.4 exactly on identical excerpt, simulated relation, refrigeration and expanded inputs. Native PDFs were checked in both themes and with many devices. The subsequently supplied complete 23-page reference PDF was inspected. Live Ollama, Raspberry Pi/ARM and the original unrounded result remain unavailable; no inference-latency improvement or production non-regression guarantee is claimed.

The complementary interpretation vocabulary is deliberately bounded. A model returning only legacy selection fields remains compatible but does not automatically receive credit for new interpretive content. Free-form unvalidated model prose is not shown as factual analysis in the PDF; raw errors/legacy diagnostics remain accessible in stored results.

Version 0.2.5 is prepared locally. No remote tag, release or deployment is published automatically. See `VALIDATION-0.2.5.md` for evidence and remaining checks.
