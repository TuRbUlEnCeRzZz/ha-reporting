# HA Reporting 0.2.4 — More useful qualified observations

- Restores **Period overview** before AI analysis. Exact overview sentences are removed from the PDF's AI display, while the stored AI response is preserved.
- Makes exploitable partial energy/cycle comparisons available with explicit contributor coverage. Original quality classes are unchanged: an observed partial ratio does not establish full-period efficiency.
- Distinguishes changes in total consumption, usage counts and per-cycle consumption. More ventilation activations with similar mean duration do not establish timer drift or a fault.
- Preserves reconstructed totals as qualified attention, including exploitable partial coverage, and excludes reconstructed counters from combined ratios.
- Keeps readable Wh/kWh and minute/second formatting, detailed comparisons and no-AI reporting. Refrigeration energy per operating hour is descriptive, not a measure of efficiency.
- Retains up to three relevant mobile observations, with concise partial-ratio wording and no mandatory fill. Generic collection advice is suppressed when a selected ratio supports a more concrete check.

No new dependency or required option. Saved categories, notification services/recipients, historical calculations, coverage/density classifications, counter reconstruction, periods and AI Task/Ollama transport remain unchanged.

Validation uses the supplied v0.2.3 PDF's rounded excerpts plus synthetic surrounding records. The original unrounded result/series, live Supervisor/Ollama and Raspberry Pi runtime remain unavailable. Rounded figures are never treated as exact historical ground truth. See `VALIDATION-0.2.4.md` for executed tests, local measurements and limits.

This prepares version 0.2.4; no tag or release is published automatically. After updating, generate a representative real report and check its detailed numbers, qualifications, PDF and notification.
