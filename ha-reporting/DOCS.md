# HA Reporting technical documentation

## 0.2.0-rc.4 — Selection-only fact ledger

RC4 changes the AI boundary again: the provider no longer writes the quantitative report. HA Reporting builds the complete deterministic `ha-reporting-ai-context-v10` ledger, the AI selects evidence IDs, and HA Reporting renders the final numbers and sentences itself.

### Selection protocol

The model must return one JSON object only:

```json
{
  "summary": ["R1", "F42"],
  "attention": ["C7"],
  "recommendations": [
    {"action": "collect_more_data", "evidence": "C7"}
  ]
}
```

`summary` and `attention` contain existing ledger IDs only. Recommendations use one of four allow-listed actions: `collect_more_data`, `monitor_forecast`, `monitor_source`, or `verify_reconstructed_counter`, each tied to validated evidence. Unsupported IDs and actions are discarded.

### Deterministic rendering

HA Reporting resolves the selected ID back to its source, metric, unit and statistic, then writes the quantitative sentence itself. A comparison fact therefore cannot borrow another device name, another source's coverage, another unit or another percentage. `period_delta` and `counter_end` remain separate by construction.

Headline eligibility also excludes normal power `max`/`p95` facts. Those values remain in the lossless ledger and in the detailed report, but they cannot be promoted by the model into the main AI summary. This is specifically intended to keep smoothed forecast peaks from being treated as overload or calibration alarms.

If the AI provider returns prose, malformed JSON or no valid summary ID, HA Reporting uses a deterministic fallback selection and still renders a grounded three-section analysis.


## 0.2.0-rc.3 — Fact-ledger AI contract and VictoriaMetrics maintenance inventory

`0.2.0-rc.3` changes the model-facing contract instead of adding more prompt-only prohibitions. It also adds a read-only maintenance diagnostic for VictoriaMetrics.

### AI context v9: deterministic fact ledger

`ha-reporting-ai-context-v9` preserves the semantic data previously sent to AI, but separates it into three layers:

1. `sources` — a compact registry containing source identity, metric/unit and current-period quality metadata;
2. `comparison_sets` — N/N-x metadata for exactly one source and one reference target;
3. `facts` — atomic statistics. Each fact contains exactly one statistic such as `mean`, `max`, `period_delta` or `integrated_energy_kwh`.

Compact field aliases are documented in the embedded `legend`. Unlike the old v3 positional rows, a fact never contains an ordered bundle such as `[max, p95, mean]`; the statistic name remains explicit. This keeps the context compact while sharply reducing opportunities for small local models to swap statistics or merge neighbouring comparisons.

A quantitative sentence must be supported by exactly one fact or one deterministic `relationship`. The prompt also requires physical quantities to remain stable: °C cannot become consumption, W cannot become energy, and an absolute kWh gap cannot become an invented percentage.

Forecast-versus-measured max/P95 values remain available as context, but a peak gap alone is explicitly not evidence of overload, bad calibration, bad sensor placement or a fault.

### VictoriaMetrics maintenance inventory

**Settings → Maintenance → VictoriaMetrics** adds a read-only analysis endpoint and UI. It:

- uses the existing VictoriaMetrics provider URL;
- queries VictoriaMetrics `/api/v1/series` for Home Assistant-labelled historical series across the retained history;
- retrieves the live Home Assistant entity set through the Supervisor/Core API;
- does not load or inspect HA Reporting catalogs;
- groups VM series by Home Assistant `(domain, entity_id)`;
- classifies entries as `active`, `orphaned`, `protected` or `indeterminate`;
- exposes series counts and metric names for diagnostics.

The first cleanup policy is deliberately conservative. Missing `sensor` and `binary_sensor` entities can be shown as orphaned. Missing entities from other domains are protected. Incomplete VM label metadata is indeterminate. RC3 provides **no delete route**, no background cleanup and no automatic mutation of VictoriaMetrics.

### Validated behaviour carried forward

RC1/RC2 deterministic comparison gating, limited-percentage suppression, sparse-zero handling, long-running AI timeouts, PDF generation, Paperless export and same-session Ingress/Nabu Casa downloads remain unchanged.

---

## 0.2.0-rc.1 — Deterministic direction and comparison gating

`0.2.0-rc.1` is the first release candidate for the 0.2.0 milestone. It builds on beta.26 without adding a new provider or reporting feature. The goal is to make model-facing interpretation harder to misuse before the stable release.

