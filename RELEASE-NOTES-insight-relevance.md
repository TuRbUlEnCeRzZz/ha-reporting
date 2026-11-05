# HA Reporting 0.2.3 — Targeted insight relevance corrections

This update improves how HA Reporting selects and presents important observations, while preserving its existing statistical engine and detailed reports.

- **Consistent highlights:** the PDF, mobile notifications and AI Task context share the same deterministic appliance priorities. Absolute impact, relative change and measurement quality are considered together; insignificant changes no longer fill the summary.
- **Clearer derived indicators:** short durations use minutes/seconds, and small energy ratios use Wh. Percentages continue to use unrounded values. Unselected validated ratios remain available in the PDF details.
- **More cautious interpretation:** repeated quality warnings are grouped, collection advice requires measurable activity, and reconstructed-counter changes remain explicitly qualified. Cycle counters do not automatically establish efficiency, compressor behavior or equipment faults.
- **Category default correction:** new devices default to Other instead of the first category, Refrigeration. Existing user categories are preserved.

Historical calculations, counter reconstruction, reporting periods, N/N-x comparisons, EMHASS relationships, AI Task/Ollama, notification destinations and exports remain unchanged. No new dependency or required configuration setting is introduced.

Validation: **237 Python tests and 140 JavaScript checks passed**, with synthetic native PDFs generated in both themes. Numerical ledger facts matched the baseline on identical synthetic inputs. The original weekly history, live Home Assistant/Ollama services and Raspberry Pi 4 runtime were unavailable, so on-device acceptance is still required. Local measurements show a modest presentation cost and approximately 5–7% more AI context to retain shared evidence; they do not establish an Ollama latency improvement.

After updating, generate a representative report and review its numerical tables, selected highlights, PDF and notification. Correct any pre-existing device categories explicitly; this update does not migrate them automatically.
