# HA Reporting companion integration — beta.15

La beta.15 ajoute une intégration Home Assistant légère. Elle ne calcule aucun rapport : elle expose l'action native `ha_reporting.run_report` et envoie la requête au moteur de l'add-on.

## Installation manuelle

1. Copier `custom_components/ha_reporting/` dans `/config/custom_components/ha_reporting/` de Home Assistant.
2. Redémarrer Home Assistant Core.
3. Ajouter **HA Reporting** depuis **Paramètres → Appareils et services → Ajouter une intégration**.
4. L'URL proposée pour l'installation actuelle est `http://0800b638-ha-reporting:8099`. La modifier si le slug réseau de l'add-on est différent.

## Action native

```yaml
action: ha_reporting.run_report
data:
  report_id: rapport_domotique_mensuel
  ai_analysis: true
  generate_pdf: true
  theme: dark
  destinations:
    - paperless
```

L'action est non bloquante. Avec `response_variable`, elle retourne le `job_id` :

```yaml
action: ha_reporting.run_report
data:
  report_id: rapport_domotique_mensuel
  ai_analysis: true
  generate_pdf: true
  destinations:
    - paperless
response_variable: lancement
```

## Événements Home Assistant

L'add-on beta.15 émet :

- `ha_reporting_report_started`
- `ha_reporting_report_completed`
- `ha_reporting_report_failed`

L'événement `ha_reporting_report_completed` contient notamment `report_id`, `report_name`, `job_id`, `status`, `ai_analysis`, `document_id`, `filename`, `exports`, `warnings`, `duration_seconds` et la période résolue. Aucune série brute n'est placée sur le bus d'événements.

Exemple de notification persistante :

```yaml
triggers:
  - trigger: event
    event_type: ha_reporting_report_completed
conditions:
  - condition: template
    value_template: >
      {{ trigger.event.data.report_id == 'rapport_domotique_mensuel' }}
actions:
  - action: persistent_notification.create
    data:
      notification_id: >
        ha_reporting_{{ trigger.event.data.report_id }}
      title: >
        {{ trigger.event.data.report_name }}
      message: >
        {{ trigger.event.data.ai_analysis or 'Analyse IA non disponible.' }}
```
