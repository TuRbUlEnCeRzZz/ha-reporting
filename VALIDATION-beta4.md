# HA Reporting 0.1.0-beta.4 — validation

## Correctif

- Exécution du rapport découplée de l’AI Task.
- Rapport statistique renvoyé avant l’analyse IA.
- Endpoint séparé `POST /api/report/{id}/ai-analysis`.
- Cache mémoire du dernier rapport pour le rendu HTML/PDF.
- État UI `pending/running` non bloquant.
- Garde-fou IA de 180 s côté serveur.

## Vérifications

- 69 tests Python : OK.
- 17 contrôles JavaScript UI : OK.
- `python -m py_compile` : OK.
- `node --check` : OK.
- YAML : OK.
- Version/layout add-on `0.1.0-beta.4` : OK.

Le correctif ne modifie pas le moteur statistique, les règles runtime, VictoriaMetrics, les comparaisons ni le rendu de données.
