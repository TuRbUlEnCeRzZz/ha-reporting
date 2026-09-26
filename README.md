# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.6**.

Beta.6 conserve le moteur statistique, les comparaisons, le rendu HTML/PDF et le timeout IA configurable, mais remplace l'appel AI Task REST longue durée par le WebSocket interne Home Assistant. L'analyse IA s'exécute désormais dans un job serveur réellement indépendant de l'Ingress ; le navigateur ne fait que suivre son état par requêtes courtes.

- Transport AI Task : `ws://supervisor/core/websocket`
- Authentification : `SUPERVISOR_TOKEN`
- Action : `ai_task.generate_data` avec `return_response: true`
- Heartbeat WebSocket : 20 s
- Polling UI : 2 s
- Timeout IA : configurable, 600 s par défaut, 60–1800 s acceptés
- Les statistiques compactes uniquement sont transmises au modèle ; aucune série brute VictoriaMetrics.

Voir [VALIDATION-beta6.md](VALIDATION-beta6.md).
