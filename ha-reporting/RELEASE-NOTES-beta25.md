# HA Reporting 0.1.0-beta.25

Beta.25 improves AI report reliability by moving important forecast-versus-measured comparisons out of the language model and into HA Reporting's deterministic statistics layer.

## Highlights

- Added `ha-reporting-ai-context-v5` with a new deterministic `relationships` section.
- When one integrated forecast-power source and one measured period-energy source can be paired unambiguously, HA Reporting now calculates the energy comparison itself before calling the AI Task.
- The AI receives actual energy, integrated forecast energy, absolute difference, relative difference and both coverage values.
- When one forecast-power source and one measured-power source can be paired unambiguously, HA Reporting also supplies deterministic mean-power differences plus P95/max values as secondary context.
- AI instructions now require the summary to include the available energy forecast comparison and prioritize period-energy accuracy over isolated power peaks.
- Partial data is still preserved. Coverage determines how strongly a relationship may be interpreted; it never causes source removal.
- All cross-source arithmetic is calculated by HA Reporting, reducing the risk that smaller local models omit integrated energy, pair the wrong sources or calculate a different percentage.

## Unchanged behavior

- Power-to-energy integration introduced in beta.24 remains provider-agnostic.
- `energy_measurement` versus cumulative `energy_total` semantics remain unchanged.
- No current or comparison source is removed from the AI context, including partially covered sources.
- Long-running local AI support and the configurable timeout up to 2 hours from beta.23 remain unchanged.
- French and English UI/report languages remain supported.

## Upgrade notes

Existing reports and catalogues require no migration. A power source must still have **Statistics + energy integration** enabled if its integrated period energy should be available for forecast-versus-actual analysis. Relationships are only generated when source pairing is unambiguous inside the same report device; HA Reporting will not guess between multiple candidates.

For an EMHASS-style report, a forecast source such as `p_load_forecast` can provide both forecast-power statistics and integrated forecast energy, while a measured cumulative energy source provides the actual period consumption. No EMHASS-specific entity ID is hard-coded.

## Validation

Validation passed with **137 Python tests** and **87 JavaScript UI checks**, plus Python compilation, JavaScript syntax and shell syntax checks. Regression coverage includes deterministic relationship generation, ambiguous-pairing safeguards, partial-coverage behavior, AI prompt requirements, lossless source preservation and the existing beta.24/beta.23 functionality. See `VALIDATION-beta25.md` for the complete validation record.
