# HA Reporting 0.1.0-alpha.23 — validation

Base : archive utilisateur `ha-reporting-0.1.0-alpha.22.zip`. Aucun historique
VictoriaMetrics n'est modifié par cette version.

## Objectif

Alpha.22 identifiait correctement deux runtimes suspects, mais les traitait tous
les deux en fallback brut parce que VictoriaMetrics signalait des baisses. Les
fixtures réelles anonymisées montrent :

- compresseur vinothèque : 2 baisses, total 0,017444 h, dont une baisse d'arrondi ;
- compresseur armoire combinée : 1 baisse de 0,017 h ;
- ventilateur vinothèque : aucune baisse.

Alpha.23 vérifie les points bruts puis classe les baisses. Les deux premiers cas
sont des corrections mineures : ils conservent le delta direct et restent en
`provider_rollup`. Un retour proche de zéro, une grande baisse, trop de baisses,
une valeur négative ou un export incohérent continue de déclencher le fallback
ou une erreur explicite.

## Seuils de sécurité

- arrondi : <= 0,0005 h ;
- correction mineure : baisse <= 0,02 h avec valeur d'arrivée > 0,02 h ;
- maximum 2 transitions négatives ;
- somme maximale des baisses : 0,02 h ;
- un retour à zéro ou proche de zéro reste un `reset_candidate`.

Les seuils sont appliqués uniquement après lecture brute ciblée ; ils ne sont pas
déduits aveuglément du rollup.

## Résultat attendu sur les fixtures réelles

| Runtime | Delta | Mode final | Fallback | Vérification brute |
|---|---:|---|---:|---:|
| Vinothèque, compresseur | 20,152 h | provider_rollup | 0 | oui |
| Armoire combinée, compresseur | 58,792 h | provider_rollup | 0 | oui |
| Vinothèque, ventilateur | 22,417 h | provider_rollup | 0 | non |

Les deux vérifications conservent les exemples de transitions et leur
classification dans `verification.diagnostic`.

## Tests locaux

- 61 tests Python/YAML ;
- 13 contrôles JavaScript UI ;
- compilation Python ;
- syntaxe JavaScript ;
- syntaxe `run.sh` ;
- YAML et structure d'installation.

Les tests couvrent notamment `[start,end)`, DST, qualité métrique, compteurs,
comparaisons, export brut borné, correction mineure de 61 s, petit retour à zéro
qui doit rester un reset, et les snapshots runtime réels anonymisés.

## Validation à effectuer sur Home Assistant OS / Raspberry Pi 4

Après installation, relancer le rapport annuel sur les données VictoriaMetrics
réparées. Attendu pour les deux appareils de test : 10 sources OK, 0 erreur,
0 invalide, **0 fallback**, et **2 runtimes vérifiés**. Les valeurs évoluent
naturellement avec l'heure de fin du rapport.
