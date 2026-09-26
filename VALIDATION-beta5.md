# Validation — HA Reporting 0.1.0-beta.5

## Objet

Beta.5 rend le délai maximal de l’analyse IA configurable par rapport tout en conservant l’exécution asynchrone introduite en beta.4.

## Comportement validé

- Valeur par défaut : **600 s**.
- Choix UI : **300 / 600 / 900 / 1200 s**.
- Validation backend : **60 à 1800 s**.
- Compatibilité ascendante : un rapport beta.3/beta.4 sans `timeout_seconds` utilise 600 s.
- Le délai configuré est appliqué à l’appel Home Assistant `ai_task.generate_data`.
- Le garde-fou serveur attend le délai configuré avec une petite marge technique.
- Le garde-fou navigateur suit la même configuration avec une marge de 15 s.
- L’exécution statistique du rapport reste non bloquante et indépendante de l’IA.
- Le timeout choisi est exposé dans les diagnostics `report.ai_analysis` / `ai_analysis`.

## Régressions exécutées

- **71 tests Python : OK**
- **17 contrôles JavaScript UI : OK**
- `node --check` : OK
- Compilation Python : OK
- YAML : OK
- `run.sh` : OK
- Références de version beta.5 : OK

## Couverture ajoutée

- timeout AI Task par défaut à 600 s ;
- timeout personnalisé transmis à la requête Home Assistant ;
- bornes de validation 60–1800 s ;
- conservation des régressions runtime, DST, `[start,end)`, comparaisons, rendu HTML/PDF et analyse IA.
