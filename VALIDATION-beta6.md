# Validation — HA Reporting 0.1.0-beta.6

## Objet

Beta.6 rend le transport AI Task robuste pour les générations longues : WebSocket Home Assistant côté add-on, job IA serveur en arrière-plan et polling court côté Ingress.

## Comportement validé

- Le calcul statistique du rapport reste indépendant et se termine immédiatement.
- Le démarrage AI Task retourne immédiatement un état `running` au navigateur.
- L'appel `ai_task.generate_data` utilise le WebSocket Home Assistant interne `ws://supervisor/core/websocket`.
- Authentification WebSocket avec `SUPERVISOR_TOKEN`.
- `call_service` utilise `return_response: true`.
- L'entité `ai_task.*` configurée est transmise dans `service_data`.
- Timeout configurable conservé : 600 s par défaut, 60–1800 s.
- Heartbeat applicatif toutes les 20 s pendant une génération longue.
- L'UI interroge l'état toutes les 2 s avec des requêtes courtes.
- Une erreur réseau ponctuelle de polling Ingress ne marque plus le job AI Task comme échoué.
- Le `conversation_id`, le transport et les diagnostics de heartbeat sont conservés dans le JSON.
- Un ancien job IA ne peut pas écraser le résultat d'un rapport réexécuté entre-temps.

## Régressions

- moteur statistique runtime / compteurs / énergie ;
- fenêtres strictes `[start,end)` ;
- DST et périodes personnalisées ;
- comparaisons N/N-x ;
- rollup VictoriaMetrics et fallback ciblé ;
- rendu HTML/PDF et analyse IA ;
- validation des timeouts IA ;
- job IA asynchrone et polling de statut.

- **75 tests Python : OK**
- **17 contrôles JavaScript UI : OK**
- `node --check` : OK
- Compilation Python : OK
- YAML : OK
- `run.sh` : OK
- Version/layout beta.6 : OK
