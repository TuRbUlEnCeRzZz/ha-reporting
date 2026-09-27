# HA Reporting 0.1.0-beta.14

Archive de développement pour Home Assistant OS.

Beta.14 introduit une API asynchrone permettant d'orchestrer un rapport complet par `report_id` : calcul statistique, analyse IA optionnelle, PDF natif local et exports configurés. Le démarrage renvoie immédiatement un `job_id`, puis l'état est suivi via l'API.

Voir `ha-reporting/README.md`, `ha-reporting/DOCS.md` et `VALIDATION-beta14.md`.
