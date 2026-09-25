# Changelog

## 0.1.0-alpha.18

- Enforce strict `[start,end)` period semantics.
- Correct monthly expected point count (31 days @ 300 s = 8928).
- Split period coverage from sample density.
- Render historical no-data neutrally.
- Preserve statistically invalid status.
- Add invalid/unsupported counts to summaries.
- Make energy/cycle reset detection more conservative.
- Prefer direct cumulative counter delta when no plausible reset exists.
- Explicitly surface reconstructed counter results and ignored drops.

## 0.1.0-alpha.17

- First real multi-catalog report execution.
