# Validation — HA Reporting 0.2.2

## Release preparation status

These documents prepare the energy-interpretation changes merged through PR #1 for a 0.2.2 release. The application package still declares 0.2.1; this documentation change does not bump runtime metadata, create a tag, publish a GitHub release or deploy an installation.

## Completed feature validation

- 213 Python tests passed: 187 existing regressions and 26 new energy-insight tests.
- 118 JavaScript UI checks and 16 product UI checks passed.
- Python compilation, JavaScript syntax and whitespace checks passed.
- Synthetic native PDFs were generated and visually inspected; the large example contained 62 devices over 22 pages. Its mobile summary contained 655 characters.
- Coverage includes counter quality/reconstruction flags, missing or zero references, derived ratios, source identity collisions, invalid AI selections, notifications, long comments and Europe/Zurich daylight-saving boundaries.

See [the full energy-insights audit](../VALIDATION-energy-insights.md) for the baseline commit, commands, numerical scenarios, resource observations and implementation decisions.

The sample figures are synthetic checks, not a replay of the unavailable 78-source weekly report. In particular, the rounded totals 58.80 and 59.7 kWh imply approximately -1.51%; they cannot independently reproduce the reference report's -1.53%.

## Still required before production acceptance

- Prepare consistent 0.2.2 package/runtime metadata and validate the resulting package.
- Build/install the app on the actual Raspberry Pi 4 and Home Assistant OS environment.
- Check existing catalogues, report definitions, schedules and stored documents after upgrade.
- Run representative reports with and without EMHASS data and AI analysis.
- Exercise the configured AI Task/Ollama provider, including failure/timeout behavior, and measure actual generation latency and resource usage.
- Verify persistent/mobile/TTS notifications, recipients, delivery count and readability.
- Inspect original freezer, office-PC and living-room TV/PC counter histories before claiming their specific reconstructions are correct.
- Check production logs and review a PDF with the actual device names, comments and comparison periods.

No on-device or real-provider compatibility claim is made by the local tests.
