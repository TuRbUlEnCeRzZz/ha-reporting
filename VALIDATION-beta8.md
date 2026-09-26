# Validation — HA Reporting 0.1.0-beta.8

## Portée

Beta.8 finalise les garde-fous de formulation de l’analyse IA sans modifier le moteur statistique, le transport Home Assistant WebSocket, les rollups VictoriaMetrics ni les règles runtime validées précédemment.

Changements vérifiés :

- politique de formulation explicite pour les comparaisons (`full_period_change_allowed`, `descriptive_gap_only`, `no_change_claim`) ;
- distinction entre reconstruction du compteur courant et couverture partielle de la référence ;
- interdiction dans le prompt des conclusions annuelles affirmatives pour les comparaisons partielles/reconstruites ;
- recommandations prudentes et longueur d’analyse inchangée ;
- resynchronisation du bloc `execution` dans l’UI après achèvement asynchrone de l’AI Task ;
- ordre éditorial conservé : synthèse générale → analyse IA → données → comparaisons.

## Tests exécutés

- Python : **78 tests** — OK.
- JavaScript UI : **20 contrôles** — OK.
- `node --check ha-reporting/app/app.js` — OK.
- Compilation Python (`main.py`, `ai_report.py`, `html_report.py`, `victoriametrics.py`) — OK.
- YAML (`config.yaml`, `repository.yaml`) — OK.
- `bash -n ha-reporting/run.sh` — OK.
- Version/layout `0.1.0-beta.8` — OK.

## Régressions couvertes

- périodes strictes `[start,end)` et DST ;
- provider rollup / qualité métrique ;
- runtime plausibility, micro-corrections et fallback ciblé ;
- compteurs énergie et resets ;
- comparaisons N/N-x et température sans pourcentage relatif ;
- contexte IA compact sans séries brutes ;
- AI Task WebSocket avec `return_response`, heartbeat et timeout configurable ;
- job IA asynchrone et cache de résultat ;
- rendu HTML/PDF et échappement ;
- polling Ingress récupérant désormais les métadonnées d’exécution mises à jour.
