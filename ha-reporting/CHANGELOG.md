# Changelog

## 0.1.0-beta.2

- Preserve the dark standalone HTML visual language when printing or saving as PDF.
- Add exact print color adjustment so report backgrounds and N/reference comparison bars are retained by supporting browsers.
- Stop forcing a white print canvas; use the same dark report palette for screen and print.
- Relax print fragmentation for catalogs and devices while keeping individual source cards together, preventing orphan catalog headings and near-empty pages.
- Keep headings attached to the content that follows and reduce print spacing without flattening cards or comparison graphics.
- Add print-fidelity regressions for dark colors, chart bars, and pagination rules.

## 0.1.0-beta.1

- Freeze the alpha.23 runtime/statistics behavior as the first beta baseline.
- Add a standalone HTML report renderer with no external assets or JavaScript dependencies.
- Add a dedicated `GET /api/report/{id}/html` endpoint that executes the report and returns the rendered document.
- Add a `Rapport HTML / PDF` action in the report preview after a successful execution.
- Add print-specific A4 styling and an `Imprimer / enregistrer en PDF` action.
- Render metric-aware source cards for power, energy, runtime, cycles and temperature.
- Preserve data-quality context, runtime verification and fallback indicators in the rendered report.
- Add N/N-x comparison sections with compact base/reference bar charts and absolute/relative deltas when applicable.
- Keep HTML output self-contained and escape catalog, device and entity text before rendering.
- Add renderer regressions and packaging checks for the new rendering module.

## 0.1.0-alpha.23

- Classify runtime negative transitions as rounding, minor correction, reset candidate or large drop.
- Raw-verify suspicious runtime rollups before deciding whether a fallback is actually required.
- Keep provider rollup and direct delta when raw history proves only benign minor corrections.
- Preserve raw fallback for reset candidates, large drops, invalid data and ambiguous exports.
- Accept at most two benign negative transitions totaling at most 0.02 h (72 s); a return near zero is never accepted as benign.
- Expose `verification` diagnostics and `sources_runtime_verified` separately from fallbacks.
- Keep `execution.raw_series_transferred` accurate when raw verification occurs without fallback.
- Show verified minor runtime corrections in the report UI.
- Add regressions for benign 61 s corrections, tiny return-to-zero resets and real anonymized runtime snapshots.

## 0.1.0-alpha.22

- Preserve original runtime rollup diagnostics and raw negative transitions.
- Replace sampled runtime fallback with bounded, targeted raw JSONL export.
- Retain fallback for actual drops; rounding compatibility is diagnostic only.
- Fail closed on partial, conflicting, ambiguous or excessive raw exports.
- Check runtime plausibility against observed samples, including negative values.
- Enforce millisecond-accurate half-open rollup windows.
- Handle explicit autumn DST folds and reject nonexistent spring local times.
- Apply metric-aware density to detailed analysis as well as rollups.
- Report actual raw fallback transfers and clarify the UI message.
- Make server startup import-safe for repeatable report integration tests.
- Add Python, YAML, JavaScript regressions and anonymized real runtime fixtures.

## 0.1.0-alpha.21

- Validate optimized runtime against the actually observed source window.
- Add targeted detailed fallback for suspicious provider-rollup runtime.
- Limit fallback queries to affected runtime history windows.
- Add transparent `series_fallback` metadata and fallback counts.
- Fix elapsed period duration across DST.
- Preserve custom comparison elapsed duration across DST.
- Make optimized data density metric-aware.
- Display event-driven optimized sources as `density n/a`.
- Retain provider-side density for power.

## 0.1.0-alpha.20

- Scalable long-period provider rollups.
- Long-period quality-aware comparisons.
