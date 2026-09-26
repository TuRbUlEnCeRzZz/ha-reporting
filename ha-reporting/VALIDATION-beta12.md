# Validation 0.1.0-beta.12

## Périmètre

- `ExportProvider` conservé sans modification du moteur statistique ni de l’analyse IA.
- Paperless-ngx avec deux modes : `consume_folder` recommandé et `api` optionnel.
- Dossier consume sans token, limité à `/share`.
- Test d’écriture du dossier consume sans déposer de document consommable.
- Copie atomique vers consume avec versionnage des collisions.
- API REST de beta.11 conservée avec token masqué.
- Export manuel, retry et statut persistant par document.
- PDF local conservé en cas d’échec.
- Aucun export automatique ni rétention automatique.

## Résultats

- 95 tests Python : OK.
- 36 contrôles JavaScript : OK.
- `node --check` : OK.
- `python -m compileall` : OK.
- YAML : OK.
- `run.sh` : OK.