### AI context v7

`ha-reporting-ai-context-v7` keeps every current and comparison source and adds deterministic direction metadata to validated full-period N/N-x statistics. When a statistic supports a complete-period trend claim, HA Reporting emits `trend_direction` as one of `increase`, `decrease` or `unchanged`. This field is authoritative; the AI Task is explicitly instructed not to reverse it.

Partial and limited comparisons still keep base/reference values and absolute gaps, but they do not receive a full-period `trend_direction`. Their wording policy remains descriptive rather than trend-assertive.

### Limited comparison percentages

When the comparison engine classifies a source as `limited`, relative percentages are now suppressed for all comparison statistics. HA Reporting preserves the base value, reference value and absolute difference and records `relative_change_reason: limited_comparison` when no stronger reason already applies. This avoids values such as `+945%` being highlighted from a reference that covers only a small fraction of the period.

### Current-period cross-source comparison gating

The AI Task may compare two current-period sources only when HA Reporting emitted a deterministic `relationship`. For forecast-versus-measured relationships, both sides must satisfy the >=95% full-period coverage rule before HA Reporting emits an absolute/relative performance gap.

If coverage is insufficient, the relationship remains present with the individual forecast/measured values and their coverage, but uses `comparison_policy: coverage_insufficient_for_period_gap` and omits gap/direction fields. The AI is instructed to mention values separately if useful and not to invent a monthly/daily performance gap.

### Downloads

The beta.26 document-download fix is unchanged: the Documents page uses an authenticated same-origin Ingress `fetch()` and downloads a local Blob. The release-candidate validation therefore includes an explicit real-device Nabu Casa download check.

---


## beta.26 — Comparison reliability and Ingress-safe downloads

Beta.26 does not remove or trim report data. It changes how HA Reporting qualifies comparisons and how those reliability facts are exposed to the renderer and AI Task.

### Coverage and density

Period coverage and sampling density are separate concepts. The comparison engine now uses these coverage tiers:

- **>=95%**: representative (`comparable`) when no other limitation applies;
- **80% to <95%**: `partial`, usable with caution;
- **<80%**: `limited`, not suitable for a full-period trend claim.

Power sensors in Home Assistant are frequently event-driven, so a density below 80% is not automatically a missing-period condition. For power only, density below 10% adds a partial-data warning and density below 2% marks the comparison limited. This preserves useful power comparisons such as appliance histories with 10-40% event density while still flagging genuinely sparse histories.

### Near-zero references and sparse zero values

A relative percentage can become arbitrarily large when its reference rounds to zero. beta.26 therefore keeps the absolute gap but suppresses the relative percentage below metric-aware reference floors (for example 0.1 W for power and 0.1 kWh for energy). The comparison value records `relative_change_reason: near_zero_reference`; no source or absolute statistic is removed.

For power, an all-near-zero signal with sampling density below 10% is marked `sparse_zero_uncertain`. The model and renderer can then distinguish a confirmed zero from a value that may simply result from insufficient history.

### AI context v6

`ha-reporting-ai-context-v6` retains every current and comparison source. It adds rules telling the AI that >=95% coverage is representative, that low event density is not the same as low period coverage, that near-zero percentages must not be recreated, and that sparse-zero values must not be described as confirmed inactivity. Deterministic forecast-versus-measured relationships now require >=95% coverage on both sides before `full_period_comparison_supported` becomes true.

### Home Assistant Ingress PDF downloads

The backend download route and UTF-8 `Content-Disposition` handling are unchanged. The frontend no longer calls `window.open(..., "_blank")` for local documents because a new browser tab—especially from the Companion app or Nabu Casa—may not retain the Ingress authentication context. The Documents page now performs a same-origin authenticated `fetch()`, converts the response to a Blob, and triggers a local download without navigating away from HA Reporting.

---

## beta.25 — Deterministic cross-source AI relationships

Beta.25 keeps the self-describing, lossless source records from beta.24 and adds deterministic relationships calculated by HA Reporting before the AI Task call. The purpose is to remove one remaining source of ambiguity for smaller local language models: deciding which forecast and measured sources belong together and performing arithmetic across them.

### Relationship generation

Relationships are provider-agnostic and are created only inside one report device when pairing is unambiguous. HA Reporting never drops partial sources to create them.

For one forecast `power` source with `integrated_energy_kwh` and one measured `energy_total` source with `period_delta`, HA Reporting emits `energy_forecast_vs_actual` with:

