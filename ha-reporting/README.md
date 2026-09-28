# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.20**.

Beta.20 consolide l'expérience utilisateur et la précision énergétique :

- l'onglet principal **Données** décrit plus clairement les appareils, capteurs et métriques à analyser ;
- les définitions de rapports peuvent être **dupliquées** ;
- les destinations d'export sont configurées depuis **Paramètres** ;
- le fond de l'interface reprend le fond réellement rendu par Home Assistant / Liquid Glass lorsque celui-ci est accessible depuis l'Ingress ;
- le PDF sombre colore maintenant toute la feuille A4, y compris la zone de marge ;
- les pics de puissance des périodes détaillées utilisent les échantillons bruts VictoriaMetrics et la moyenne de puissance est pondérée dans le temps ;
- l'analyse IA n'est plus invitée à commenter des diagnostics internes sans incidence utilisateur ;
- les automatisations peuvent utiliser une notification persistante, une entité `notify.*` ou un TTS (`tts.*` + `media_player.*`).

La traduction dynamique n'est pas encore incluse : l'interface reste en français pour cette version.

## Notes historiques

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
