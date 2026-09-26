# HA Reporting — 0.1.0-beta.3

Troisième bêta du moteur de rapports pour Home Assistant OS. Le moteur statistique
alpha.23 et le rendu HTML/PDF de beta.2 restent gelés ; beta.3 ajoute l’analyse IA
optionnelle via AI Task, avec un contexte statistique compact et sans transmission
des séries brutes.

Voir [DOCS.md](DOCS.md) pour l’installation et les détails techniques.

## Analyse IA — beta.3

Un rapport peut activer une analyse IA et choisir une entité `ai_task.*`. Sans sélection explicite,
l’entité AI Task préférée de Home Assistant est utilisée. HA Reporting appelle `ai_task.generate_data`
avec le contexte statistique compact du rapport et ajoute la réponse à l’aperçu et au document HTML/PDF.

Pour Ollama no-thinking, désactiver **Think before responding** dans les options de l’entité AI Task
sélectionnée. Ce réglage appartient au provider Home Assistant et n’est pas forcé par HA Reporting.