- `forecast_energy_kwh`;
- `actual_energy_kwh`;
- `absolute_gap_kwh` (`actual - forecast`);
- `relative_gap_pct`, using forecast energy as the reference when non-zero;
- forecast and actual coverage;
- `full_period_comparison_supported`, true only when both coverages are at least 80%.

For one forecast power source and one measured power source, HA Reporting emits `power_forecast_vs_actual` with the forecast/measured means, deterministic mean gap, optional relative mean gap, P95 and maximum values, plus coverage. Power values are normalized to watts for the relationship (`W` and `kW` are supported). Energy counters are normalized to kWh (`Wh` and `kWh` are supported).

If more than one candidate measured source or forecast source exists in the device, HA Reporting does not guess a pairing and does not emit that relationship. The original source records remain available to the model.

### AI interpretation policy

`ha-reporting-ai-context-v5` adds a top-level `relationships` array. These relationship values are deterministic report facts and the AI is instructed not to recalculate them. When `energy_forecast_vs_actual` is available, the summary must include actual period energy, integrated forecast energy, absolute gap and relative gap when available. The energy comparison is prioritized over isolated peak-power differences.

When `full_period_comparison_supported` is false, the values are still preserved but the AI must state the coverage limitation and avoid presenting the gap as a reliable full-period performance conclusion. A power relationship may be used to compare mean power, while P95/max are secondary context rather than standalone evidence of overall forecast quality.

No source is omitted by beta.25. The existing 90,000-character preferred size and 220,000-character application guard remain unchanged; the downstream AI provider/model still enforces its own token context.

---

## beta.24 — Source semantics, power integration and AI context v4

Beta.24 adds a generic derived-energy path for power sources and changes the model-facing context from positional normalization to self-describing records.

### Power → energy integration

A catalogue source with `metric: power` may persist `derive_energy: true`. This does not replace any power statistic. The analysis still exposes peak, P95 and time-weighted mean, and additionally publishes `statistics.integrated_energy_kwh`.

For provider rollups, VictoriaMetrics already returns `integrate(<power>[window])`; HA Reporting converts the power-unit-seconds integral to kWh. For detailed series analysis, numeric Home Assistant history is treated as a stateful gauge: each power value remains active until the next recorded change inside `[start, end)`, and the same piecewise-constant integral is converted to kWh. `W` and `kW` source units are supported.

The derived value is shown only when the source opted into energy integration. This keeps the feature generic: an EMHASS `p_load_forecast` source can expose both forecast-power statistics and period forecast energy, but the code contains no EMHASS-specific branch.

### Energy measurements versus cumulative counters

Automatic metric detection now reads Home Assistant `state_class`. A kWh/Wh sensor with `state_class: measurement` is proposed as `energy_measurement`; cumulative/legacy energy sensors continue to use `energy_total`. Existing catalogue definitions are not silently migrated because the stored metric is an explicit user choice.

`energy_measurement` is analyzed as a gauge. It is not given counter reset semantics and is not automatically interpreted as period consumption.

### AI context v4

`ha-reporting-ai-context-v4` is still lossless at the semantic report layer: no current-period or comparison source is omitted, including partial sources. Raw samples remain intentionally outside the AI contract.

The important change is semantic locality. Every source record contains its readable source path, metric, unit, quality information and named values together. Power records use keys such as `max`, `p95`, `mean` and optional `integrated_energy_kwh`; cumulative counters use `period_delta` and `counter_end`. Comparison records likewise use named `base`, `reference`, `gap` and optional percentage fields.

This removes the v3 requirement for a model to join positional arrays with a separate legend and source registry. The prompt also states that:

- `max`, `p95` and `mean` are authoritative names and must not be swapped;
- `period_delta` is the period change/consumption;
- `counter_end` is a cumulative ending reading and must never be reported as a period delta;
- `integrated_energy_kwh` belongs to the exact power source that produced it;
- forecast/prevision sources must not be described as measured values;
- `energy_measurement` is not a cumulative counter.

Self-describing records cost more characters than v3. beta.24 therefore treats 90,000 characters as the preferred operating size and keeps an application guard at 220,000 characters. No trimming occurs at either threshold. The downstream AI provider/model still enforces its own token context and may reject a request below or above these character counts depending on tokenizer behavior.

---

## beta.23 — Long-running local AI analysis

Beta.23 extends the per-report AI Task timeout range for slow local inference without changing the deterministic statistics pipeline or the beta.22 lossless AI context.

