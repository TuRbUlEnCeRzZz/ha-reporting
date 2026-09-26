# HA Reporting — 0.1.0-beta.10

Bêta 0.1.0-beta.10 pour Home Assistant OS, notamment sur Raspberry Pi 4 (aarch64).
Le moteur statistique, les comparaisons N/N-x, la vérification runtime et l'analyse IA restent inchangés. Beta.9 ajoute la couche documentaire locale.

## Rapport HTML et PDF natif

Après une exécution réussie, HA Reporting propose deux sorties complémentaires :

- **Rapport HTML** : document autonome consultable dans le navigateur ;
- **Générer PDF natif** : PDF créé directement par l'add-on avec WeasyPrint, sans utiliser la boîte d'impression du navigateur ni une plateforme externe.

Le PDF reprend le même contenu structuré : synthèse générale, analyse IA lorsqu'elle est activée, données justificatives, comparaisons N/N-x et graphiques. Le thème clair/sombre est aligné sur le thème visible dans HA Reporting au moment de la génération.

Le PDF est conservé dans le stockage persistant de l'add-on sous `/config/documents` et apparaît dans la page **Documents**, depuis laquelle il peut être téléchargé ou supprimé.

Si l'analyse IA est activée et encore en cours, la génération PDF native est refusée temporairement afin d'éviter de figer un rapport incomplet.

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
4. Vérifier la version 0.1.0-beta.10 dans les journaux et relancer les rapports.

Ne pas copier le dossier de dépôt complet à la place du dossier de l'add-on.
Pour une installation issue d'un dépôt Git, mettre à jour les fichiers du même
dépôt plutôt que créer une seconde installation locale avec un stockage distinct.
L'archive contient les sources à construire par Supervisor, pas une image OCI.

## Références techniques

- [Rollups MetricsQL](https://docs.victoriametrics.com/victoriametrics/metricsql/)
- [Export JSONL VictoriaMetrics](https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/#how-to-export-data-in-json-line-format)

Voir `VALIDATION-beta10.md` à la racine du dépôt pour les tests et résultats.

## Analyse IA optionnelle (beta.6)

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


### beta.6 — AI Task WebSocket

Long AI analyses use Home Assistant's internal WebSocket API through the Supervisor proxy. The report calculation completes independently, the AI job continues server-side, and the Ingress UI polls only short status requests. The AI timeout remains configurable (default 600 s).


## Transport IA beta.6

L'analyse IA n'utilise plus une requête REST longue. HA Reporting ouvre le WebSocket interne Home Assistant via `ws://supervisor/core/websocket`, authentifié avec `SUPERVISOR_TOKEN`, puis appelle `ai_task.generate_data` avec `return_response: true`. Le job IA reste côté serveur ; l'interface Ingress ne fait que des requêtes courtes de suivi d'état toutes les 2 secondes. Des heartbeats applicatifs maintiennent le canal observable pendant les générations longues.


## Finition IA — beta.8

Beta.8 conserve le transport WebSocket de beta.6 mais verrouille le vocabulaire des comparaisons incomplètes. Le contexte compact transmet `base_quality`, `reference_quality` et un bloc `interpretation` enrichi pour chaque source comparée : limitation de couverture côté N et N-x, reconstruction éventuelle de chaque côté, capacité ou non à conclure sur la période complète, et `wording_policy`.

Lorsque `wording_policy=descriptive_gap_only`, l’AI Task ne doit pas écrire qu’une grandeur « a augmenté », « a diminué », « est en hausse » ou « est en baisse » sur la période complète. Elle doit formuler l’écart comme un résultat descriptif sur les données disponibles et rappeler la couverture insuffisante.

La reconstruction du compteur courant est distinguée de la couverture historique : par exemple, `base_quality.counter_mode=provider_reconstructed` signifie que N a été reconstruit après reset, tandis que `reference_quality.period_coverage_percent=34.8` signifie séparément que la référence N-x est partielle. Le prompt interdit de fusionner ces notions sous une formulation ambiguë comme « reconstruction partielle ».

Un post-traitement minimal supprime uniquement la contradiction « Aucune recommandation particulière » lorsqu’une autre recommandation est déjà présente ; il ne réécrit pas le fond de l’analyse. La longueur et le ton prudent restent inchangés.

Les temps restent séparés entre moteur statistique et IA. Après achèvement de l’AI Task, le cache serveur met à jour `ai_analysis_duration_seconds`, `ai_analysis_finished_at_epoch`, `pipeline_finished_at_epoch`, `total_duration_seconds` et `total_duration_includes_ai=true`. Beta.8 transmet aussi ce bloc `execution` au polling Ingress afin que le JSON affiché dans l’interface soit resynchronisé, et pas seulement le HTML/PDF généré depuis le cache.

En impression, l’analyse IA reste placée juste après la synthèse générale, avant les données détaillées et les comparaisons qui servent de référence pour vérifier ou contester l’interprétation.


## PDF natif et documents (beta.10)

Chaque définition de rapport peut configurer un modèle de nom de fichier et une politique de doublons. Le PDF natif est généré localement par l'add-on avec WeasyPrint puis conservé dans le stockage persistant de l'add-on sous `/config/documents`.

Variables disponibles pour le nom : `{report_id}`, `{report_name}`, `{year}`, `{month}`, `{day}`, `{period_start}`, `{period_end}`, `{period_type}`, `{generated_date}`, `{generated_datetime}`, `{comparison}`.

Politiques de doublons :

- `version` : crée automatiquement `_2`, `_3`, etc. ;
- `overwrite` : remplace le document local portant le même nom ;
- `fail` : refuse la génération si le nom existe déjà.

La page **Documents** permet de consulter l'historique local, télécharger un PDF ou le supprimer. Lorsque l'analyse IA est activée, la génération PDF attend que son état ne soit plus `pending`/`running`, afin de figer un document complet.

Beta.10 n'effectue aucun export vers une plateforme tierce. L'abstraction `ExportProvider` et Paperless-ngx sont réservés à beta.11.
