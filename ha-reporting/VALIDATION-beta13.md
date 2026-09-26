# Validation 0.1.0-beta.13

## Périmètre

Beta.13 ajoute l'API asynchrone d'automatisation du pipeline complet : calcul, analyse IA optionnelle, PDF natif local et exports demandés.

## Contrat API

- `POST /api/automation/report-jobs` : démarre un job et retourne HTTP 202.
- `GET /api/automation/report-jobs` : liste les jobs récents.
- `GET /api/automation/report-jobs/{job_id}` : retourne l'état, l'historique, le document, les exports, avertissements et erreur éventuelle.
- Options : `report_id`, `ai_analysis`, `generate_pdf`, `theme`, `destinations`.
- Une demande identique à un job encore actif est dédupliquée.

## États

`queued` → `running` → `data_complete` → `ai_running` (si demandé) → `pdf_generating` (si demandé) → `exporting` (si demandé) → `completed`.

Un échec non fatal d'IA ou d'export produit `completed_with_errors` et conserve le PDF local. Une erreur structurelle de calcul ou de génération PDF produit `error`.

## Régressions

- 100 tests Python : OK.
- 36 contrôles JavaScript UI : OK.
- Compilation Python : OK.
- YAML : OK.
- `run.sh` : syntaxe OK.
- Pipeline automatisé avec PDF et export : OK.
- Échec d'export non destructif : OK.
- Déduplication d'un job actif identique : OK.
- Routes API d'automatisation présentes dans le package : OK.

Le moteur statistique, les comparaisons N/N-x, la vérification runtime, le rendu PDF et les providers d'export beta.12 restent inchangés hors orchestration.
