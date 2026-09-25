# HA Reporting — 0.1.0-alpha.5

This milestone improves catalog management.

## New

- Catalog ID generated automatically from its name.
- Device ID generated automatically from its name.
- IDs are persisted in YAML and are therefore stable after creation.
- Multiple devices can be added to the same catalog.
- Custom categories can be created from the UI.
- Custom categories are stored in `/config/categories.yaml`.
- Filter: sensors only.
- Filter: selected entities only.
- Existing metric suggestions remain available.
- `_day` and `_month` helper entities remain excluded from automatic selection.

## Important ID behavior

The ID is derived from the name only at creation time. A future rename of the display name must not silently rename the stored ID.

Example:

`Vinothèque` -> `vinotheque`

Later display rename to `Vinothèque salon` keeps the stored ID `vinotheque`.

## Suggested test

1. Create catalog `Électroménager`.
2. Confirm preview ID becomes `electromenager`.
3. Add device `Vinothèque`.
4. Confirm preview ID becomes `vinotheque`.
5. Create a custom category with the `+` button if desired.
6. Search for `vinotheque`.
7. Review/select the desired entities.
8. Add the device.
9. Return to Catalogues and confirm the catalog contains 1 device.
