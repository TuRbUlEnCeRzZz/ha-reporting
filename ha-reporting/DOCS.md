# HA Reporting — 0.1.0-alpha.7

UI/UX refinement release.

## Changes

- Home Assistant-style Back button using a standard arrow icon.
- Catalog disclosure control now uses a standard chevron-right / chevron-down behavior instead of a Play-like triangle.
- Smooth chevron rotation when expanding/collapsing catalogs.
- Hover tooltips clarify what **Modifier** changes:
  - catalog: display name only;
  - device: display name and category.
- Expanded Home Assistant theme bridge.
- Explicit support for Liquid Glass variables when available through Ingress:
  - card background and hover background;
  - borders;
  - shadows;
  - blur;
  - sheen and tint;
  - dialog background/blur;
  - HA primary/secondary background and header colors.
- Generic Home Assistant theme variables remain the fallback.
- Internal IDs remain stable when names are edited.

No catalog schema or reporting-engine behavior changes are introduced in this release.
