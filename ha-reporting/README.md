# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.13**.

Beta.13 ajoute une API d’automatisation asynchrone pour piloter le pipeline complet depuis Home Assistant ou, à terme, une intégration compagnon :

- lancement d’un rapport par `report_id` ;
- calcul statistique puis analyse IA optionnelle ;
- génération et stockage du PDF natif ;
- export vers une ou plusieurs destinations configurées, dont Paperless-ngx ;
- suivi non bloquant par `job_id` avec états, historique, erreurs, document généré et résultats d’export ;
- déduplication des demandes identiques encore actives ;
- échec d’export non destructif : le PDF local reste conservé et le job se termine avec avertissements.

Endpoints beta.13 :

- `POST /api/automation/report-jobs`
- `GET /api/automation/report-jobs`
- `GET /api/automation/report-jobs/{job_id}`

L’intégration Home Assistant native qui exposera une action `ha_reporting.run_report` reste prévue pour l’étape suivante.
