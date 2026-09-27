# HA Reporting 0.1.0-beta.15

Archive de développement pour Home Assistant OS.

Beta.15 conserve l’API asynchrone du pipeline complet et ajoute la passerelle native vers Home Assistant : événements de fin de job et intégration compagnon avec l’action `ha_reporting.run_report`.

Voir `ha-reporting/README.md`, `ha-reporting/DOCS.md`, `COMPANION-INTEGRATION.md` et `VALIDATION-beta15.md`.


## Intégration compagnon Home Assistant

Beta.15 fournit aussi `custom_components/ha_reporting/`. Après copie dans `/config/custom_components/ha_reporting/` et redémarrage de Home Assistant Core, l’intégration expose l’action native `ha_reporting.run_report`. L’add-on émet les événements `ha_reporting_report_started`, `ha_reporting_report_completed` et `ha_reporting_report_failed`. Voir `COMPANION-INTEGRATION.md`.
