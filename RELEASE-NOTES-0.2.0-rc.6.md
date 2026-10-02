# HA Reporting 0.2.0-rc.6

`0.2.0-rc.6` is a focused stabilization release on top of RC5. It keeps the deterministic shortlist architecture and addresses the last issues found during real daily, monthly and annual report testing.

## Highlights

### Correct units for integrated forecast energy

- Fixes deterministic rendering of `integrated_energy_kwh` facts.
- Derived energy from a power source is now always rendered as **kWh**, even though the original source sensor is expressed in `W` or `kW`.
- Prevents outputs such as `Integrated energy 6.85 W` / `Énergie intégrée 6,85 W` while keeping the underlying source and report statistics unchanged.

### Mandatory validated forecast-versus-actual relationships

- Introduces **`ha-reporting-ai-context-v12`** and the **`id_only_v3_relationship_priority`** selection protocol.
- Validated `energy_forecast_vs_actual` relationships are mandatory summary evidence.
- Validated `power_forecast_vs_actual` relationships are also mandatory summary evidence after period-energy comparison.
- This ensures that a complete EMHASS forecast/measured comparison cannot be omitted merely because the LLM selected unrelated current-period facts.
- Relationships with insufficient coverage remain attention-only and still do **not** expose a calculated full-period gap.

### Cleaner recommendations

- Recommendation actions targeting the same real Home Assistant source are grouped before rendering.
- When one source needs both data-quality caution and reconstructed-counter monitoring, HA Reporting emits one combined recommendation instead of duplicate bullets.
- Global quality (`Q*`) and forecast relationship (`R*`) recommendations remain separate semantic topics.

## Unchanged behavior

- RC5 deterministic shortlisting, report-wide quality signals and source deduplication remain unchanged.
- The complete report dataset and complete internal fact ledger remain lossless; only the model-facing context is shortlisted.
- VictoriaMetrics maintenance remains read-only and independent from HA Reporting catalogs.
- Same-session Home Assistant Ingress / Nabu Casa downloads, notifications, PDF generation and Paperless export remain unchanged.

## Validation

RC6 validation includes Python regression tests, JavaScript UI checks, Python compilation, JavaScript syntax checks, shell syntax validation, metadata parsing and ZIP integrity verification. See `VALIDATION-0.2.0-rc.6.md` for details.

## Recommended real-world acceptance tests before 0.2.0

1. Run a daily EMHASS report and verify that integrated energy is displayed in **kWh** and that both validated energy and mean-power forecast-versus-measured relationships appear in the summary.
2. Run the monthly N/N-1 report and verify that the current-period EMHASS relationship is present while the incomplete N/N-1 forecast remains limited.
3. Run the annual N/N-1 report and verify that the deterministic global comparison-quality warning remains the headline when no representative N/N-x comparison exists.
4. Confirm that sources with both limited/reconstructed conditions no longer generate redundant recommendation bullets.
