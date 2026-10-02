## 0.2.0-rc.8

- add collapsible/expandable Automation cards with persisted per-card state and automatic expansion while a job is running;
- add Automation sorting by creation date, name, next run, last start, last finish, duration and status, including ascending/descending order and Collapse all / Expand all controls;
- persist `created_at` for new automations and infer it from the oldest retained history entry for legacy definitions when possible;
- apply the same collapsible/sortable UX pattern to Documents with generation date, name, period start/end, report type and size sorting;
- make Automatic AI context selection more conservative so substantial monthly/annual reports prefer Optimized unless a larger mode is selected explicitly;
- introduce `ha-reporting-ai-context-v14` and `id_only_v5_recommendation_guard`;
- reject `verify_reconstructed_counter` recommendations unless the selected evidence itself proves reconstructed/reset handling;
- keep deterministic calculations, units, comparison eligibility, forecast relationships, numeric prose, VictoriaMetrics maintenance, downloads, exports and scheduler semantics unchanged.

## 0.2.0-rc.7

- add global AI context levels under Settings: Optimized, Extended, Complete and Automatic;
- introduce `ha-reporting-ai-context-v13` and `id_only_v4_context_levels`;
- keep deterministic calculations, units, relationships and numeric rendering unchanged across all context levels;
- expose requested/effective AI context level in report metadata and fall back safely if a larger mode exceeds the application context guard;
- suppress redundant standalone forecast/actual facts when an authoritative relationship is already rendered;
- preserve decimal precision coherently between forecast/actual values and deterministic gaps;
- prioritize total electrical energy in annual summaries when N/N-x has no representative comparison;
- keep RC6 relationship priority, RC5 shortlisting, read-only VictoriaMetrics maintenance, PDF downloads and export/automation behavior unchanged.

## 0.2.0-rc.6

- fix deterministic rendering of `integrated_energy_kwh` so derived forecast energy is always displayed in kWh instead of inheriting the source power unit;
- introduce `ha-reporting-ai-context-v12` and `id_only_v3_relationship_priority`;
- make validated forecast-versus-actual energy and mean-power relationships mandatory summary evidence so complete EMHASS comparisons cannot be omitted by the model;
- keep unsupported forecast relationships attention-only when coverage is insufficient for a full-period gap;
- merge multiple recommendation actions that target the same real source, preserving data-quality and reconstructed-counter guidance in one concise line;
- keep RC5 deterministic shortlisting, quality signals, source deduplication, read-only VictoriaMetrics maintenance and lossless report data unchanged.

## 0.2.0-rc.5

- introduce `ha-reporting-ai-context-v11` with a deterministic model-facing shortlist built from the complete internal fact ledger;
- deduplicate shared sources by Home Assistant entity identity so repeated room sensors do not consume duplicate AI context or inherit appliance labels;
- add mandatory report-wide quality signals for source availability and N/N-x comparison representativeness;
- exclude current-period values below 80% coverage from normal AI summary eligibility;
- exclude limited/reconstructed/unavailable N/N-x facts from normal headline conclusions while retaining their quality evidence;
- surface an explicit deterministic warning when a comparison target has zero representative comparisons;
- shortlist representative/significant facts before AI Task execution while preserving the detailed report and full internal ledger;
- keep routine max/P95/counter-end facts out of the LLM shortlist;
- round coverage values in deterministic AI prose and deduplicate repeated rendered attention/recommendation lines;
- expose full-ledger versus shortlisted fact/source counts in AI metadata;
- keep VictoriaMetrics maintenance read-only and independent from HA Reporting catalogs.

## 0.2.0-rc.4

- introduce `ha-reporting-ai-context-v10` with an **ID-only fact-ledger selection protocol**;
- stop asking AI providers to write quantitative report prose; models now select validated fact/relationship IDs only;
- render all numeric sentences deterministically inside HA Reporting from the selected ledger entries;
- validate selected IDs against section-specific eligibility rules and discard unsupported IDs;
- exclude raw power max/P95 facts from normal headline selection so isolated forecast peak gaps cannot dominate the analysis;
- prevent cumulative `counter_end` readings from being selected as period-consumption summary facts;
- add deterministic fallback selection when an AI provider returns malformed JSON, free-form prose or no valid summary IDs;
- generate recommendation wording from a small allow-list of actions tied to validated evidence IDs;
- keep the complete semantic fact ledger lossless and preserve RC3 VictoriaMetrics maintenance, authenticated downloads, notifications, PDF generation and Paperless behavior unchanged.

