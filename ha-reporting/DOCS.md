# HA Reporting — 0.1.0-alpha.4

First visual catalog editor.

- Create a catalog from Ingress.
- Search live Home Assistant entities.
- Suggested metric types are editable.
- Initial selection ignores `_day` and `_month` helpers.
- Adds `voltage` and `current`.
- Saves version-1 YAML to `/config/catalogs`.

First test: create `Réfrigération`, device `Vinothèque`, search `vinotheque`, review the checked rows, then save. Expected file: `refrigeration.yaml`.
