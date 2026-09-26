# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.5**.

Cette bêta conserve le moteur statistique et le rendu HTML/PDF validés, ainsi que l’analyse IA asynchrone, et rend son délai maximal configurable par rapport (600 s par défaut). Le modèle reçoit uniquement un contexte statistique compact déjà calculé par HA Reporting ; aucun point brut VictoriaMetrics n’est transmis.

Pour Ollama, le mode **no-thinking** se configure sur l’entité AI Task en désactivant `Think before responding`. HA Reporting sélectionne l’entité AI Task choisie dans le rapport, ou utilise l’entité préférée de Home Assistant lorsqu’aucune n’est imposée.

Voir [VALIDATION-beta5.md](VALIDATION-beta5.md).
