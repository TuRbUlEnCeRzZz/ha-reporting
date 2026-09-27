# Validation — HA Reporting 0.1.0-beta.15

## Périmètre

- API asynchrone beta.14 conservée.
- Événements Home Assistant : `ha_reporting_report_started`, `ha_reporting_report_completed`, `ha_reporting_report_failed`.
- Résultat final du job enrichi avec le texte de l’analyse IA et son statut.
- Intégration compagnon `custom_components/ha_reporting` avec config flow et action native `ha_reporting.run_report`.
- Action non bloquante ; retour optionnel du `job_id` via `response_variable`.
- Aucun échantillon/série brute transmis sur le bus d’événements.
- Échec d’émission d’événement non destructif pour le rapport/PDF/export.

## Tests

- 105 tests Python : OK.
- 36 contrôles JavaScript UI : OK.
- Compilation Python add-on + intégration : OK.
- Syntaxe/chargement YAML et JSON : OK.
- Syntaxe `run.sh` : OK.
- Régression pipeline complet + événements started/completed : OK.
- Régression pipeline échoué + événement failed : OK.
- Régression endpoint REST Home Assistant `/api/events/...` + Bearer Supervisor : OK.
- Packaging de l’intégration compagnon et manifeste beta.15 : OK.

## Installation compagnon

Copier `custom_components/ha_reporting` dans `/config/custom_components/ha_reporting`, redémarrer Home Assistant Core, puis ajouter **HA Reporting** depuis l’interface des intégrations. URL locale proposée : `http://0800b638-ha-reporting:8099`.