## 0.2.0-rc.3

- introduce `ha-reporting-ai-context-v9` with a deterministic atomic fact ledger for AI interpretation;
- normalize source/comparison identity into compact registries while retaining every semantic current and N/N-x statistic;
- require every quantitative AI statement to come from one fact or one explicit deterministic relationship;
- forbid invented devices, cross-fact source pairing, physical-unit changes and unsupported peak-based fault/calibration diagnoses;
- add a read-only **Settings → Maintenance → VictoriaMetrics** inventory;
- compare HA-labelled VictoriaMetrics series with the live Home Assistant entity set without reading HA Reporting catalogs;
- classify VictoriaMetrics entities as active, orphaned, protected or indeterminate using a conservative first cleanup policy;
- expose no deletion endpoint and perform no automatic VictoriaMetrics cleanup;
- keep authenticated Ingress/Nabu Casa PDF downloads, notifications, report statistics, PDF generation and Paperless workflows unchanged.

## 0.2.0-rc.2

- introduce `ha-reporting-ai-context-v8` with atomic N/N-x comparison records;
- assign a compact `id` to every comparison record and forbid AI providers from mixing fields across different records;
- require mean/min/max/P95/consumption wording to use the matching named statistic only;
- allow relative percentages only when the same statistic explicitly contains `gap_pct`; never reinterpret an absolute gap as a percentage;
- keep coverage scoped to its exact comparison/relationship and forbid coverage transfer between neighbouring sources;
- keep RC1 deterministic relationships, direction metadata, coverage gating, limited-comparison handling and lossless source retention unchanged;
- keep notifications unchanged;
- keep the same-session Ingress/Nabu Casa PDF download implementation unchanged after successful real-device validation.

## 0.2.0-rc.1

- introduce `ha-reporting-ai-context-v7` as the first 0.2.0 release-candidate AI contract;
- add authoritative `trend_direction` metadata to validated full-period N/N-x statistics so AI providers cannot legitimately reverse an increase into a decrease or vice versa;
- restrict current-period cross-source comparisons to deterministic HA Reporting `relationships`;
- when forecast/measured coverage is insufficient for a full-period comparison, preserve both values and coverage but omit absolute/relative performance gaps;
- suppress relative percentages for `limited` comparisons while preserving source values and absolute differences;
- keep beta.26 coverage tiers, sparse-zero safeguards and same-session Ingress/Nabu Casa PDF downloads unchanged;
- preserve all current/comparison sources and partial data without AI-context trimming.

## 0.1.0-beta.26

- add explicit comparison quality tiers: representative (>=95% coverage), partial (80-95%) and limited (<80%);
- add a `limited` comparison status and surface it in report summaries;
- stop treating normal event-driven power density as incomplete-period coverage; only very sparse power histories downgrade reliability;
- detect sparse near-zero power histories and avoid presenting uncertain zero values as confirmed inactivity;
- suppress relative percentages when the reference is too close to zero while retaining the absolute difference and source data;
- introduce `ha-reporting-ai-context-v6` with near-zero and sparse-zero interpretation rules for AI Task providers;
- require >=95% coverage for deterministic forecast/measured relationships to be described as full-period comparisons;
- fix PDF downloads through Home Assistant Ingress/Nabu Casa by using same-session `fetch()` + Blob downloads instead of opening the protected download URL in a new tab;
- keep all comparison sources, partial data, deterministic statistics, beta.25 relationships and existing PDF/Paperless workflows intact.

## 0.1.0-beta.25

- Introduce `ha-reporting-ai-context-v5` with deterministic cross-source `relationships` while preserving every current/comparison source, including partial coverage.
- Precompute forecast-versus-actual period-energy comparisons when one integrated forecast power source and one measured cumulative energy source can be paired unambiguously inside the same report device.
- Expose `forecast_energy_kwh`, `actual_energy_kwh`, `absolute_gap_kwh`, `relative_gap_pct`, both coverage values and a `full_period_comparison_supported` flag to AI Tasks.
- Precompute mean-power forecast-versus-measured gaps and carry P95/max values as secondary context when one forecast and one measured power source can be paired unambiguously.
- Require AI summaries to report the deterministic energy forecast comparison when it is available, instead of omitting `integrated_energy_kwh`.
- Prioritize period-energy forecast accuracy over isolated peak-power differences and qualify relationships whose coverage does not support a full-period comparison.
- Keep arithmetic in HA Reporting so the language model does not need to infer source pairing or recalculate gaps/percentages.
- Keep beta.24 power integration, source semantics and lossless data retention unchanged.
- Add English, paste-ready GitHub release notes and document that every future release must provide them.

