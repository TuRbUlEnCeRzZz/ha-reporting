# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.15**.

Beta.15 conserve l’API d’automatisation asynchrone et ajoute les événements Home Assistant nécessaires à l’intégration compagnon :

- lancement d’un rapport par `report_id` ;
- calcul statistique puis analyse IA optionnelle ;
- génération et stockage du PDF natif ;
- export vers une ou plusieurs destinations configurées, dont Paperless-ngx ;
- suivi non bloquant par `job_id` avec états, historique, erreurs, document généré et résultats d’export ;
- déduplication des demandes identiques encore actives ;
- échec d’export non destructif : le PDF local reste conservé et le job se termine avec avertissements.

Endpoints beta.15 :

- `POST /api/automation/report-jobs`
- `GET /api/automation/report-jobs`
- `GET /api/automation/report-jobs/{job_id}`

L’intégration compagnon fournie à la racine du dépôt expose maintenant l’action native `ha_reporting.run_report`.


## Événements Home Assistant beta.15

Les jobs d’automatisation émettent des événements compacts sur le bus Home Assistant : `ha_reporting_report_started`, `ha_reporting_report_completed` et `ha_reporting_report_failed`. L’événement de fin inclut le texte de l’analyse IA, le document local et l’état des exports, sans séries brutes.
