# HA Reporting — 0.1.0-beta.8

Add-on de reporting pour Home Assistant OS, conçu notamment pour Raspberry Pi 4.
Le moteur statistique provider/rollup, les comparaisons N/N-x, les vérifications runtime, le rendu HTML/PDF et le transport AI Task WebSocket restent inchangés dans leur principe.

## Analyse IA — beta.8

L’analyse IA est placée en tête du contenu du rapport, juste après la synthèse générale. Les données, graphiques et indicateurs détaillés viennent ensuite pour permettre à l’utilisateur de vérifier, nuancer ou remettre en question l’interprétation proposée.


Un rapport peut activer une analyse IA et choisir une entité `ai_task.*`. Sans sélection explicite, l’entité AI Task préférée de Home Assistant est utilisée. Pour Ollama no-thinking, désactiver **Think before responding** sur l’entité AI Task sélectionnée.

HA Reporting transmet uniquement un contexte structuré compact : statistiques calculées, qualité/couverture et comparaisons. Les séries brutes VictoriaMetrics ne sont jamais envoyées au modèle.

Beta.8 finalise les garde-fous d’interprétation :

- chaque comparaison expose un `wording_policy` (`full_period_change_allowed`, `descriptive_gap_only` ou `no_change_claim`) ;
- pour une comparaison partielle/reconstruite ou à couverture limitée, le prompt interdit les formulations « a augmenté », « a diminué », « en hausse » ou « en baisse » comme conclusion de période complète ;
- le modèle doit parler d’« écart calculé sur les données disponibles » et expliciter la limite de couverture ;
- reconstruction du compteur de la période courante et couverture partielle de la référence sont deux notions séparées dans le contexte ;
- les recommandations restent proportionnées à la qualité des données ;
- « Aucune recommandation particulière » n’est conservé que si aucune autre recommandation n’est présente.

## Exécution IA non bloquante

L’analyse IA reste un job serveur indépendant. Le rapport statistique termine immédiatement, puis l’UI suit le job par polling court. Le transport est le WebSocket interne Home Assistant `ws://supervisor/core/websocket`, authentifié par `SUPERVISOR_TOKEN`, avec heartbeat toutes les 20 s. Le timeout est configurable de 60 à 1800 s, 600 s par défaut.

Les métadonnées d’exécution distinguent :

- `data_total_duration_seconds` : calcul statistique ;
- `ai_analysis_duration_seconds` : durée de l’AI Task ;
- `total_duration_seconds` : durée du pipeline jusqu’à la fin de l’IA lorsqu’elle est activée ;
- `total_duration_includes_ai` : indique si la durée totale inclut déjà l’analyse.

Le polling de l’interface récupère aussi le bloc `execution` mis à jour, afin que le JSON affiché dans l’aperçu reflète réellement la durée IA et la durée totale une fois le job terminé.

## HTML / PDF

Le rapport HTML/PDF conserve les cartes, graphiques N/Réf. et place l’analyse IA juste après la synthèse générale. En impression, l’analyse peut rester sur la première page si l’espace le permet ; le titre reste lié au début de son contenu.

Voir [DOCS.md](DOCS.md) pour l’installation et les détails techniques.