## 0.1.0-beta.24

- Add an optional **Statistics + energy integration** processing mode for `power` sources.
- Expose `integrated_energy_kwh` from the same time-weighted power series and exact report window used for power statistics.
- Keep derived power energy generic and provider-agnostic; no EMHASS-specific code path is required.
- Add the `energy_measurement` metric and use Home Assistant `state_class: measurement` to distinguish kWh/Wh gauges from cumulative energy counters during automatic metric detection.
- Expose Home Assistant `state_class` in the source picker.
- Introduce `ha-reporting-ai-context-v4`, replacing positional statistic arrays with self-describing named fields on each source record.
- Distinguish `period_delta` from `counter_end` explicitly in AI input and add prompt rules forbidding cumulative counter readings from being described as period consumption.
- Add explicit AI semantics for forecast sources and for `integrated_energy_kwh`.
- Preserve every current/comparison source, including partial coverage; beta.24 still fails explicitly instead of trimming report data.
- Keep beta.23 long-running AI timeouts and WebSocket heartbeat behavior unchanged.

## 0.1.0-beta.23

- Raise the maximum configurable AI Task timeout from 1,800 seconds to 7,200 seconds (2 hours).
- Keep the 600-second default for backward compatibility and smaller reports.
- Add report-editor timeout presets from 5 minutes through 2 hours, including 90 minutes for slow local inference.
- Display configured AI timeouts in minutes/hours instead of raw seconds while analysis is running.
- Preserve custom persisted timeout values within the supported 60–7,200 second range when editing reports.
- Keep long AI execution in the existing server-side background job with WebSocket heartbeats.
- Return timeout errors in the selected report language with human-readable durations.
- Keep the beta.22 lossless `ha-reporting-ai-context-v3` contract unchanged; beta.23 does not drop report data to reduce AI input.

## 0.1.0-beta.22

- Add the `ha-reporting-ai-context-v3` lossless normalized semantic context for AI Task calls.
- Replace repeated nested metadata with array-index registries and positional rows.
- Preserve every current-period and comparison source, including partial-coverage entries; beta.22 no longer trims routine sources to meet the preferred target.
- Keep calculated values, coverage, applicable density, warnings, comparison status/policy and reconstruction flags in the normalized AI contract.
- Keep the 50,000-character preferred target and 60,000-character hard safety limit; contexts above the hard limit now fail explicitly rather than discarding data.
- Record schema, lossless mode, final/original sizes and current/comparison source counts in AI result metadata.
- Show the no-source-omitted diagnostic in the Ingress report card and generated HTML/PDF reports.
- Keep raw VictoriaMetrics samples and previews excluded from AI input.

## 0.1.0-beta.21

- Add the first HA Reporting internationalization layer with French and English interface support.
- Detect the initial interface language from Home Assistant when available and persist the user's override locally.
- Add separate default-report and per-report language settings so the interface and generated reports can use different languages.
- Translate renderer-owned HTML/PDF labels to English when a report uses `language: en`.
- Generate AI Task instructions and normalized AI section headings in the selected report language.
- Keep backward compatibility with existing report definitions by defaulting missing language values to French.
- Fix native PDF downloads with Unicode filenames by emitting an ASCII fallback plus RFC 5987 UTF-8 `filename*` metadata.
- Prefer the Supervisor information endpoint for Home Assistant OS timezone discovery, cache the resolved timezone, retain the Core configuration endpoint as a fallback, and avoid repeated 502 log storms.
- Add Supervisor API access with the default role, limited to the information needed by HA Reporting.
- Establish English as the language for new maintainer-facing code comments, release notes, validation notes and technical documentation.

## 0.1.0-beta.20

- statistiques de puissance précises : pics calculés sur les échantillons bruts VictoriaMetrics pour les périodes détaillées ;
- puissance moyenne pondérée dans le temps, avec intégrale provider pour les longues périodes ;
- PDF sombre avec fond de page A4 sombre jusqu'aux marges physiques ;
- fond de l'Ingress synchronisé sur le fond réellement rendu par Home Assistant / Liquid Glass quand disponible ;
- onglet « Données » et libellés d'aide clarifiés pour un usage non technique ;
- bouton « Dupliquer » pour les définitions de rapport ;
- destinations d'export déplacées dans « Paramètres » ;
- automatisations : notification persistante, entité `notify.*` et TTS via `tts.*` + `media_player.*` ;
- contexte IA nettoyé des diagnostics de reset/fallback sans intérêt utilisateur.

