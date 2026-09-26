# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.9**.

Beta.9 introduit le socle documentaire local, sans plateforme tierce :

- génération PDF native côté add-on avec WeasyPrint ;
- thème clair/sombre du PDF aligné sur le thème actuellement visible dans HA Reporting ;
- conservation persistante locale dans `/config/documents` ;
- nom de fichier configurable par rapport avec variables dynamiques ;
- politiques de doublons `version`, `overwrite` et `fail` ;
- page **Documents** avec historique, téléchargement et suppression ;
- aperçu du nom de sortie dans le plan de rapport ;
- le PDF natif exige que l'analyse IA soit terminée lorsqu'elle est activée, afin de figer un document complet ;
- aucune intégration Paperless ni `ExportProvider` dans cette version : ce sera le chantier beta.10.

Le moteur statistique, les comparaisons, les garde-fous runtime et le transport AI Task WebSocket restent inchangés.
