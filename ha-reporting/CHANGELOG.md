# Changelog

## 0.1.0-alpha.12.1

- Fix temperature and other unknown numeric metrics in VictoriaMetrics.
- Add label-based VictoriaMetrics series discovery.
- Keep exact known mappings as the preferred fast path.
- Fall back to entity-label discovery when an exact mapping has no data.
- Reject ambiguous multi-series matches explicitly.

## 0.1.0-alpha.12

- Non-destructive sensor editing.
- Runtime hardening.
