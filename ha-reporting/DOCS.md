# HA Reporting — 0.1.0-alpha.2

This release introduces persistent YAML catalogs.

## Location

Catalogs are read from:

```text
/config/catalogs/*.yaml
/config/catalogs/*.yml
```

Create `catalogs` in the HA Reporting app/add-on configuration folder.

## Minimal test catalog

```yaml
catalog_version: 1

id: test
name: "Catalogue de test"

defaults:
  provider: victoria_metrics

devices:
  vinotheque:
    name: "Vinothèque"
    category: refrigeration
    enabled: true

    sensors:
      power:
        entity_id: sensor.REPLACE_ME_POWER
        metric: power
        unit: W

      energy:
        entity_id: sensor.REPLACE_ME_ENERGY
        metric: energy_total
        unit: kWh
```

Replace the example entity IDs with real Home Assistant entity IDs.

## Supported metric vocabulary

`power`, `energy_total`, `temperature`, `humidity`, `runtime`, `cycles`, `state`.

A bad catalog is rejected independently and does not prevent valid catalogs from loading.

## Expected log

```text
Catalog discovery complete
Loaded: 1
Rejected: 0
✓ Catalogue de test [test] — 1 device(s)
HA Reporting ready.
```

The next milestone will add the provider abstraction without changing valid version-1 catalogs.
