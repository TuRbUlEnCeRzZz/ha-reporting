# Validation — HA Reporting 0.1.0-beta.16

## Périmètre

Beta.16 ajoute les automatisations internes de HA Reporting sans modifier le moteur statistique, les garde-fous runtime, l’analyse IA, le PDF natif ni les ExportProvider validés.

## Fonctionnalités couvertes

- stockage persistant des automatisations sous `/config/automations.json` ;
- fréquences horaire, quotidienne, hebdomadaire, mensuelle et annuelle ;
- fuseau horaire Home Assistant ;
- prévention d’un double lancement dans le même créneau ;
- pipeline asynchrone existant réutilisé ;
- Analyse IA : suivre le rapport / forcer activée / forcer désactivée ;
- PDF natif et thème clair/sombre ;
- destinations d’export, dont Paperless-ngx ;
- notification persistante Home Assistant contenant l’analyse IA ;
- lancement manuel « Exécuter maintenant » ;
- Companion toujours compatible mais facultatif.

## Validation automatique

- 111 tests Python : OK ;
- 42 contrôles JavaScript UI : OK ;
- compilation Python : OK ;
- syntaxe JavaScript : OK ;
- parsing YAML : OK ;
- syntaxe `run.sh` : OK ;
- packaging/version beta.16 : OK.
