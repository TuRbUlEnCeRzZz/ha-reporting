# HA Reporting — 0.1.0-beta.14

Bêta 0.1.0-beta.14 pour Home Assistant OS, notamment sur Raspberry Pi 4 (aarch64).
Le moteur statistique, les comparaisons N/N-x, la vérification runtime et l'analyse IA restent inchangés. Beta.13 ajoute l'orchestration asynchrone du pipeline complet.

## API d’automatisation beta.14

HA Reporting peut désormais lancer un rapport complet via une requête courte et retourner immédiatement un `job_id`. Le travail se poursuit côté add-on : calcul, analyse IA éventuelle, PDF natif, stockage local et exports.

### Démarrer un job

```http
POST /api/automation/report-jobs
Content-Type: application/json

{
  "report_id": "rapport_domotique_mensuel",
  "ai_analysis": true,
  "generate_pdf": true,
  "theme": "dark",
  "destinations": ["paperless"]
}
```

`ai_analysis` peut être `true`, `false` ou omis. Lorsqu'il est omis, la configuration enregistrée dans le rapport décide si l'IA doit être exécutée. `destinations` exige `generate_pdf=true`, car les providers exportent le document local généré.

La réponse HTTP `202` contient le job :

```json
{
  "job": {
    "id": "…",
    "status": "queued",
    "report_id": "rapport_domotique_mensuel"
  }
}
```

### Suivre un job

```http
GET /api/automation/report-jobs/{job_id}
```

Les états possibles sont `queued`, `running`, `data_complete`, `ai_running`, `pdf_generating`, `exporting`, `completed`, `completed_with_errors` et `error`. Le résultat final contient notamment `document_id`, le nom du PDF, les exports effectués, les avertissements et l'erreur éventuelle.

```http
GET /api/automation/report-jobs
```

retourne les jobs récents. Une demande strictement identique à un job encore actif est dédupliquée et retourne le même `job_id`.

L’échec d’une destination d’export ne détruit jamais le PDF local : le job termine en `completed_with_errors`. Les erreurs de calcul ou de génération PDF restent fatales et placent le job en `error`.

Cette API constitue le contrat prévu pour l’intégration Home Assistant compagnon qui exposera plus tard une action native `ha_reporting.run_report`.

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

