# HA Reporting 0.1.0-beta.3 — validation

## Objectif

Conserver sans changement le moteur statistique/runtime et le rendu HTML/PDF de beta.2,
puis ajouter une analyse IA optionnelle au niveau du rapport via l’action Home Assistant
`ai_task.generate_data`.

## Contrat de données IA

- L’IA reçoit uniquement un JSON compact construit à partir des statistiques déjà calculées.
- Les séries brutes, les aperçus de points, les diagnostics de provider détaillés et les exports
  VictoriaMetrics ne sont pas transmis.
- Le contexte contient : période, synthèse, statistiques par source, qualité utile et comparaisons N/N-x.
- L’analyse IA ne peut pas faire échouer le rapport : une erreur AI Task est enregistrée et rendue
  comme une section indisponible.

## No-thinking

L’action `ai_task.generate_data` ne possède pas de paramètre de raisonnement par appel. Pour Ollama,
le rapport doit utiliser une entité AI Task configurée avec `Think before responding` désactivé.
HA Reporting permet de sélectionner explicitement cette entité, ou d’utiliser l’entité AI Task
préférée de Home Assistant.

## Contrôles automatisés

Les tests vérifient notamment :

- construction du contexte IA sans `preview` ni points bruts ;
- extraction des réponses REST AI Task directes et namespacées ;
- appel de `/api/services/ai_task/generate_data?return_response` ;
- transmission optionnelle de `entity_id` ;
- échappement HTML de la réponse IA ;
- rendu de l’analyse IA dans le rapport interactif et HTML/PDF ;
- maintien des régressions runtime, DST, périodes, comparaisons, qualité et impression beta.2 ;
- version et layout d’installation `0.1.0-beta.3`.

## Résultat local

- 69 tests Python : OK.
- 16 contrôles JavaScript UI : OK.
- `node --check` sur `app.js` : OK.
- `bash -n` sur `run.sh` : OK.
- compilation Python de l’application : OK.
- YAML du dépôt/add-on : OK.
