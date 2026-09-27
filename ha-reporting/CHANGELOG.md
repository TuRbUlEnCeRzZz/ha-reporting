## 0.1.0-beta.14

- Corrige la sérialisation publique des jobs asynchrones : les objets runtime privés (notamment `threading.Thread`) sont retirés avant copie profonde, ce qui évite l'erreur `cannot pickle '_contextvars.Context' object`.
- Conserve l’API d’automatisation asynchrone introduite dans la beta.13 et son pipeline complet calcul → IA → PDF → exports.
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
