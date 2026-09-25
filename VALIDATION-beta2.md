# HA Reporting 0.1.0-beta.2 — validation

## Objectif

Conserver le moteur statistique validé en alpha.23/beta.1 et améliorer uniquement
la fidélité du rapport imprimé : thème sombre, mini-graphiques N/référence et
pagination sans page quasi vide entre les sections.

## Contrôles automatisés

- 63 tests Python : OK.
- 13 contrôles JavaScript UI : OK.
- `node --check` sur `app.js` : OK.
- `bash -n` sur `run.sh` : OK.
- compilation Python de l’application : OK.
- YAML du dépôt/add-on : OK.
- version `0.1.0-beta.2` et layout d’installation : OK.

## Régressions d’impression

Le renderer teste explicitement :

- présence de `@media print` ;
- `print-color-adjust: exact` ;
- palette sombre (`--paper:#14191f`) ;
- absence de l’ancien `body{background:#fff...}` ;
- règles de fragmentation `break-inside:auto` pour catalogues/appareils ;
- maintien des mini-barres de comparaison et de l’indicateur runtime vérifié.

## Validation visuelle

Le rapport réel anonymisé N/N-1 utilisé pendant beta.1 a été rendu en PDF de
validation avec WeasyPrint puis rasterisé à 120 dpi. Résultat : 3 pages, fond
sombre sur toutes les pages, cartes sombres, texte clair et barres N/référence
bleue/violette visibles. La page presque vide observée dans le PDF beta.1 ne
réapparaît pas dans ce rendu de validation.

Le PDF produit depuis le navigateur reste soumis aux capacités/options du moteur
d’impression du navigateur. La génération PDF côté serveur n’est pas incluse en
beta.2.
