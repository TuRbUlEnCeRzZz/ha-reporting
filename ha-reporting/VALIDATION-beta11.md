# Validation — 0.1.0-beta.11

Périmètre : `ExportProvider` + Paperless-ngx, sans modification du moteur statistique ni de l’analyse IA.

Résultats :

- 91 tests Python : OK ;
- 32 contrôles JavaScript UI : OK ;
- compilation Python (`compileall`) : OK ;
- syntaxe JavaScript (`node --check`) : OK ;
- YAML : OK ;
- `run.sh` (`bash -n`) : OK ;
- layout/version du package : OK ;
- authentification Paperless `Authorization: Token …` : testée ;
- test de connexion sur l’API documents Paperless : testé ;
- upload multipart vers `/api/documents/post_document/` avec nom de fichier de destination : testé ;
- persistance des statuts d’export : testée ;
- retry comptabilisé via `attempts` : testé ;
- conservation du PDF local lors d’un échec distant : testée ;
- enregistrement de la référence distante lorsqu’elle est renvoyée : testé.

Le test d’intégration réel contre l’instance Paperless de l’utilisateur reste à effectuer depuis Home Assistant OS, car l’archive ne contient évidemment ni URL ni token utilisateur.
