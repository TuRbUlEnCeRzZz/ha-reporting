# HA Reporting — 0.1.0-alpha.18

Data-reliability hardening before period comparisons.

## Strict report boundaries

Report periods use `[start,end)` semantics. Alpha.18 now enforces this in both
the VictoriaMetrics provider and statistics engine.

A 31-day month sampled every 300 seconds expects exactly 8928 points.

## Period coverage vs sample density

The former single density value is split into:

- **Period coverage**: how much of the requested period lies between the first
  and last available samples.
- **Sample density**: how complete the samples are inside that observed interval.

This distinguishes a source that only started halfway through a month from a
source that existed all month but was sparsely recorded.

## No history is neutral

An empty historical result is now shown as:

`Pas d'historique disponible sur cette période.`

It remains a `no_data` status and is no longer styled as a provider/statistical
error.

## Safer cumulative counters

Energy and cycle counters now prefer first-to-last delta when no plausible reset
is detected.

Downward transitions are treated as resets only when the new value is close to
the counter baseline. Other downward jumps are ignored and surfaced as
warnings.

When a genuine reset is used, the result is explicitly marked as reconstructed.

Normalized statistics expose:
- direct delta;
- reconstructed delta;
- mode (`direct`, `reconstructed`, `undetermined`);
- resets detected;
- negative transitions;
- anomalies ignored.

## Invalid data remains invalid

Statistically invalid results are no longer accidentally converted into
`no_data`. Device and report summaries now distinguish:

- OK;
- no history;
- invalid;
- unsupported;
- errors.

## Next milestone

The report pipeline is now ready for N / N-1 / N-x comparison work.
