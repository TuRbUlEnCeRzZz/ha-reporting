# HA Reporting 0.1.0-beta.1 — validation

## Portée

Première bêta basée sur le moteur statistique alpha.23. Cette version ajoute une
couche de rendu HTML autonome et imprimable sans modifier les règles de calcul,
de qualité, de comparaison ou de vérification runtime validées en alpha.23.

## Rendu ajouté

- `GET /api/report/{id}/html` exécute le rapport et retourne un document HTML autonome.
- Le document contient résumé, catalogues, appareils, métriques, qualité et comparaisons.
- Les comparaisons exploitables possèdent des mini-graphiques N / référence sans dépendance externe.
- Les textes dynamiques sont échappés avant insertion dans le HTML.
- Une feuille de style `@media print` A4 et un bouton d'impression permettent l'enregistrement PDF côté navigateur.
- L'interface Ingress affiche `Rapport HTML / PDF` après une exécution réussie.

## Résultats des tests locaux

- Python unittest : 63 tests réussis.
- JavaScript UI : 13 contrôles réussis.
- `node --check ha-reporting/app/app.js` : OK.
- `bash -n ha-reporting/run.sh` : OK.
- YAML du dépôt : OK.
- Compilation Python : OK.
- Layout add-on et version `0.1.0-beta.1` : OK.

## Non-régression

Les régressions alpha.23 restent couvertes : fenêtres `[start,end)`, DST,
qualité métrique, rollups VictoriaMetrics, plausibilité runtime, classification
des petites corrections, fallback ciblé, compteurs, comparaisons N/N-x et
métadonnées de transfert brut.

## Limites beta.1

Le PDF n'est pas encore produit côté serveur : il est généré via l'impression du
navigateur. L'envoi vers Paperless n'est pas encore implémenté. Les graphiques
beta.1 sont des visualisations synthétiques de comparaison ; les courbes
chronologiques nécessiteront une couche de séries/downsampling dédiée.
