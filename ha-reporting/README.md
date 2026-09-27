# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.16**.

Beta.16 ajoute un scheduler interne persistant pilotable directement depuis l’onglet **Automatisations** de HA Reporting. Il permet de choisir le rapport, la fréquence, l’override IA, le PDF, le thème, les destinations et une notification persistante contenant l’analyse IA.

Le pipeline planifié reste le même que celui validé par l’API asynchrone :

- calcul statistique ;
- analyse IA selon le rapport ou override explicite ;
- génération du PDF natif ;
- stockage local dans Documents ;
- export Paperless-ngx ou autre destination disponible ;
- notification persistante Home Assistant facultative.

Les planifications sont stockées sous `/config/automations.json` dans le stockage persistant de l’add-on. Le scheduler utilise le fuseau horaire Home Assistant et marque chaque créneau avant lancement pour éviter une double exécution dans la même minute.

Fréquences beta.16 : toutes les heures, quotidien, hebdomadaire, mensuel et annuel. Les jours inexistants (par exemple le 31 février) sont simplement ignorés pour la période concernée.

Endpoints beta.16 :

- `GET /api/scheduled-automations`
- `POST /api/scheduled-automations`
- `GET /api/scheduled-automation/{id}`
- `PATCH /api/scheduled-automation/{id}`
- `DELETE /api/scheduled-automation/{id}`
- `POST /api/scheduled-automation/{id}/run`
- `POST /api/automation/report-jobs`
- `GET /api/automation/report-jobs`
- `GET /api/automation/report-jobs/{job_id}`

Le Companion Home Assistant de beta.15/16 reste **facultatif**. Il expose `ha_reporting.run_report` pour les scénarios avancés pilotés depuis Home Assistant Core, mais les automatisations courantes peuvent désormais être entièrement gérées dans HA Reporting.

Les événements `ha_reporting_report_started`, `ha_reporting_report_completed` et `ha_reporting_report_failed` restent émis par l’add-on.
