# Validation — 0.1.0-beta.9

## Périmètre

Beta.9 ajoute le socle documentaire local sans modifier le moteur statistique ni le transport AI Task WebSocket :

- génération PDF native locale via WeasyPrint ;
- stockage persistant `/config/documents` ;
- modèles de nom configurables avec variables ;
- politiques de doublons `version`, `overwrite`, `fail` ;
- page Documents avec historique, téléchargement et suppression ;
- thème clair/sombre du PDF transmis depuis l'UI Home Assistant ;
- aucune destination externe ni Paperless dans cette version.

## Tests automatisés

- 86 tests Python : OK
- 26 contrôles JavaScript UI : OK
- syntaxe JavaScript (`node --check`) : OK
- compilation Python : OK
- YAML : OK
- syntaxe `run.sh` : OK
- version/layout add-on : OK

## PDF natif

- rendu WeasyPrint sombre : OK
- rendu WeasyPrint clair : OK
- signature `%PDF` et taille non vide contrôlées : OK
- HTML/CSS autonome, sans ressource web externe : conservé
- graphiques de comparaison : rendus par CSS statique
- pagination de finition validée sur un rapport annuel réaliste : 3 pages au lieu de 4
- cartes `unavailable` compactées sans perte de la raison d'indisponibilité
- identifiants longs : coupures contrôlées aux séparateurs `_` et `.`

## Stockage documentaire

- modèle par défaut : `{report_id}_{period_start}_{period_end}`
- extension `.pdf` ajoutée automatiquement
- variables inconnues rejetées
- caractères interdits neutralisés
- doublon `version` : `_2`, `_3`, etc. validé
- suppression du PDF et du manifeste : validée
- métadonnées de document : rapport, période, date, taille, thème, statut PDF, futur bloc `exports`

## Compatibilité

- architectures déclarées : `aarch64`, `amd64`
- Home Assistant OS / add-on Ingress : inchangé
- stockage sous `/config`, donc persistant à travers les mises à jour de l'add-on
- anciens rapports sans bloc `output` : valeurs par défaut appliquées automatiquement

## Hors périmètre volontaire

- `ExportProvider`
- Paperless-ngx
- export automatique vers une plateforme tierce
- retries d'export
- règles de rétention automatiques

Ces éléments sont réservés à beta.10 et versions suivantes.