- `AI_DEFAULT_TIMEOUT_SECONDS = 600` (10 minutes).
- `AI_MIN_TIMEOUT_SECONDS = 60`.
- `AI_MAX_TIMEOUT_SECONDS = 7200` (2 hours).
- The report editor offers 5, 10, 15, 20, 30 and 45 minutes, then 1 hour, 1 hour 30 minutes and 2 hours.
- Persisted custom values inside the supported range remain valid and are reinserted into the selector when a report is edited.
- The browser polling guard uses the configured timeout plus a small 30-second margin.
- The server-side AI worker remains independent of the Ingress page and keeps WebSocket heartbeat traffic active every 20 seconds while waiting for the Home Assistant AI Task response.
- Timeout messages use human-readable durations and the selected report language.

A timeout only limits how long HA Reporting waits for the AI Task response. HA Reporting closes its WebSocket connection when the timeout is reached, but a downstream provider such as Ollama may continue processing if Home Assistant/provider cancellation does not propagate. For long local jobs, choose a timeout with enough headroom instead of relying on repeated timeout/retry cycles.

The `ha-reporting-ai-context-v3` serialization introduced in beta.22 remains lossless at the semantic report level: partial-coverage sources and comparisons are retained.


## beta.22 — Lossless AI context normalization

Beta.22 uses the `ha-reporting-ai-context-v3` semantic schema for AI Task input. The deterministic report result is unchanged; only the model-facing representation is normalized. Raw VictoriaMetrics samples, previews, provider traces and renderer-only data remain outside the AI contract.

The AI path keeps two thresholds:

- `AI_TARGET_CONTEXT_CHARS = 50000`: preferred operating size;
- `AI_MAX_CONTEXT_CHARS = 60000`: hard safety guard before the AI Task call.

Unlike the earlier beta.22 draft, the final beta.22 path does **not** trim sources to reach the preferred target. Every current-period source and every comparison source is serialized, including partial-coverage entries. If the lossless normalized context is still above the hard limit, the AI stage returns an explicit error instead of dropping data.

### v3 representation

The v3 schema reduces repetition structurally:

- catalogues, devices and sources are declared once and referenced by their array index;
- categories, metrics, units, statuses, policies, statistic names, warnings and reasons use shared registries;
- current-period rows use positional columns declared by `legend.current`;
- comparison rows use positional columns declared by `legend.comparison`;
- metric-specific current values use `legend.value_schemas`;
- optional trailing fields are omitted only when their documented default applies; this changes serialization size, not semantic content;
- a compact flag string records runtime verification, non-applicable density and base/reference reconstruction.

The context sets `lossless: true`. Here, lossless means that HA Reporting does not omit semantic source/comparison entries or the values/quality fields represented by the AI schema. It does not mean raw time-series samples are sent to the model.

A completed AI result includes diagnostic fields under `ai_analysis.input`: final context characters, preferred/hard limits, beta.21 compact-context size, v3 schema, normalization mode, `context_lossless`, current-source count and comparison-source count. The Ingress and HTML/PDF renderers display the final size and the no-omission guarantee.

The implementation deliberately stays with one AI Task call. If a future installation produces a lossless v3 context above 60,000 characters, multi-call chunking can be evaluated separately rather than silently reintroducing source omission.

---

## beta.21 — Internationalization and HTTP reliability

Beta.21 introduces an i18n compatibility layer in `app/i18n.js`. It contains stable message IDs with French and English values, translates the existing beta.20 DOM (including dynamically inserted nodes), and exposes `hrT(messageId)` for new UI work. New features should use message IDs instead of adding hard-coded user-facing strings.

The interface language is resolved in this order: a locally stored HA Reporting preference, the Home Assistant parent document language when it is readable through Ingress, then the browser language. Only `fr` and `en` are currently supported. The default report language is stored independently, and each report persists its own `language` field. Legacy reports without this field use `fr`.

English report generation is deliberately scoped to renderer-owned text. `rendering/html_report.py` translates report headings, quality labels, period descriptions and technical footer labels while preserving device names, entity IDs and measured values. `analysis/ai_report.py` selects French or English AI instructions from the report language and normalizes the expected section headings accordingly.

Native PDF downloads now build `Content-Disposition` with an ASCII-safe `filename=` fallback plus an RFC 5987 `filename*=UTF-8''...` value. This prevents `http.server` from raising `UnicodeEncodeError` on filenames containing characters outside Latin-1.

