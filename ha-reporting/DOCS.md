# HA Reporting — 0.1.0-beta.5

Deuxième bêta pour Home Assistant OS, notamment sur Raspberry Pi 4 (aarch64).
Les calculs, contrôles de qualité, rollups, comparaisons et vérifications runtime
de l’alpha.23 restent gelés. beta.2 consolide la sortie imprimable : le document
HTML et la sortie PDF navigateur partagent désormais le même thème sombre et
conservent les graphiques de comparaison.

## Rapport HTML et sortie PDF

Après une exécution réussie, le bouton **Rapport HTML / PDF** ouvre un document
autonome généré à partir des mêmes résultats structurés. Le rendu comprend :

- l’en-tête, la période, le fuseau et les métadonnées d’exécution ;
- une synthèse de qualité (sources OK, erreurs, runtimes vérifiés, fallbacks) ;
- des cartes adaptées aux métriques puissance, énergie, temps, cycles et température ;
- les indicateurs de couverture/densité et les vérifications runtime ;
- les comparaisons N/N-x avec mini-graphiques N / référence ;
- une feuille de style A4 sombre dédiée à l’impression, avec couleurs et graphiques préservés ;
- des règles de pagination qui laissent les catalogues/appareils se fragmenter entre pages tout en gardant chaque carte source intacte.

Le document n’utilise aucune ressource web externe. Le bouton **Imprimer /
enregistrer en PDF** s’appuie pour l’instant sur la fonction d’impression du
navigateur. beta.2 demande explicitement la fidélité des couleurs d’impression
(`print-color-adjust: exact`) et ne force plus un fond blanc en mode print.
La génération PDF serveur et l’envoi Paperless restent des étapes suivantes.

L’URL technique est `GET /api/report/{id}/html`. Elle réexécute le rapport au
moment de l’ouverture afin que le document reflète les données courantes.

## Runtimes, vérification brute et fallback ciblé

Les longues périodes utilisent toujours les rollups VictoriaMetrics. Lorsqu'un
rollup runtime signale une reconstruction, une baisse ou une incohérence,
beta.2 lit les points bruts uniquement pour cette source et sa fenêtre réellement
observée. Cette lecture sert d'abord à **classifier** les transitions négatives.

Quatre classes sont distinguées : `rounding`, `minor_correction`,
`reset_candidate` et `large_drop`. Une correction est considérée bénigne seulement
si la valeur d'arrivée reste au-dessus de 0,02 h, si chaque baisse reste petite,
si la somme de toutes les baisses ne dépasse pas 0,02 h (72 s) et s'il n'y a pas
plus de deux transitions négatives sur la fenêtre. Le seuil d'arrondi reste
0,0005 h (1,8 s). Un retour proche de zéro n'est jamais classé bénin.

