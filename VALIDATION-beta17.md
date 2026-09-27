# Validation — HA Reporting 0.1.0-beta.17

Date : 27.09.2026

## Portée

Beta.17 consolide les automatisations internes introduites en beta.16 : historique persistant, diagnostics, retry contrôlé, récupération des jobs interrompus et affichage 24 h.

## Vérifications automatiques

- 118 tests Python : OK.
- 42 contrôles JavaScript UI : OK.
- `python -m compileall` sur l'add-on et le Companion : OK.
- `node --check app.js` : OK.
- `bash -n run.sh` : OK.
- YAML/JSON de packaging : OK.

## Régressions couvertes

- historique limité aux 50 dernières exécutions ;
- migration transparente des automatisations beta.16 sans historique/retry ;
- statut, durée, erreurs, avertissements, PDF et exports persistés ;
- un échec global planifie un retry lorsque celui-ci est activé ;
- `completed_with_errors` n'est pas relancé afin d'éviter les doublons ;
- un job actif perdu lors d'un redémarrage est marqué `interrupted` ;
- la déduplication d'un job actif ne peut pas être contournée par `scheduled` / `manual` / `retry` ;
- le prochain lancement tient compte d'un retry plus proche que la planification régulière ;
- vue Historique et réglages de retry présents dans l'Ingress ;
- saisie d'heure explicite en format `HH:MM` 24 h ;
- fuseau Home Assistant conservé pour le scheduler.

## Compatibilité

- Home Assistant OS / Raspberry Pi 4 : architecture inchangée.
- Companion beta.16 : compatible et toujours facultatif ; aucune modification de son API n'est requise pour beta.17.
- `automations.json` passe au schéma interne `version: 2`, avec lecture transparente des données beta.16.
