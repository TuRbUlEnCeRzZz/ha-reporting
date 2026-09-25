# HA Reporting — 0.1.0-alpha.22

Version de consolidation pour Home Assistant OS, notamment sur Raspberry Pi 4
(aarch64). Les architectures aarch64 et amd64 sont conservées. Aucun changement
de catalogue, de définition de rapport ou de configuration n'est requis.

## Runtimes et fallback ciblé

Les longues périodes utilisent toujours les rollups VictoriaMetrics. Une
reconstruction, une baisse signalée ou un runtime invalide déclenche une lecture
brute uniquement de la source concernée, entre son premier et son dernier point
observés dans le rapport. Les autres sources restent en rollup.

Alpha.21 utilisait `query_range` avec un pas de 300 secondes pour ce fallback.
Cette grille pouvait manquer une baisse courte ainsi que les véritables
premier et dernier points. Alpha.22 utilise `/api/v1/export` en lecture seule,
avec les timestamps d'origine, puis le moteur de plausibilité existant.

Les contrôles physiques ne sont pas assouplis. La limite totale du moteur
détaillé utilise désormais la durée entre les points réellement observés,
sans ajouter la marge temporelle du fallback. Les valeurs runtime négatives
sont invalides. Les resets réels, y compris un petit retour à zéro, restent
reconstruits selon les règles existantes.

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

`retrieval_mode: series_fallback` et les compteurs de fallback sont conservés.
`execution.raw_series_transferred` reflète maintenant un fallback effectué.

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
4. Vérifier la version 0.1.0-alpha.22 dans les journaux et relancer les rapports.

Ne pas copier le dossier de dépôt complet à la place du dossier de l'add-on.
Pour une installation issue d'un dépôt Git, mettre à jour les fichiers du même
dépôt plutôt que créer une seconde installation locale avec un stockage distinct.
L'archive contient les sources à construire par Supervisor, pas une image OCI.

## Références techniques

- [Rollups MetricsQL](https://docs.victoriametrics.com/victoriametrics/metricsql/)
- [Export JSONL VictoriaMetrics](https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/#how-to-export-data-in-json-line-format)

Voir `VALIDATION-alpha22.md` à la racine du dépôt pour les tests et résultats.