## 0.1.0-beta.19

- Remplace la navigation principale par cinq onglets persistants : Catalogues, Rapports, Documents, Automatisations et Paramètres.
- N’empile plus les sections principales dans l’historique du navigateur ; le bouton Retour devient contextuel aux écrans de détail.
- Simplifie l’en-tête à `HA Reporting` et au numéro de version.
- Corrige les accords : Jour/Mois/Trimestre/Semestre précédent complet, Semaine/Année précédente complète.
- Remplace les badges techniques `N-1…N-x` par des libellés lisibles.
- Ajoute `period.boundary_time` pour définir le début d’une journée métier (par exemple `05:30`).
- Conserve `00:00` par défaut pour tous les rapports existants.
- Préserve l’heure locale lors des décalages quotidiens et des comparaisons autour des changements DST.

## 0.1.0-beta.13

- Ajoute une API d’automatisation asynchrone pour lancer le pipeline complet d’un rapport sans bloquer la requête HTTP.
- `POST /api/automation/report-jobs` accepte `report_id`, `ai_analysis`, `generate_pdf`, `theme` et `destinations`.
- Ajoute le suivi par `job_id` avec les états `queued`, `running`, `data_complete`, `ai_running`, `pdf_generating`, `exporting`, `completed`, `completed_with_errors` et `error`.
- Expose la liste et le détail des jobs via `GET /api/automation/report-jobs` et `GET /api/automation/report-jobs/{job_id}`.
- Déduplique une demande strictement identique tant qu’un job correspondant est encore actif.
- Permet de forcer l’analyse IA, de la désactiver pour un lancement, ou d’utiliser la configuration du rapport lorsque l’option est omise.
- Le pipeline enregistre toujours le PDF local avant les exports et conserve cet artefact lorsqu’une destination échoue.
- Un échec d’export ou d’analyse IA est signalé en avertissement sans invalider les statistiques ni supprimer le PDF ; un échec structurel du calcul/PDF met le job en `error`.
- Prépare l’API stable qui sera consommée par l’intégration Home Assistant compagnon lors d’une version ultérieure.

## 0.1.0-beta.12

- Ajoute un mode **dossier `consume`** recommandé, sans token ni API, via un chemin monté sous `/share`.
- Monte le partage Home Assistant `/share` en lecture/écriture dans l’add-on pour permettre l’export vers un stockage réseau configuré par Home Assistant OS.
- Teste l’accessibilité en écriture du dossier consume sans créer de fichier que Paperless pourrait ingérer.
- Copie les PDF de façon atomique via un fichier temporaire, puis renommage final ; versionne le nom en cas de collision.
- Le statut d’export distingue le dépôt dans `consume` d’une confirmation d’indexation Paperless.
- Conserve le mode **API REST** de beta.11 comme option avancée.
- Préserve la compatibilité avec une configuration beta.11 existante : URL + token sans champ `mode` reste interprété en mode API.
- Le PDF local reste toujours l’artefact de référence et n’est jamais supprimé après export.

## 0.1.0-beta.11

- Introduit l’abstraction `ExportProvider`, séparée de la génération et du stockage local des PDF.
- Ajoute Paperless-ngx comme première destination d’export via son API REST.
- Ajoute une page **Destinations d’export** avec URL, token API, modèle de nom spécifique et test de connexion.
- Le token Paperless n’est jamais renvoyé à l’interface après enregistrement ; un champ vide conserve le secret existant.
- Ajoute l’export manuel depuis **Documents**, avec nom Paperless spécifique ou fallback sur le nom local.
- Enregistre le statut, les erreurs, le nombre de tentatives et la référence distante dans le manifeste du document.
- Permet de retenter un export échoué ou de réexporter un document déjà envoyé.
- Un échec distant laisse toujours le PDF local intact.
- Aucun export automatique planifié ni politique de rétention automatique dans cette version.

## 0.1.0-beta.10

- Reprend le socle documentaire local introduit en beta.9.
- Pagination PDF native affinée : cartes de comparaison compactées à l'impression et suppression des répétitions sur les sources indisponibles.
- Les identifiants Home Assistant longs se coupent désormais aux séparateurs (`_` / `.`) plutôt qu'au milieu des mots.
- Le rapport annuel de validation tient désormais sur 3 pages au lieu de 4 sans perte d'information.
- Aucun export tiers dans cette version ; `ExportProvider` / Paperless sont reportés à beta.11.

