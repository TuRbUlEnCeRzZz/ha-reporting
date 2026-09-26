# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.8**.

Beta.8 finalise l’analyse IA sans modifier le moteur statistique validé, le transport AI Task WebSocket ni le timeout configurable :

- les comparaisons `partial`, `reconstructed` ou à couverture insuffisante sont explicitement marquées `descriptive_gap_only` dans le contexte IA ;
- le prompt interdit désormais de présenter ces écarts comme une hausse/baisse annuelle réelle ;
- reconstruction du compteur courant et couverture partielle de la référence sont distinguées explicitement ;
- recommandations prudentes et longueur d’analyse inchangées ;
- les métadonnées asynchrones de durée sont resynchronisées dans l’UI après la fin de l’AI Task ;
- l’analyse IA reste placée après la synthèse générale et avant les données justificatives/comparaisons.

Le transport AI Task reste `ws://supervisor/core/websocket`, avec heartbeat 20 s, polling UI 2 s et timeout configurable (600 s par défaut). Aucune série brute VictoriaMetrics n’est transmise au modèle.

Voir [VALIDATION-beta8.md](VALIDATION-beta8.md).
