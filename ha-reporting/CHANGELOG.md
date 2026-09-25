# Changelog

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
