# HA Reporting

Add-on Home Assistant OS — version **0.1.0-beta.12**.

Beta.12 conserve l’architecture `ExportProvider` de beta.11 et rend l’intégration Paperless-ngx plus simple et robuste :

- **mode dossier `consume` recommandé et sans token**, via un chemin sous `/share` ;
- mode API REST avec URL + token conservé comme option avancée ;
- test de la destination depuis l’interface ;
- export manuel d’un PDF déjà stocké depuis **Documents** ;
- modèle de nom Paperless optionnel, avec retour automatique au nom local lorsqu’il est vide ;
- copie atomique vers le dossier `consume` : le fichier final n’apparaît qu’une fois complètement écrit ;
- versionnage `_2`, `_3`, etc. si un fichier du même nom est encore présent dans `consume` ;
- état d’export persistant par document, avec mode, erreurs et nombre de tentatives ;
- un échec Paperless ne supprime ni n’invalide jamais le PDF local.

Pour le mode `consume`, Home Assistant OS doit exposer le partage Paperless sous `/share`, par exemple `/share/paperless_consume`. Le PDF local reste l’artefact de référence.

Cette version n’ajoute volontairement ni planification d’export ni rétention automatique.
