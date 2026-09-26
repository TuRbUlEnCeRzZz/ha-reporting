# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.7**.

Beta.7 conserve le moteur statistique, le transport AI Task WebSocket et le timeout configurable de beta.6, puis consolide l’interprétation IA et le rendu final :

- comparaisons partielles/reconstruites transmises avec leur qualité et leur couverture ;
- prompt IA plus strict : un écart sur données incomplètes n’est plus présenté comme une évolution annuelle certaine ;
- recommandations proportionnées au niveau de confiance ;
- suppression automatique de la phrase « Aucune recommandation particulière » lorsqu’une autre recommandation existe déjà ;
- métadonnées de durée distinguant calcul statistique, IA et durée totale du pipeline ;
- section IA placée après la synthèse générale et avant les données détaillées, sans saut de page forcé.

Le transport AI Task reste `ws://supervisor/core/websocket`, avec heartbeat 20 s, polling UI 2 s et timeout configurable (600 s par défaut). Aucune série brute VictoriaMetrics n’est transmise au modèle.

Voir [VALIDATION-beta7.md](VALIDATION-beta7.md).


Révision beta.7 : hiérarchie éditoriale du rapport ajustée pour présenter l’analyse IA avant les données justificatives et les comparaisons.
