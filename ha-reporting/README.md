# HA Reporting — 0.1.0-beta.5

Cinquième bêta du moteur de rapports pour Home Assistant OS. Le moteur statistique
alpha.23 et le rendu HTML/PDF de beta.2 restent gelés. Beta.5 conserve l’analyse IA
ajoutée en beta.3 : le rapport statistique se termine immédiatement et l’AI Task
s’exécute séparément, avec délai maximal et sans transmission des séries brutes.

Voir [DOCS.md](DOCS.md) pour l’installation et les détails techniques.

## Analyse IA — beta.5

Un rapport peut activer une analyse IA et choisir une entité `ai_task.*`. Sans sélection explicite,
l’entité AI Task préférée de Home Assistant est utilisée. HA Reporting appelle `ai_task.generate_data`
avec le contexte statistique compact du rapport et ajoute la réponse à l’aperçu et au document HTML/PDF.

Pour Ollama no-thinking, désactiver **Think before responding** dans les options de l’entité AI Task
sélectionnée. Ce réglage appartient au provider Home Assistant et n’est pas forcé par HA Reporting.

### Exécution non bloquante

Le calcul du rapport et l’analyse IA sont découplés. Le rapport reste disponible même si le modèle local est lent ou indisponible. L’interface affiche l’état de l’analyse puis injecte le résultat lorsqu’il arrive. Le délai maximal est configurable par rapport : 300, 600, 900 ou 1200 s dans l’interface, avec 600 s par défaut. Le backend accepte de 60 à 1800 s pour garder le format extensible. Le rapport statistique reste non bloquant pendant toute l’inférence.
