# Validation — HA Reporting 0.1.0-beta.7

## Objectif

Consolider l'analyse IA sans modifier le moteur statistique : interprétation plus prudente des comparaisons incomplètes, recommandations cohérentes, durées d'exécution non ambiguës et pagination PDF propre de la section IA.

## Changements validés

- Le contexte IA compact inclut désormais la qualité de base/référence et un bloc `interpretation` par source comparée.
- Une comparaison `partial`, `reconstructed` ou à couverture limitée est explicitement signalée au prompt comme non suffisante pour affirmer une hausse/baisse de période complète.
- Le prompt privilégie la surveillance et l'accumulation d'historique lorsque la comparaison seule est faible.
- Le post-traitement retire `Aucune recommandation particulière.` si une recommandation substantielle est déjà présente.
- Les métadonnées distinguent `data_total_duration_seconds`, `ai_analysis_duration_seconds` et `total_duration_seconds`, avec `total_duration_includes_ai`.
- Le pied HTML/PDF affiche séparément le temps de calcul statistique et, lorsqu'elle existe, la durée IA.
- L’analyse IA est rendue immédiatement après la synthèse générale, avant les données détaillées et les comparaisons ; aucune coupure de page forcée n’est appliquée.

## Tests

- 78 tests Python `unittest` : OK.
- 18 contrôles JavaScript UI : OK.
- `node --check` sur `app.js` : OK.
- Compilation Python de l'ensemble de `ha-reporting/app` : OK.
- Validation YAML : OK.
- `bash -n run.sh` : OK.
- Version/layout add-on `0.1.0-beta.7` : OK.

## Non-régressions couvertes

- sémantique stricte `[start,end)` ;
- périodes DST et comparaisons ;
- VictoriaMetrics rollups/export brut ;
- plausibilité runtime et corrections mineures ;
- fallback ciblé ;
- comparaisons N/N-x ;
- HTML/PDF autonome ;
- transport AI Task WebSocket, heartbeat, timeout configurable et job asynchrone.

- Hiérarchie éditoriale vérifiée : synthèse générale → analyse IA → données justificatives → comparaisons.
