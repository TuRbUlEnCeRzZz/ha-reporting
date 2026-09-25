# HA Reporting — 0.1.0-alpha.6

This release focuses on catalog management and Home Assistant-style navigation.

## New UI behavior

- Attempts to reuse active Home Assistant theme CSS variables when Ingress permits access.
- Keeps robust light/dark fallbacks if the parent theme cannot be read.
- Catalogs are expandable/collapsible.
- Expanded catalogs show included devices, categories and sensor counts.
- Internal **Back** button.
- Browser Back/Forward history support.
- Rename catalogs while keeping their IDs stable.
- Edit device display name and category while keeping device IDs stable.
- Delete a device from a catalog.
- Delete a complete catalog with explicit confirmation.
- Deleting configuration never deletes Home Assistant or VictoriaMetrics historical data.
- Adds an explicit **Détection auto** button for entity selection.

## Catalog vs report period

A catalog groups devices/data sources. It is intentionally independent from report periods.

Example:

- Catalog: `Électroménager`
- Reports using it:
  - Daily report
  - Monthly report
  - Annual report
  - Custom date-range report

Period and comparison logic will belong to report definitions, not catalogs.