Voir le [README anglais](README.md#installation-on-home-assistant-os) pour l'installation et la mise à jour beta.18. Copier le dossier de l'archive contenant `config.yaml` et `Dockerfile` vers `/addons/ha-reporting`, en conservant la même installation et son stockage.

## Références techniques

- [Rollups MetricsQL](https://docs.victoriametrics.com/victoriametrics/metricsql/)
- [Export JSONL VictoriaMetrics](https://docs.victoriametrics.com/victoriametrics/single-server-victoriametrics/#how-to-export-data-in-json-line-format)

Voir `VALIDATION-beta13.md` à la racine du dépôt pour les tests et résultats.

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

## ExportProvider et Paperless-ngx (beta.11–beta.13)

Le PDF natif reste toujours généré et stocké localement avant tout export. Beta.11 introduit une interface `ExportProvider` afin qu’une destination externe ne devienne jamais une dépendance du moteur de rapport. Beta.12 ajoute le mode dossier `consume` recommandé, sans supprimer le mode API.

### Mode recommandé : dossier `consume`

La page **Documents → Destinations d’export** propose par défaut le mode **Dossier consume**. Ce mode ne demande aucun token Paperless et n’utilise pas l’API REST. HA Reporting copie le PDF local vers un dossier sous `/share`, par exemple `/share/paperless_consume`.

Sur Home Assistant OS, le partage réseau contenant le dossier `consume` de Paperless doit être monté avec un usage **Share** afin qu’il soit visible sous `/share`. L’add-on HA Reporting monte `/share` en lecture/écriture. Le bouton de test vérifie que le dossier existe et qu’HA Reporting peut y créer puis supprimer un répertoire de contrôle.

Lors de l’export, HA Reporting écrit d’abord une copie temporaire dans le même dossier, force son écriture, puis la renomme vers le nom final. Paperless ne voit donc le fichier PDF final qu’une fois la copie terminée. Si le même nom existe encore dans le dossier consume, HA Reporting ajoute `_2`, `_3`, etc.

Le statut `completed` signifie que le PDF a été **déposé** dans le dossier consume ; il ne constitue pas une confirmation que Paperless a déjà terminé l’indexation. Le PDF source reste conservé dans HA Reporting.

### Mode API optionnel

Le mode **API REST** reste disponible pour les installations qui préfèrent un envoi HTTP direct. Il utilise l’URL Paperless et un token API, ainsi que l’endpoint `/api/documents/post_document/`. Le token enregistré n’est jamais renvoyé au navigateur ; laisser le champ token vide lors d’une modification conserve le secret existant.

### Nom du fichier et suivi

L’export Paperless est manuel dans cette version. Chaque document local peut être envoyé, réenvoyé, ou retenté après une erreur. Le manifeste local conserve l’état de l’export, le nombre de tentatives, le mode utilisé, le nom envoyé et les informations de destination disponibles. Une erreur de copie, de réseau ou de Paperless ne supprime jamais le PDF local.

Le modèle de nom Paperless est optionnel. Vide, Paperless reçoit le même nom que le PDF local. Lorsqu’un modèle est défini, les mêmes variables que pour le nom local sont disponibles, ce qui permet de préparer des workflows basés sur le nom du document.

Beta.12 n’ajoute pas encore de planification d’export, de retry automatique ni de rétention automatique.


### beta.15 — intégration compagnon et événements Home Assistant

L’API asynchrone de beta.14 reste la source de vérité. Beta.15 ajoute des événements Home Assistant compacts aux transitions principales du pipeline et fournit une intégration compagnon (`custom_components/ha_reporting`) qui expose l’action native `ha_reporting.run_report`. L’action démarre le job et retourne immédiatement ; les automatisations réagissent ensuite à `ha_reporting_report_completed` ou `ha_reporting_report_failed`.

## Automatisations internes (beta.16)

L’onglet **Automatisations** permet de planifier le pipeline complet sans YAML Home Assistant ni Companion :

`rapport → IA → PDF → Documents → exports → notification`

Le fuseau horaire est lu depuis Home Assistant. Les définitions sont persistées dans `/config/automations.json` (stockage `addon_config`).

L’option Analyse IA possède trois états : suivre la configuration du rapport, forcer activée, forcer désactivée. La notification persistante réutilise le texte final de l’analyse IA lorsqu’il est disponible.

Le bouton **Exécuter maintenant** utilise le même moteur de jobs asynchrones que l’API externe et n’attend donc pas la fin de l’analyse IA dans la requête HTTP.


## Fiabilité des automatisations (beta.17)

Chaque automatisation conserve les 50 dernières exécutions avec statut, déclencheur, durée, erreurs, avertissements, PDF et résultat des exports. L’interface affiche également le prochain lancement et une éventuelle tentative de retry.

Le retry est configurable par automatisation (`enabled`, `max_retries`, `delay_minutes`) et ne s’applique qu’aux échecs globaux (`error`). Un job `completed_with_errors` n’est pas relancé afin d’éviter de dupliquer un PDF ou un export déjà réussi. Après redémarrage de l’add-on, un job qui était encore actif est marqué `interrupted` et peut être replanifié selon la même politique de retry.

Les heures sont saisies en format 24 h `HH:MM`. Le scheduler continue d’utiliser le fuseau renvoyé par Home Assistant, y compris pour les changements heure d’été/hiver.

## Beta.18 — Suivi visuel

Les cartes affichent les étapes réellement exécutées : collecte/statistiques (réalisées ensemble par appareil), IA, PDF, export et notification. Une étape désactivée ou en erreur n'est pas présentée comme réussie. Le rafraîchissement est de 3 secondes pendant une exécution, 15 secondes au repos, suspendu lorsque la page est masquée. Les détails terminaux sont persistés avec les automatisations. Les statuts API beta.17 restent inchangés ; `steps` dans les jobs et `progress` dans la liste des automatisations sont des ajouts.

L'installation et sa progression restent gérées par Home Assistant Supervisor.
