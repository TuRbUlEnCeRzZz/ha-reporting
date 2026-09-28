# Validation — HA Reporting 0.1.0-beta.20

Date : 28.09.2026

## Portée

Beta.20 consolide la précision des statistiques de puissance et l'intégration visuelle dans Home Assistant, sans ajouter de couche de traduction.

- pic de puissance exact à partir des échantillons bruts sur les périodes détaillées ;
- moyenne de puissance pondérée par le temps ;
- moyenne longue période basée sur `integrate()` côté VictoriaMetrics ;
- fond PDF sombre sur toute la page A4 en thème sombre ;
- fond HA Reporting repris du rendu Home Assistant / Liquid Glass lorsque disponible ;
- onglet « Données » à la place de « Catalogues » ;
- duplication de rapports ;
- destinations d'export accessibles depuis Paramètres ;
- diagnostics internes de reset/fallback filtrés du contexte IA lorsqu'ils n'affectent pas l'interprétation.

## Validation automatique

- 113 tests Python : OK ;
- 55 contrôles JavaScript UI : OK ;
- compilation Python : OK ;
- syntaxe JavaScript : OK ;
- YAML : OK ;
- `run.sh` : OK ;
- rendu PDF natif vérifié après rasterisation : fond sombre présent dans la marge A4 ;
- packaging ZIP : OK.