Si la lecture brute confirme uniquement des corrections bénignes, le résultat
reste en `provider_rollup`, le delta direct `last - first` est conservé et aucun
fallback n'est compté. Le JSON expose alors `verification.classification =
minor_corrections`. Si un reset candidat, une grande baisse, une donnée invalide
ou un export ambigu est rencontré, le fallback brut alpha.22 reste actif.

La vérification brute est donc un filet de sécurité, pas une tolérance aveugle.
`execution.raw_series_transferred` reste vrai lorsqu'une vérification brute a eu
lieu, même si le résultat final reste en rollup.

## Diagnostic conservé

Chaque fallback expose dans le JSON :

- `fallback.status` : completed ou failed ;
- `fallback.rollup_statistics` et `fallback.rollup_quality` : décision initiale ;
- `fallback.sampling: raw` et les bornes réellement lues ;
- `fallback.diagnostic` : nombre et somme des baisses, jusqu'à 20 exemples ;
- `rounding_compatible` : baisse compatible avec un demi-millième d'heure,
  purement indicative. Ce drapeau ne supprime aucun contrôle ni fallback.

La compatibilité avec un arrondi suppose une baisse au plus égale à 0,0005 h
(1,8 seconde), avec une valeur d'arrivée supérieure à 0,02 h. Elle ne prouve
pas la cause de la baisse. Le seuil n'est jamais appliqué aux cycles ou à
l'énergie, ni utilisé pour pardonner un reset.

Un export vide, incomplet, contradictoire, non fini, ambigu ou indisponible
produit une erreur sur cette source. Le rollup suspect n'est pas réutilisé
comme s'il avait été vérifié. Les bornes et le nombre de points doivent être
cohérents avec le rollup. Une modification concurrente de l'historique peut
ainsi nécessiter de relancer le rapport.

Pour protéger la mémoire du Raspberry Pi, l'export est lu ligne par ligne,
avec des limites de 200 000 points, 32 Mio au total et 1 Mio par ligne. Un
dépassement échoue explicitement sans résultat tronqué.

`retrieval_mode: series_fallback` et les compteurs de fallback sont conservés
pour les cas réellement suspects. Les corrections mineures vérifiées restent en
`provider_rollup`. `summary.sources_runtime_verified` compte ces vérifications.
`execution.raw_series_transferred` couvre à la fois vérifications et fallbacks.

## Périodes, DST et qualité

Les fenêtres des rollups sont calculées à la milliseconde, selon la précision
de stockage de VictoriaMetrics, pour respecter `[start,end)`, y compris avec
une fin fractionnaire. Un point situé exactement à end est exclu ; un point
situé exactement à start est inclus.

Les durées utilisent toujours les epochs. Une plage traversant l'heure répétée
d'automne est ordonnée selon les instants réels ; les offsets explicites
permettent de désigner les deux occurrences. Une heure locale inexistante au
printemps est rejetée. Une heure ambiguë sans offset désigne la première
occurrence, comme précédemment.

La densité de la puissance est conservée. Températures et compteurs affichent
`densité n/a` dans les modes détaillé et optimisé. Couverture et nombre de points
restent disponibles. Les règles de comparaison sont conservées.

## Installation locale

1. Décompresser l'archive. Elle contient un dossier de dépôt `ha-reporting`.
2. Copier son sous-dossier `ha-reporting` (celui qui contient `config.yaml` et
   `Dockerfile`) vers `/addons/ha-reporting` sur Home Assistant OS.
3. Actualiser le magasin des add-ons, puis installer ou reconstruire l'add-on
   local HA Reporting selon le mode d'installation existant.
4. Vérifier la version 0.1.0-beta.5 dans les journaux et relancer les rapports.

Ne pas copier le dossier de dépôt complet à la place du dossier de l'add-on.
Pour une installation issue d'un dépôt Git, mettre à jour les fichiers du même
dépôt plutôt que créer une seconde installation locale avec un stockage distinct.
L'archive contient les sources à construire par Supervisor, pas une image OCI.

## Références techniques

- [Rollups MetricsQL](https://docs.victoriametrics.com/victoriametrics/metricsql/)
- [Export JSONL VictoriaMetrics](https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/#how-to-export-data-in-json-line-format)

Voir `VALIDATION-beta5.md` à la racine du dépôt pour les tests et résultats.

## Analyse IA optionnelle (beta.5)

Dans la définition d’un rapport, activer **Inclure une analyse IA dans le rapport** puis choisir une
entité AI Task. Laisser la sélection vide utilise l’entité AI Task préférée configurée dans Home Assistant.

HA Reporting transmet uniquement des statistiques et métadonnées de qualité compactes. Les points bruts
VictoriaMetrics ne sont jamais envoyés au modèle. La consigne demande une synthèse courte en français,
des points d’attention et des recommandations prudentes, sans inventer de chiffres ni masquer les limites
de couverture.

Avec Ollama, le mode no-thinking se règle dans l’intégration Ollama en désactivant **Think before responding**.
L’action Home Assistant `ai_task.generate_data` ne permet pas de changer ce paramètre pour un appel isolé.


### Délai IA configurable

Chaque rapport peut définir `ai_analysis.timeout_seconds`. La valeur par défaut est **600 s**. L’interface propose 300, 600, 900 et 1200 s ; le backend valide toute valeur comprise entre 60 et 1800 s. Ce délai est appliqué à l’appel `ai_task.generate_data`, au garde-fou serveur et au garde-fou navigateur avec une petite marge technique. Le calcul statistique du rapport reste indépendant et disponible immédiatement.
