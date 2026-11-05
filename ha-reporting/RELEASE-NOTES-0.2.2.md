# HA Reporting 0.2.2 — More useful energy insights

HA Reporting 0.2.2 improves how reports interpret energy usage, compare periods and present useful observations on mobile. It builds on the existing reporting engine with deterministic calculations and guarded AI selection.

## What changed

- **More relevant observations:** ranking considers absolute energy impact, relative change and measurement quality. Idle equipment and unchanged comparisons no longer fill the summaries; their readings remain in the detailed report.
- **Energy and runtime per cycle:** when counters are unambiguous, comparable and sufficiently covered, reports calculate kWh/cycle and hours/cycle. This helps distinguish a change in usage from a change in consumption per cycle without claiming an efficiency improvement or diagnosing a fault.
- **Clearer comparisons:** the historical change of the validated total meter is shown alongside its forecast gap when available. Consuming more than an EMHASS forecast is distinct from consuming more than the previous period.
- **More focused AI analysis:** the existing ID-only selection protocol gains validated per-cycle facts and a guarded, contextual verification action. Recommendations are less repetitive, while the code continues to own numerical calculations and final wording.
- **Better quality handling:** low sampling density limits full-period power/forecast conclusions. Reconstructed counter flags are retained, and a counter reset is explicitly treated as a measurement event rather than evidence of an appliance fault.
- **Shorter mobile notifications:** notifications select energy figures, up to two appliance observations, a significant source warning when present and one justified action. They no longer copy the full AI text or end with a hard character cut.
- **Targeted PDF improvements:** a deterministic overview remains useful when AI is unavailable, repeated AI sentences are avoided, long comments wrap more safely, and the runtime verification count now explains its meaning. The dark presentation and detailed statistics are retained.
- **Forecast pairing fix:** devices using identical sensor keys keep their own forecast/actual relationship identities in the AI context.

For example, a washer using 3.49 kWh over 5 cycles versus 3.10 kWh over 7 cycles can be described as approximately 0.70 versus 0.44 kWh/cycle. The report suggests checking operating conditions rather than asserting a cause.

## Upgrade and compatibility

No new configuration option, application dependency or additional AI call is introduced. The historical statistics, counter reconstruction, period and comparison engines are unchanged. Stored catalogues, schedules, report modes, AI Task entity settings, notification recipients and delivery mechanisms retain their existing interfaces. User-owned categories are not automatically reclassified.

AI remains optional. Statistics and PDF generation remain available when AI Task or Ollama fails, with deterministic observations where the available data supports them. Per-cycle comparisons are omitted when source identity, history, coverage or counter quality is insufficient; the underlying readings remain in the detailed report.

After installing the packaged release, run a representative report and check the PDF and configured notification on the actual Home Assistant installation.

## Validation and remaining limits

Local validation passed: **213 Python tests** (187 existing and 26 new), **118 UI checks**, **16 product UI checks**, Python compilation and JavaScript syntax checks. Synthetic native PDFs were rendered and visually inspected, including a 62-device, 22-page example and a 655-character notification.

The original weekly history/PDF, Raspberry Pi runtime, real Home Assistant service calls and actual Ollama responses were unavailable. These results do not certify production compatibility or real-model latency. No production deployment was performed.

See `VALIDATION-0.2.2.md` for the validation scope and remaining acceptance checks.