## 0.1.0-beta.9

- PDF natif local via WeasyPrint.
- Stockage persistant des documents sous `/config/documents`.
- Modèles de nom de fichier configurables avec variables dynamiques.
- Gestion des doublons : version, remplacement ou refus.
- Nouvelle page Documents : historique, téléchargement et suppression.
- Aucun export tiers dans cette version.

## 0.1.0-beta.8

- Add explicit AI comparison wording policies: `full_period_change_allowed`, `descriptive_gap_only` and `no_change_claim`.
- For partial, reconstructed or coverage-limited comparisons, forbid assertive full-period increase/decrease language and require descriptive « sur les données disponibles » wording.
- Separate current-period counter reconstruction from reference-period coverage limitations in AI context and prompt guidance.
- Preserve the cautious recommendation style and existing AI summary length.
- Return refreshed execution metadata with AI status polling so the Ingress JSON reflects AI duration and end-to-end pipeline duration after asynchronous completion.
- Keep the editorial order: executive summary, AI interpretation, detailed data, comparisons and technical metadata.
- Preserve the Home Assistant WebSocket transport, heartbeat, configurable timeout and provider/statistics engine unchanged.

## 0.1.0-beta.7

- Hiérarchie éditoriale révisée : l’analyse IA est présentée juste après la synthèse générale, avant les données détaillées et les comparaisons.
- Le texte introductif rappelle explicitement que les chiffres, graphiques et indicateurs restent la référence pour vérifier, nuancer ou contester l’interprétation IA.
- Le PDF ne force plus l’analyse IA sur une nouvelle page ; son titre reste néanmoins lié au début du contenu lors de la pagination.

- Add comparison-quality metadata to the compact AI context, including base/reference coverage and interpretation flags.
- Strengthen the AI prompt so partial, reconstructed or coverage-limited comparisons are not phrased as proven full-period increases/decreases.
- Keep recommendations proportional to confidence; favor monitoring/collecting history when the comparison itself is incomplete.
- Remove contradictory `Aucune recommandation particulière` boilerplate when substantive recommendations are already present.
- Separate statistical, AI and end-to-end pipeline durations in execution metadata.
- Keep the HTML/PDF footer explicit about calculation time vs AI time.
- Place completed AI analysis immediately after the executive summary, before detailed data and comparisons.

## 0.1.0-beta.6

- AI Task transport moved from a long REST call to the Home Assistant WebSocket API via `ws://supervisor/core/websocket`.
- AI analysis now runs as a server-side background job; browser requests return immediately and poll short status endpoints.
- Application-level WebSocket heartbeats keep long local-model generations observable.
- Transient Ingress/browser polling errors no longer mark the AI task itself as failed.
- Conversation ID and transport diagnostics are preserved in the report JSON.

# Changelog

## 0.1.0-beta.5

- Make the AI analysis timeout configurable per report instead of a fixed 180 s limit.
- Default local AI timeout to 600 s (10 minutes), better suited to CPU/RAM constrained Ollama workloads.
- Offer 300, 600, 900 and 1200 s choices in the report editor.
- Validate persisted/API timeout values between 60 and 1800 s for forward compatibility.
- Apply the configured timeout consistently to the Home Assistant AI Task HTTP request, server wall-clock guard and browser request guard.
- Preserve the non-blocking beta.4 execution model: report statistics complete immediately while AI runs separately.
- Expose the configured timeout in report/AI diagnostics and the pending UI state.
- Keep backward compatibility: beta.3/beta.4 reports without `timeout_seconds` transparently use 600 s.

## 0.1.0-beta.4

- Decouple AI Task execution from the deterministic report request so a slow local model can never keep the report stuck on `Exécution en cours`.
- Return and render the statistical report immediately, then launch AI interpretation through a separate endpoint.
- Show a neutral `analyse IA en cours` state while local inference continues.
- Cache the latest executed report in memory so the standalone HTML/PDF view can include the AI result once it completes without re-running the full report.
- Add a 180 s HA Reporting wall-clock guard for AI analysis; timeout or AI failure does not invalidate the statistical report.
- Keep AI work isolated in a daemon worker so the HTTP request serving the report UI is always released.
- Add UI regression coverage for the pending AI state; preserve all beta.3 AI context-minimization and escaping tests.