Timezone discovery no longer depends exclusively on Home Assistant Core `/api/config`. The add-on requests Supervisor information first, validates the returned timezone with `zoneinfo`, caches a successful result for one hour, and falls back to Core configuration and finally `TZ`/UTC. A last-resort fallback is cached for five minutes to prevent log storms while still allowing automatic recovery. The add-on declares `hassio_api: true` with `hassio_role: default`.

From beta.21 onward, newly added or modified maintainer-facing comments, changelog entries, validation files and technical documentation are written in English. Historical documentation is kept unchanged where it documents earlier releases.

---

# Nouveautés beta.20

## Données et rapports

L'onglet **Catalogues** devient **Données** afin de mieux décrire son rôle : choisir les appareils, capteurs et métriques à analyser. Le moteur continue d'utiliser les catalogues comme objets internes.

Les rapports disposent d'un bouton **Dupliquer**. La copie reprend les catalogues, période, comparaisons, analyse IA et paramètres de sortie, mais reçoit un nouvel ID et ne copie ni documents ni automatisations.

## Statistiques de puissance

Pour les périodes détaillées, les sources `power` utilisent l'export brut VictoriaMetrics lorsque celui-ci est disponible. Le pic n'est donc plus dépendant du pas d'affichage de 5 minutes. La moyenne est pondérée par le temps entre les échantillons. Sur les longues périodes en rollup, VictoriaMetrics fournit également une intégrale `integrate()` utilisée pour la moyenne temporelle.

## Thème et PDF

Dans l'Ingress, HA Reporting recopie les propriétés de fond effectivement rendues par Home Assistant afin de mieux s'intégrer aux thèmes tels que Liquid Glass. Un fallback interne reste disponible si le parent n'est pas lisible.

En thème sombre, le PDF natif applique maintenant le fond sombre à la page A4 elle-même ; la marge n'apparaît donc plus comme un cadre blanc.

## Exports et notifications

Les destinations d'export sont accessibles depuis **Paramètres**. Les documents conservent leurs actions d'export manuel.

Une automatisation peut maintenant combiner :

- notification persistante Home Assistant ;
- notification via une entité `notify.*` (notamment mobile) ;
- lecture TTS via une entité `tts.*` et un lecteur `media_player.*`.

L'échec d'une notification reste non destructif : le rapport/PDF déjà généré reste valide et le job se termine avec avertissement.

## Analyse IA

Le contexte IA ne transmet plus l'absence de reset comme un fait digne d'être commenté. Le prompt lui demande de ne mentionner reset, reconstruction ou fallback que lorsqu'ils se sont réellement produits et qu'ils affectent l'interprétation.

## Langue

Beta.20 reste en français. La couche de traduction français/anglais est reportée à une version ultérieure.

# HA Reporting — 0.1.0-beta.13

Bêta 0.1.0-beta.13 pour Home Assistant OS, notamment sur Raspberry Pi 4 (aarch64).
Le moteur statistique, les comparaisons N/N-x, la vérification runtime et l'analyse IA restent inchangés. Beta.13 ajoute l'orchestration asynchrone du pipeline complet.

## API d’automatisation beta.13

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

1. Décompresser l'archive. Elle contient un dossier de dépôt `ha-reporting`.
2. Copier son sous-dossier `ha-reporting` (celui qui contient `config.yaml` et
   `Dockerfile`) vers `/addons/ha-reporting` sur Home Assistant OS.
3. Actualiser le magasin des add-ons, puis installer ou reconstruire l'add-on
   local HA Reporting selon le mode d'installation existant.
4. Vérifier la version 0.1.0-beta.13 dans les journaux et relancer les rapports.

Ne pas copier le dossier de dépôt complet à la place du dossier de l'add-on.
Pour une installation issue d'un dépôt Git, mettre à jour les fichiers du même
dépôt plutôt que créer une seconde installation locale avec un stockage distinct.
L'archive contient les sources à construire par Supervisor, pas une image OCI.

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

Each report can define `ai_analysis.timeout_seconds`. The default remains **600 s**. Beta.23 validates values from 60 to 7,200 seconds and exposes practical presets from 5 minutes through 2 hours. The configured value applies to the Home Assistant `ai_task.generate_data` wait guard and to the browser-side monitoring deadline with a small technical margin. The deterministic report calculation remains independent and available before AI finishes.


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