## 0.1.0-beta.3

- Add optional report-level AI analysis through Home Assistant `ai_task.generate_data`.
- Let each report use the preferred AI Task entity or an explicitly selected `ai_task.*` entity.
- Keep no-thinking control on the AI provider entity; the report UI documents the Ollama `Think before responding` requirement.
- Send only compact validated report statistics, quality metadata and N/N-x comparison values to the model; never send raw VictoriaMetrics samples or previews.
- Ask the model for a concise French synthesis, points of attention and recommendations without exposing reasoning.
- Embed the generated AI analysis in the interactive report preview and standalone HTML/PDF report.
- Fail open: an AI Task error is displayed in the report but does not invalidate the statistical report.
- Record AI duration, selected entity, conversation ID and compact-context size in report JSON diagnostics.
- Add AI Task response-shape, context-minimization, escaping and UI regressions.

## 0.1.0-beta.2

- Preserve the dark standalone HTML visual language when printing or saving as PDF.
- Add exact print color adjustment so report backgrounds and N/reference comparison bars are retained by supporting browsers.
- Stop forcing a white print canvas; use the same dark report palette for screen and print.
- Relax print fragmentation for catalogs and devices while keeping individual source cards together, preventing orphan catalog headings and near-empty pages.
- Keep headings attached to the content that follows and reduce print spacing without flattening cards or comparison graphics.
- Add print-fidelity regressions for dark colors, chart bars, and pagination rules.

## 0.1.0-beta.1

- Freeze the alpha.23 runtime/statistics behavior as the first beta baseline.
- Add a standalone HTML report renderer with no external assets or JavaScript dependencies.
- Add a dedicated `GET /api/report/{id}/html` endpoint that executes the report and returns the rendered document.
- Add a `Rapport HTML / PDF` action in the report preview after a successful execution.
- Add print-specific A4 styling and an `Imprimer / enregistrer en PDF` action.
- Render metric-aware source cards for power, energy, runtime, cycles and temperature.
- Preserve data-quality context, runtime verification and fallback indicators in the rendered report.
- Add N/N-x comparison sections with compact base/reference bar charts and absolute/relative deltas when applicable.
- Keep HTML output self-contained and escape catalog, device and entity text before rendering.
- Add renderer regressions and packaging checks for the new rendering module.

## 0.1.0-alpha.23

- Classify runtime negative transitions as rounding, minor correction, reset candidate or large drop.
- Raw-verify suspicious runtime rollups before deciding whether a fallback is actually required.
- Keep provider rollup and direct delta when raw history proves only benign minor corrections.
- Preserve raw fallback for reset candidates, large drops, invalid data and ambiguous exports.
- Accept at most two benign negative transitions totaling at most 0.02 h (72 s); a return near zero is never accepted as benign.
- Expose `verification` diagnostics and `sources_runtime_verified` separately from fallbacks.
- Keep `execution.raw_series_transferred` accurate when raw verification occurs without fallback.
- Show verified minor runtime corrections in the report UI.
- Add regressions for benign 61 s corrections, tiny return-to-zero resets and real anonymized runtime snapshots.

## 0.1.0-alpha.22

- Preserve original runtime rollup diagnostics and raw negative transitions.
- Replace sampled runtime fallback with bounded, targeted raw JSONL export.
- Retain fallback for actual drops; rounding compatibility is diagnostic only.
- Fail closed on partial, conflicting, ambiguous or excessive raw exports.
- Check runtime plausibility against observed samples, including negative values.
- Enforce millisecond-accurate half-open rollup windows.
- Handle explicit autumn DST folds and reject nonexistent spring local times.
- Apply metric-aware density to detailed analysis as well as rollups.
- Report actual raw fallback transfers and clarify the UI message.
- Make server startup import-safe for repeatable report integration tests.
- Add Python, YAML, JavaScript regressions and anonymized real runtime fixtures.

## 0.1.0-alpha.21

- Validate optimized runtime against the actually observed source window.
- Add targeted detailed fallback for suspicious provider-rollup runtime.
- Limit fallback queries to affected runtime history windows.
- Add transparent `series_fallback` metadata and fallback counts.
- Fix elapsed period duration across DST.
- Preserve custom comparison elapsed duration across DST.
- Make optimized data density metric-aware.
- Display event-driven optimized sources as `density n/a`.
- Retain provider-side density for power.

## 0.1.0-alpha.20

- Scalable long-period provider rollups.
- Long-period quality-aware comparisons.
