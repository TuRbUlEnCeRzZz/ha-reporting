/* HA Reporting i18n foundation (beta.22).
 *
 * The legacy beta.20 UI still contains French source strings in a number of
 * rendering functions.  beta.21 centralizes translations here and translates
 * both the static DOM and dynamically inserted UI fragments.  New UI work
 * should use hrT(messageId) directly instead of adding hard-coded strings.
 */
const HR_I18N_MESSAGES = {
  "nav.data": {fr:"Données", en:"Data"},
  "nav.reports": {fr:"Rapports", en:"Reports"},
  "nav.documents": {fr:"Documents", en:"Documents"},
  "nav.automations": {fr:"Automatisations", en:"Automations"},
  "nav.settings": {fr:"Paramètres", en:"Settings"},
  "nav.main": {fr:"Navigation principale", en:"Main navigation"},
  "common.back": {fr:"Retour", en:"Back"},
  "common.refresh": {fr:"Actualiser", en:"Refresh"},
  "common.close": {fr:"Fermer", en:"Close"},
  "common.cancel": {fr:"Annuler", en:"Cancel"},
  "common.save": {fr:"Enregistrer", en:"Save"},
  "common.edit": {fr:"Modifier", en:"Edit"},
  "common.delete": {fr:"Supprimer", en:"Delete"},
  "common.none": {fr:"Aucune", en:"None"},
  "common.disabled": {fr:"Désactivée", en:"Disabled"},
  "common.not_configured": {fr:"Non configuré", en:"Not configured"},
  "common.pending": {fr:"En attente", en:"Pending"},
  "common.name": {fr:"Nom", en:"Name"},
  "common.report": {fr:"Rapport", en:"Report"},
  "common.catalog": {fr:"Catalogue", en:"Catalog"},
  "common.device": {fr:"Appareil", en:"Device"},
  "common.sensor": {fr:"Capteur", en:"Sensor"},
  "common.period": {fr:"Période", en:"Period"},
  "common.start": {fr:"Début", en:"Start"},
  "common.end": {fr:"Fin", en:"End"},
  "common.type": {fr:"Type", en:"Type"},
  "common.state": {fr:"État", en:"State"},
  "common.unit": {fr:"Unité", en:"Unit"},
  "common.metric": {fr:"Métrique", en:"Metric"},
  "common.include": {fr:"Inclure", en:"Include"},
  "common.provider": {fr:"Provider", en:"Provider"},
  "common.copy_word": {fr:"copie", en:"copy"},
  "common.report_filename": {fr:"rapport", en:"report"},

  "data.title": {fr:"Données à analyser", en:"Data to analyze"},
  "data.help": {fr:"Regroupe les appareils, capteurs et métriques à analyser dans des catalogues réutilisables.", en:"Group devices, sensors and metrics to analyze into reusable catalogs."},
  "catalog.new": {fr:"+ Nouveau catalogue", en:"+ New catalog"},
  "catalog.new_title": {fr:"Nouveau catalogue", en:"New catalog"},
  "catalog.auto_id": {fr:"ID automatique", en:"Automatic ID"},
  "catalog.stable_id": {fr:"ID stable", en:"Stable ID"},
  "catalog.id_help": {fr:"Un ID existant n’est jamais écrasé ni renommé automatiquement.", en:"An existing ID is never overwritten or renamed automatically."},
  "catalog.create_device": {fr:"Créer et ajouter un appareil", en:"Create and add a device"},

  "reports.help": {fr:"Définis la présentation, la période, les comparaisons, l’analyse IA et la sortie PDF de chaque rapport.", en:"Define the layout, period, comparisons, AI analysis and PDF output for each report."},
  "report.new": {fr:"+ Nouveau rapport", en:"+ New report"},
  "report.new_title": {fr:"Nouveau rapport", en:"New report"},
  "report.scope_help": {fr:"Définis le périmètre, la période et les comparaisons N / N-x du rapport.", en:"Define the report scope, period and N / N-x comparisons."},
  "report.catalogs": {fr:"Catalogues", en:"Catalogs"},
  "report.position": {fr:"Position", en:"Position"},
  "report.current_period": {fr:"Période en cours", en:"Current period"},
  "report.previous_period": {fr:"Période précédente complète", en:"Previous complete period"},
  "report.day_start": {fr:"Début de la journée", en:"Day start"},
  "report.day_start_help": {fr:"Heure locale Home Assistant. Par défaut : 00:00.", en:"Home Assistant local time. Default: 00:00."},
  "report.comparisons": {fr:"Comparaisons", en:"Comparisons"},
  "report.comparisons_help": {fr:"Les unités sont explicites : N-1 période n'est pas la même chose que N-1 an.", en:"Units are explicit: N-1 period is not the same as N-1 year."},
  "report.previous_periods": {fr:"Périodes précédentes (N-x)", en:"Previous periods (N-x)"},
  "report.previous_years": {fr:"Même période des années précédentes", en:"Same period in previous years"},
  "report.n1_period": {fr:"N-1 période", en:"N-1 period"},
  "report.n1_n2_periods": {fr:"N-1 à N-2 périodes", en:"N-1 to N-2 periods"},
  "report.n1_n3_periods": {fr:"N-1 à N-3 périodes", en:"N-1 to N-3 periods"},
  "report.n1_year": {fr:"N-1 an", en:"N-1 year"},
  "report.n1_n2_years": {fr:"N-1 à N-2 ans", en:"N-1 to N-2 years"},
  "report.n1_n3_years": {fr:"N-1 à N-3 ans", en:"N-1 to N-3 years"},
  "report.ai": {fr:"Analyse IA", en:"AI analysis"},
  "report.ai_help": {fr:"L'IA reçoit uniquement les statistiques déjà calculées par HA Reporting. Pour un fonctionnement no-thinking avec Ollama, sélectionne une entité AI Task dont l'option « Think before responding » est désactivée.", en:"AI receives only statistics already calculated by HA Reporting. For no-thinking operation with Ollama, select an AI Task entity with “Think before responding” disabled."},
  "report.ai_include": {fr:"Inclure une analyse IA dans le rapport", en:"Include AI analysis in the report"},
  "report.ai_entity": {fr:"Entité AI Task", en:"AI Task entity"},
  "report.ai_preferred": {fr:"Entité AI Task préférée de Home Assistant", en:"Home Assistant preferred AI Task entity"},
  "report.ai_timeout": {fr:"Délai maximal de l'analyse IA", en:"Maximum AI analysis timeout"},
  "report.ai_mode_help": {fr:"Le mode de raisonnement est configuré sur l'entité AI Task ; HA Reporting ne le modifie pas à chaque appel.", en:"Reasoning mode is configured on the AI Task entity; HA Reporting does not change it for each call."},
  "report.ai_context": {fr:"Contexte IA", en:"AI context"},
  "report.ai_context_characters": {fr:"caractères", en:"characters"},
  "report.ai_context_compacted_from": {fr:"normalisé depuis", en:"normalized from"},
  "report.ai_context_sources_omitted": {fr:"sources routinières omises", en:"routine sources omitted"},
  "report.ai_context_no_omission": {fr:"aucune source omise", en:"no source omitted"},
  "report.output": {fr:"Sortie du rapport", en:"Report output"},
  "report.output_help": {fr:"Le PDF natif est toujours généré et conservé localement. Le nom peut utiliser des variables pour préparer de futurs workflows d'export.", en:"The native PDF is always generated and stored locally. The filename can use variables for future export workflows."},
  "report.language": {fr:"Langue du rapport", en:"Report language"},
  "report.filename_template": {fr:"Modèle de nom de fichier", en:"Filename template"},
  "report.duplicate_policy": {fr:"Si le nom existe déjà", en:"If the filename already exists"},
  "report.duplicate_version": {fr:"Créer une nouvelle version (_2, _3…)", en:"Create a new version (_2, _3…)"},
  "report.duplicate_overwrite": {fr:"Remplacer le document local", en:"Replace the local document"},
  "report.duplicate_fail": {fr:"Refuser la génération", en:"Refuse generation"},
  "report.variables": {fr:"Variables :", en:"Variables:"},
  "report.preview_label": {fr:"Aperçu :", en:"Preview:"},
  "report.save": {fr:"Enregistrer le rapport", en:"Save report"},
  "report.preview": {fr:"Aperçu du rapport", en:"Report preview"},
  "report.refresh_period": {fr:"Actualiser la période", en:"Refresh period"},
  "report.html": {fr:"Rapport HTML", en:"HTML report"},
  "report.pdf": {fr:"Générer PDF natif", en:"Generate native PDF"},
  "report.execute": {fr:"Exécuter le rapport", en:"Run report"},

  "period.day": {fr:"Jour", en:"Day"},
  "period.week": {fr:"Semaine", en:"Week"},
  "period.month": {fr:"Mois", en:"Month"},
  "period.quarter": {fr:"Trimestre", en:"Quarter"},
  "period.semester": {fr:"Semestre", en:"Half-year"},
  "period.year": {fr:"Année", en:"Year"},
  "period.custom": {fr:"Personnalisée", en:"Custom"},
  "period.hour1": {fr:"1 heure", en:"1 hour"},
  "period.hour6": {fr:"6 heures", en:"6 hours"},
  "period.hour24": {fr:"24 heures", en:"24 hours"},
  "period.day7": {fr:"7 jours", en:"7 days"},

  "automations.help": {fr:"Planifie la création des rapports, l’analyse IA, le PDF, les exports et les notifications Home Assistant.", en:"Schedule report creation, AI analysis, PDF generation, exports and Home Assistant notifications."},
  "automation.new": {fr:"+ Nouvelle automatisation", en:"+ New automation"},
  "automation.new_title": {fr:"Nouvelle automatisation", en:"New automation"},
  "automation.monitor_connecting": {fr:"Connexion au suivi…", en:"Connecting to status monitoring…"},
  "automation.history": {fr:"Historique", en:"History"},
  "automation.history_help": {fr:"Les 50 dernières exécutions sont conservées localement.", en:"The latest 50 runs are stored locally."},
  "automation.enabled": {fr:"Automatisation activée", en:"Automation enabled"},
  "automation.schedule": {fr:"Planification", en:"Schedule"},
  "automation.frequency": {fr:"Fréquence", en:"Frequency"},
  "automation.hourly": {fr:"Toutes les heures", en:"Hourly"},
  "automation.daily": {fr:"Tous les jours", en:"Daily"},
  "automation.weekly": {fr:"Toutes les semaines", en:"Weekly"},
  "automation.monthly": {fr:"Tous les mois", en:"Monthly"},
  "automation.yearly": {fr:"Tous les ans", en:"Yearly"},
  "automation.time": {fr:"Heure (24 h)", en:"Time (24 h)"},
  "automation.minute": {fr:"Minute de l'heure", en:"Minute of the hour"},
  "automation.weekday": {fr:"Jour de la semaine", en:"Day of week"},
  "automation.day_month": {fr:"Jour du mois", en:"Day of month"},
  "automation.pipeline": {fr:"Pipeline", en:"Pipeline"},
  "automation.ai_inherit": {fr:"Suivre la configuration du rapport", en:"Use report configuration"},
  "automation.ai_force_on": {fr:"Forcer activée", en:"Force enabled"},
  "automation.ai_force_off": {fr:"Forcer désactivée", en:"Force disabled"},
  "automation.pdf_theme": {fr:"Thème PDF", en:"PDF theme"},
  "automation.dark": {fr:"Sombre", en:"Dark"},
  "automation.light": {fr:"Clair", en:"Light"},
  "automation.generate_pdf": {fr:"Générer le PDF natif", en:"Generate native PDF"},
  "automation.exports": {fr:"Exports", en:"Exports"},
  "automation.paperless": {fr:"Exporter vers Paperless-ngx", en:"Export to Paperless-ngx"},
  "automation.notifications": {fr:"Notifications", en:"Notifications"},
  "automation.persistent": {fr:"Notification persistante Home Assistant", en:"Home Assistant persistent notification"},
  "automation.device_notify": {fr:"Notification appareil / smartphone", en:"Device / smartphone notification"},
  "automation.notify_help": {fr:", par exemple une notification mobile.", en:", for example a mobile notification."},
  "automation.tts": {fr:"Synthèse vocale (TTS)", en:"Text-to-speech (TTS)"},
  "automation.tts_player": {fr:"Lecteur TTS", en:"TTS media player"},
  "automation.no_player": {fr:"Aucun lecteur", en:"No player"},
  "automation.pipeline_help": {fr:"Les heures sont saisies au format 24 h et utilisent le fuseau Home Assistant. L'export Paperless nécessite la génération du PDF. Les notifications réutilisent le texte de l'analyse IA lorsqu'elle est disponible.", en:"Times use the 24-hour format and the Home Assistant timezone. Paperless export requires PDF generation. Notifications reuse the AI analysis text when available."},
  "automation.reliability": {fr:"Fiabilité", en:"Reliability"},
  "automation.retry": {fr:"Réessayer après un échec global", en:"Retry after a global failure"},
  "automation.retry_count": {fr:"Nombre de nouvelles tentatives", en:"Number of retries"},
  "automation.retry_delay": {fr:"Délai avant nouvelle tentative", en:"Delay before retry"},
  "automation.retry_help": {fr:"Le retry s'applique uniquement aux échecs du pipeline. Un rapport terminé avec avertissements n'est pas relancé afin d'éviter les doublons d'export.", en:"Retries apply only to pipeline failures. A report completed with warnings is not rerun, avoiding duplicate exports."},

  "weekday.mon": {fr:"Lundi", en:"Monday"},
  "weekday.tue": {fr:"Mardi", en:"Tuesday"},
  "weekday.wed": {fr:"Mercredi", en:"Wednesday"},
  "weekday.thu": {fr:"Jeudi", en:"Thursday"},
  "weekday.fri": {fr:"Vendredi", en:"Friday"},
  "weekday.sat": {fr:"Samedi", en:"Saturday"},
  "weekday.sun": {fr:"Dimanche", en:"Sunday"},
  "month.jan": {fr:"Janvier", en:"January"},
  "month.feb": {fr:"Février", en:"February"},
  "month.mar": {fr:"Mars", en:"March"},
  "month.apr": {fr:"Avril", en:"April"},
  "month.may": {fr:"Mai", en:"May"},
  "month.jun": {fr:"Juin", en:"June"},
  "month.jul": {fr:"Juillet", en:"July"},
  "month.aug": {fr:"Août", en:"August"},
  "month.sep": {fr:"Septembre", en:"September"},
  "month.oct": {fr:"Octobre", en:"October"},
  "month.nov": {fr:"Novembre", en:"November"},
  "month.dec": {fr:"Décembre", en:"December"},

  "documents.help": {fr:"PDF natifs générés et conservés localement par HA Reporting.", en:"Native PDFs generated and stored locally by HA Reporting."},
  "exports.title": {fr:"Destinations d’export", en:"Export destinations"},
  "exports.help": {fr:"Le PDF reste toujours stocké localement. Une destination externe reçoit uniquement une copie à la demande.", en:"The PDF always remains stored locally. An external destination receives only a copy on request."},
  "paperless.help": {fr:"Le mode recommandé dépose une copie du PDF dans le dossier", en:"The recommended mode places a copy of the PDF in the Paperless-ngx"},
  "paperless.help_tail": {fr:"de Paperless-ngx, sans token ni appel API. Le mode API reste disponible en option.", en:"folder, without a token or API call. API mode remains available as an option."},
  "paperless.mode": {fr:"Mode d’export", en:"Export mode"},
  "paperless.consume_recommended": {fr:"Dossier consume — recommandé", en:"consume folder — recommended"},
  "paperless.api": {fr:"API REST Paperless-ngx", en:"Paperless-ngx REST API"},
  "paperless.consume": {fr:"Dossier consume", en:"consume folder"},
  "paperless.url": {fr:"URL Paperless-ngx", en:"Paperless-ngx URL"},
  "paperless.token": {fr:"Token API", en:"API token"},
  "paperless.filename": {fr:"Modèle de nom envoyé à Paperless (optionnel)", en:"Filename template sent to Paperless (optional)"},
  "paperless.test": {fr:"Tester la destination", en:"Test destination"},

  "device.analysis": {fr:"Analyse de l'appareil", en:"Device analysis"},
  "device.analyze": {fr:"Analyser l'appareil", en:"Analyze device"},
  "device.add": {fr:"Ajouter un appareil", en:"Add device"},
  "device.add_help": {fr:"Ajoute les sources de données de l'appareil.", en:"Add the device data sources."},
  "device.category": {fr:"Catégorie", en:"Category"},
  "device.entities": {fr:"Entités Home Assistant", en:"Home Assistant entities"},
  "device.entities_help": {fr:"Sélectionne les sources que HA Reporting pourra exploiter.", en:"Select the sources HA Reporting can use."},
  "device.autodetect": {fr:"Détection auto", en:"Auto-detect"},
  "device.sensors_only": {fr:"Capteurs uniquement", en:"Sensors only"},
  "device.selected_only": {fr:"Sélectionnées uniquement", en:"Selected only"},
  "device.add_button": {fr:"Ajouter l'appareil", en:"Add device"},
  "device.create_category": {fr:"Créer une catégorie", en:"Create a category"},

  "settings.global": {fr:"Configuration globale de HA Reporting.", en:"Global HA Reporting configuration."},
  "settings.languages": {fr:"Langues", en:"Languages"},
  "settings.languages_help": {fr:"Choisis la langue de l'interface et la langue proposée par défaut pour les nouveaux rapports.", en:"Choose the interface language and the default language proposed for new reports."},
  "settings.ui_language": {fr:"Langue de l'interface", en:"Interface language"},
  "settings.report_language": {fr:"Langue par défaut des rapports", en:"Default report language"},
  "settings.language_detect": {fr:"La langue de l'interface est détectée depuis Home Assistant au premier lancement puis mémorisée localement. Chaque rapport peut utiliser sa propre langue.", en:"The interface language is detected from Home Assistant on first launch and then stored locally. Each report can use its own language."},
  "settings.exports_help": {fr:"Configure les destinations externes utilisées par les documents et les automatisations.", en:"Configure external destinations used by documents and automations."},
  "settings.exports_configure": {fr:"Configurer les destinations", en:"Configure destinations"},
  "settings.data_sources": {fr:"Sources de données", en:"Data sources"},
  "settings.providers_help": {fr:"Les providers fournissent les séries temporelles au moteur de reporting. Les catalogues restent indépendants de leur implémentation.", en:"Providers supply time series to the reporting engine. Catalogs remain independent from their implementation."},
  "settings.vm_first": {fr:"Premier provider implémenté dans HA Reporting.", en:"First provider implemented in HA Reporting."},
  "settings.vm_test": {fr:"Tester la connexion", en:"Test connection"},
  "settings.source_test": {fr:"Test d'une source réelle", en:"Test a real source"},
  "settings.source_test_help": {fr:"Sélectionne un capteur déjà présent dans un catalogue. HA Reporting interrogera VictoriaMetrics via DataProvider et retournera une série normalisée.", en:"Select a sensor already present in a catalog. HA Reporting will query VictoriaMetrics through DataProvider and return a normalized series."},
  "settings.query_vm": {fr:"Interroger VictoriaMetrics", en:"Query VictoriaMetrics"},
  "settings.use_entity": {fr:"Utilise une entité", en:"Use an entity"},
  "settings.provider_interface": {fr:"Interface DataProvider", en:"DataProvider interface"},
  "settings.entity": {fr:"Entité", en:"Entity"},
  "paperless.path_prefix": {fr:"Le chemin doit se trouver sous", en:"The path must be located under"},
  "paperless.path_help": {fr:"Sur Home Assistant OS, monte idéalement le partage réseau du dossier consume avec l’usage « Share », puis indique ici le chemin obtenu, par exemple", en:"On Home Assistant OS, preferably mount the network share containing the consume folder with the “Share” usage, then enter the resulting path here, for example"},
  "paperless.variables_help": {fr:"Même variables que les noms locaux : {report_id}, {report_name}, {year}, {month}, {period_start}, {period_end}, etc. Le nom déposé peut ainsi déclencher des workflows Paperless.", en:"Same variables as local filenames: {report_id}, {report_name}, {year}, {month}, {period_start}, {period_end}, etc. The deposited filename can therefore trigger Paperless workflows."},
  "paperless.keep_token": {fr:"Laisser vide pour conserver le token enregistré", en:"Leave blank to keep the saved token"},
  "paperless.keep_pdf_name": {fr:"Vide = reprendre le nom du PDF local", en:"Blank = reuse the local PDF filename"},
  "example.monthly_appliance_report": {fr:"Rapport électroménager mensuel", en:"Monthly appliance report"},
  "example.appliances": {fr:"Électroménager", en:"Appliances"},
  "example.wine_cabinet": {fr:"Vinothèque", en:"Wine cabinet"},
  "example.search_wine_cabinet": {fr:"Rechercher : vinotheque…", en:"Search: wine_cabinet…"},
  "paperless.path_help_fragment": {fr:". Sur Home Assistant OS, monte idéalement le partage réseau du dossier consume avec l’usage « Share », puis indique ici le chemin obtenu, par exemple", en:". On Home Assistant OS, preferably mount the network share containing the consume folder with the “Share” usage, then enter the resulting path here, for example"},
  "example.monthly_automatic_report": {fr:"Rapport mensuel automatique", en:"Automatic monthly report"},
  "common.error": {fr:"Erreur", en:"Error"},
  "common.errors": {fr:"Erreurs", en:"Errors"},
  "common.fallbacks": {fr:"Fallbacks", en:"Fallbacks"},
  "common.analyze": {fr:"Analyser", en:"Analyze"},
  "common.add_device_short": {fr:"+ Appareil", en:"+ Device"},
  "common.loading": {fr:"Chargement…", en:"Loading…"},
  "common.no_history": {fr:"Pas d'historique", en:"No history"},
  "common.no_pdf": {fr:"Aucun PDF", en:"No PDF"},
  "common.never_run": {fr:"Jamais exécutée", en:"Never run"},
  "common.unavailable": {fr:"Indisponible", en:"Unavailable"},
  "common.not_available": {fr:"Non disponible", en:"Unavailable"},
  "common.incoherent": {fr:"Incohérent", en:"Inconsistent"},
  "report.not_found": {fr:"Rapport introuvable", en:"Report not found"},
  "report.duplicate_prompt": {fr:"Nom du rapport dupliqué :", en:"Duplicated report name:"},
  "report.period_resolution": {fr:"Résolution de la période et du périmètre. Le rapport peut ensuite être exécuté sur les données réelles.", en:"Resolving the period and scope. The report can then be run on real data."},
  "report.no_history_period": {fr:"Pas d'historique disponible sur cette période.", en:"No history is available for this period."},
  "report.ai_preferred_short": {fr:"entité AI Task préférée", en:"preferred AI Task entity"},
  "report.ai_reference_help": {fr:"Interprétation automatique des statistiques. Les données, graphiques et indicateurs ci-dessous constituent la référence et permettent de vérifier, nuancer ou contester cette analyse.", en:"Automatic interpretation of the statistics. The data, charts and indicators below remain the reference for checking, qualifying or challenging this analysis."},
  "report.ai_continues": {fr:"Le rapport est terminé ; l’interprétation IA continue séparément.", en:"The report is complete; AI interpretation continues separately."},
  "report.ai_local_running": {fr:"Analyse locale en cours… Vous pouvez continuer à utiliser HA Reporting.", en:"Local analysis is running… You can continue using HA Reporting."},
  "report.ai_unavailable": {fr:"Analyse indisponible", en:"Analysis unavailable"},
  "report.ai_task_unavailable": {fr:"AI Task indisponible", en:"AI Task unavailable"},
  "report.ai_status_unavailable": {fr:"État AI Task indisponible", en:"AI Task status unavailable"},
  "report.run_network_warning": {fr:"✓ Rapport exécuté · analyse IA toujours en cours (suivi réseau temporairement indisponible)", en:"✓ Report completed · AI analysis is still running (network monitoring temporarily unavailable)"},
  "report.pdf_generation_failed": {fr:"Génération PDF impossible", en:"PDF generation failed"},
  "documents.destinations_failed": {fr:"Lecture des destinations impossible", en:"Unable to read export destinations"},
  "documents.destination_unreachable": {fr:"Destination inaccessible", en:"Destination unreachable"},
  "common.save_failed": {fr:"Enregistrement impossible", en:"Unable to save"},
  "paperless.test_consume": {fr:"Tester le dossier consume", en:"Test consume folder"},
  "paperless.test_api": {fr:"Tester l’API", en:"Test API"},
  "automation.queued": {fr:"En file", en:"Queued"},
  "automation.calculating": {fr:"Calcul du rapport", en:"Calculating report"},
  "automation.data_complete": {fr:"Données calculées", en:"Data calculated"},
  "automation.exporting": {fr:"Export", en:"Export"},
  "automation.completed": {fr:"Terminé", en:"Completed"},
  "automation.completed_warnings": {fr:"Terminé avec avertissements", en:"Completed with warnings"},
  "automation.failed": {fr:"Échec", en:"Failed"},
  "automation.interrupted": {fr:"Interrompu", en:"Interrupted"},
  "automation.no_report": {fr:"Aucun rapport", en:"No report"},
  "automation.saved": {fr:"✓ Automatisation enregistrée", en:"✓ Automation saved"},
  "automation.history_unavailable": {fr:"Historique indisponible", en:"History unavailable"},
  "automation.run_started": {fr:"Rapport lancé", en:"Report started"},
  "automation.reconnect": {fr:"Rapport lancé — reconnexion au suivi…", en:"Report started — reconnecting to monitoring…"},
  "automation.connection_interrupted": {fr:"Connexion interrompue — nouvelle tentative automatique…", en:"Connection interrupted — retrying automatically…"},
  "automation.confirmation_unavailable": {fr:"Confirmation indisponible. Le rapport a peut-être démarré ; vérifie son état avant de réessayer.", en:"Confirmation unavailable. The report may have started; check its status before trying again."},
  "device.select_sources": {fr:"Sélectionne les sources à associer au nouvel appareil.", en:"Select the sources to associate with the new device."},
  "device.sensors_saved": {fr:"✓ Capteurs enregistrés", en:"✓ Sensors saved"},
  "device.added": {fr:"✓ Appareil ajouté", en:"✓ Device added"},
  "device.not_found_context": {fr:"Catalogue ou appareil introuvable", en:"Catalog or device not found"},
  "catalog.not_found": {fr:"Catalogue introuvable", en:"Catalog not found"},
  "device.not_found": {fr:"Appareil introuvable", en:"Device not found"},
  "catalog.none": {fr:"Aucun catalogue.", en:"No catalog."},
  "catalog.empty": {fr:"Aucun appareil dans ce catalogue.", en:"No device in this catalog."},
  "catalog.rename": {fr:"Modifier le catalogue", en:"Edit catalog"},
  "catalog.new_category_prompt": {fr:"Nom de la nouvelle catégorie :", en:"New category name:"},
  "vm.connected": {fr:"✓ Connexion VictoriaMetrics réussie", en:"✓ VictoriaMetrics connection successful"},
  "analysis.running": {fr:"Analyse en cours…", en:"Analysis in progress…"},
  "analysis.data_quality_note": {fr:"La densité d'échantillonnage est un indicateur diagnostique : une densité faible peut provenir", en:"Sample density is a diagnostic indicator: low density can result from"},
  "category.refrigeration": {fr:"Réfrigération", en:"Refrigeration"},
  "category.appliance": {fr:"Électroménager", en:"Appliances"},
  "category.climate": {fr:"Climat", en:"Climate"},
  "category.computer": {fr:"Informatique", en:"Computing"},
  "category.lighting": {fr:"Éclairage", en:"Lighting"},
  "category.energy": {fr:"Énergie", en:"Energy"},
  "category.water": {fr:"Eau", en:"Water"},
  "category.ventilation": {fr:"Ventilation", en:"Ventilation"},
  "category.multimedia": {fr:"Multimédia", en:"Multimedia"},
  "category.other": {fr:"Autre", en:"Other"},
  "data.normalized_json": {fr:"Voir le JSON normalisé", en:"View normalized JSON"},
  "data.normalized_received": {fr:"✓ Série normalisée reçue", en:"✓ Normalized series received"},
  "report.plan_json": {fr:"Voir le JSON du plan de rapport", en:"View report plan JSON"},
  "comparison.comparable": {fr:"Comparables", en:"Comparable"},
  "comparison.partial": {fr:"Partielles", en:"Partial"},
  "comparison.reconstructed": {fr:"Reconstruites", en:"Reconstructed"},
  "comparison.unavailable": {fr:"Indisponibles", en:"Unavailable"},
  "analysis.invalid": {fr:"Invalides", en:"Invalid"},
  "analysis.unsupported": {fr:"Non supportées", en:"Unsupported"},
  "metric.period_consumption": {fr:"Consommation période", en:"Period consumption"},
  "metric.counter_start": {fr:"Début compteur", en:"Counter start"},
  "metric.counter_end": {fr:"Fin compteur", en:"Counter end"},
  "metric.runtime_rate": {fr:"Taux fonctionnement", en:"Runtime rate"},
  "metric.ignored_anomalies": {fr:"Anomalies ignorées", en:"Ignored anomalies"},
  "metric.result": {fr:"Résultat", en:"Result"},
  "device.full_json": {fr:"Voir le JSON complet de l'appareil", en:"View complete device JSON"},
  "device.density_note": {fr:"La densité d'échantillonnage est un indicateur diagnostique : une densité faible peut provenir de redémarrages Home Assistant, d'interruptions, ou simplement d'une source enregistrée de manière clairsemée.", en:"Sample density is a diagnostic indicator: low density may result from Home Assistant restarts, interruptions, or simply from a sparsely recorded source."},
  "tooltip.edit_sensors": {fr:"Ajouter, retirer ou modifier les capteurs de l’appareil", en:"Add, remove or edit the device sensors"},
  "tooltip.edit_device": {fr:"Modifier le nom et la catégorie de l’appareil", en:"Edit the device name and category"},
  "tooltip.edit_catalog": {fr:"Modifier le nom du catalogue", en:"Edit the catalog name"}
};

const HR_I18N_LOOKUP = {fr:new Map(), en:new Map()};
for(const [key, message] of Object.entries(HR_I18N_MESSAGES)){
  if(message.fr) HR_I18N_LOOKUP.fr.set(message.fr, key);
  if(message.en) HR_I18N_LOOKUP.en.set(message.en, key);
}

function hrNormalizeLanguage(value){
  const language=String(value||"").toLowerCase().replace("_","-");
  return language.startsWith("fr") ? "fr" : "en";
}

function hrDetectLanguage(){
  const stored=localStorage.getItem("ha_reporting_language");
  if(stored === "fr" || stored === "en") return stored;
  try{
    const parentLang=window.parent?.document?.documentElement?.lang;
    if(parentLang) return hrNormalizeLanguage(parentLang);
  }catch(_){ /* Ingress parent may not be directly readable. */ }
  return hrNormalizeLanguage(navigator.language || "fr");
}

let HR_CURRENT_LANGUAGE=hrDetectLanguage();

function hrT(key, variables={}){
  const message=HR_I18N_MESSAGES[key];
  let value=message?.[HR_CURRENT_LANGUAGE] ?? message?.en ?? key;
  for(const [name,replacement] of Object.entries(variables||{})){
    value=value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

function hrCurrentLanguage(){ return HR_CURRENT_LANGUAGE; }
function hrDefaultReportLanguage(){
  const stored=localStorage.getItem("ha_reporting_default_report_language");
  return stored === "en" || stored === "fr" ? stored : HR_CURRENT_LANGUAGE;
}

function hrTranslateExact(text){
  const raw=String(text ?? "");
  const leading=raw.match(/^\s*/)?.[0] || "";
  const trailing=raw.match(/\s*$/)?.[0] || "";
  const core=raw.trim();
  if(!core) return raw;
  for(const sourceLanguage of ["fr","en"]){
    const key=HR_I18N_LOOKUP[sourceLanguage].get(core);
    if(key) return leading + (HR_I18N_MESSAGES[key][HR_CURRENT_LANGUAGE] || core) + trailing;
  }
  return raw;
}

function hrTranslateDynamic(text){
  if(HR_CURRENT_LANGUAGE !== "en") return text;
  let value=String(text ?? "");
  const replacements=[
    [/^Erreur\s*:\s*/i,"Error: "],
    [/^Aperçu\s*·\s*/,"Preview · "],
    [/^Modifier\s*·\s*/,"Edit · "],
    [/^Analyse\s*·\s*/,"Analysis · "],
    [/^Historique\s*[—-]\s*/,"History — "],
    [/^Fuseau utilisé\s*:\s*/,"Timezone used: "],
    [/^Prochaine exécution$/,"Next run"],
    [/^Dernière exécution$/,"Last run"],
    [/^Durée$/,"Duration"],
    [/^Déclenchement$/,"Trigger"],
    [/^Étapes prévues$/,"Planned steps"],
    [/^Fiabilité$/,"Reliability"],
    [/^Activée$/,"Enabled"],
    [/^Désactivée$/,"Disabled"],
    [/^Exécution en cours…$/,"Run in progress…"],
    [/^Exécuter maintenant$/,"Run now"],
    [/^Chargement…$/,"Loading…"],
    [/^Aucune exécution enregistrée\.$/,"No recorded runs."],
    [/^Aucun rapport défini\.$/,"No report defined."],
    [/^Aucun PDF natif généré\.$/,"No native PDF generated."],
    [/^Aucune automatisation HA Reporting\.$/,"No HA Reporting automation."],
    [/^Aucun catalogue disponible\.$/,"No catalog available."],
    [/^Aucun catalogue avec appareil$/,"No catalog with devices"],
    [/^Aucun appareil$/,"No device"],
    [/^Aucun capteur$/,"No sensor"],
    [/^Rapport indisponible$/,"Report unavailable"],
    [/^Sans historique$/,"No history"],
    [/^Sans données$/,"No data"],
    [/^Données reçues$/,"Data received"],
    [/^Connecté$/,"Connected"],
    [/^Indisponible$/,"Unavailable"],
    [/^Sélection incomplète$/,"Incomplete selection"],
    [/^Interrogation en cours…$/,"Query in progress…"],
    [/^Résolution en cours…$/,"Resolving…"],
    [/^Exécution du rapport…$/,"Running report…"],
    [/^Génération PDF…$/,"Generating PDF…"],
    [/^PDF généré ✓$/,"PDF generated ✓"],
    [/^Analyse en cours…$/,"Analysis in progress…"],
    [/^Rapport lancé$/,"Report started"],
    [/^Ce rapport est déjà en cours\.$/,"This report is already running."],
    [/^Non supportées$/,"Unsupported"],
    [/^Analysées$/,"Analyzed"],
    [/^Sources OK$/,"Sources OK"],
    [/^Sources$/,"Sources"],
    [/^Variation période$/,"Period change"],
    [/^Couverture période$/,"Period coverage"],
    [/^Densité disponible$/,"Available density"],
    [/^Points reçus \/ période$/,"Received points / period"],
    [/^Trous détectés$/,"Detected gaps"],
    [/^Analyse métier$/,"Domain analysis"],
    [/^Qualité des données$/,"Data quality"],
    [/^Moyenne$/,"Average"],
    [/^Dernier$/,"Last"],
    [/^Minimum$/,"Minimum"],
    [/^Maximum$/,"Maximum"],
    [/^Pic$/,"Peak"],
    [/^Aperçu$/,"Preview"],
    [/^Dupliquer$/,"Duplicate"],
    [/^Capteurs$/,"Sensors"],
    [/^Développer le catalogue$/,"Expand catalog"],
    [/^Réduire le catalogue$/,"Collapse catalog"],
    [/^PDF natif local$/,"Local native PDF"],
    [/^Analyse IA · no-thinking$/,"AI analysis · no-thinking"],
    [/^Personnalisée$/,"Custom"],
    [/^en cours$/,"current"],
    [/^précédent complet$/,"previous complete"],
    [/^précédente complète$/,"previous complete"],
    [/^Rapport « (.+) » dupliqué$/,"Report “$1” duplicated"],
    [/^✓ Rapport modifié$/,"✓ Report updated"],
    [/^✓ Rapport créé$/,"✓ Report created"],
    [/^Supprimer la définition du rapport « (.+) » \?([\s\S]*)$/,"Delete report definition “$1”?$2"],
    [/^Aucun historique Home Assistant\/VictoriaMetrics n'est supprimé\.$/,"No Home Assistant/VictoriaMetrics history is deleted."],
    [/^Délai maximal configuré\s*:\s*(.+)$/,"Configured maximum timeout: $1"],
    [/^✓ Rapport exécuté · /,"✓ Report completed · "],
    [/^Réessayer (.+)$/,"Retry $1"],
    [/^Réexporter vers (.+)$/,"Re-export to $1"],
    [/^Exporter vers (.+)$/,"Export to $1"],
    [/^Supprimer le document local « (.+) » \?$/,"Delete local document “$1”?"],
    [/^Toutes les heures à :(\d{2})$/,"Every hour at :$1"],
    [/^Tous les jours à (.+)$/,"Every day at $1"],
    [/^Le (\d+) de chaque mois à (.+)$/,"On day $1 of each month at $2"],
    [/^Modifier « (.+) »$/,"Edit “$1”"],
    [/^Collecte et statistiques$/,"Collection and statistics"],
    [/^À venir$/,"Pending"],
    [/^En cours$/,"Running"],
    [/^Désactivé$/,"Disabled"],
    [/^À vérifier$/,"Check required"],
    [/^Fuseau utilisé\s*:\s*/,"Timezone used: "],
    [/^Nouvelle tentative désactivée$/,"Retry disabled"],
    [/^Supprimer l'automatisation « (.+) » \?$/,"Delete automation “$1”?"],
    [/^Ajouter un appareil à « (.+) »$/,"Add a device to “$1”"],
    [/^Capteurs · (.+)$/,"Sensors · $1"],
    [/^Analyse · (.+)$/,"Analysis · $1"],
    [/^Modifier l'appareil$/,"Edit device"],
    [/^Supprimer le catalogue « (.+) » \?([\s\S]*)$/,"Delete catalog “$1”?$2"],
    [/^Supprimer l'appareil « (.+) » \?([\s\S]*)$/,"Delete device “$1”?$2"],
    [/^✓ Analyse terminée · /,"✓ Analysis complete · "],
    [/^Non disponible · /,"Unavailable · "],
    [/^Erreur · /,"Error · "],
    [/^couverture —$/,"coverage —"],
    [/^couverture (.+)$/,"coverage $1"],
    [/^densité n\/a$/,"density n/a"],
    [/^densité —$/,"density —"],
    [/^densité (.+)$/,"density $1"],
    [/^Temps période$/,"Period runtime"],
    [/^Cycles période$/,"Period cycles"],
    [/^N couverture /,"N coverage "],
    [/^Réf\. couverture /,"Ref. coverage "],
    [/^Le (\d{2}\.\d{2}) à (.+)$/,"On $1 at $2"],
    [/^Lundi à (.+)$/,"Monday at $1"],
    [/^Mardi à (.+)$/,"Tuesday at $1"],
    [/^Mercredi à (.+)$/,"Wednesday at $1"],
    [/^Jeudi à (.+)$/,"Thursday at $1"],
    [/^Vendredi à (.+)$/,"Friday at $1"],
    [/^Samedi à (.+)$/,"Saturday at $1"],
    [/^Dimanche à (.+)$/,"Sunday at $1"],
    [/^Planification inconnue$/,"Unknown schedule"],
    [/^IA forcée activée$/,"AI forced on"],
    [/^IA forcée désactivée$/,"AI forced off"],
    [/^IA selon le rapport$/,"AI follows report settings"],
    [/^Retirer « (.+) » de ce catalogue \?/,"Remove “$1” from this catalog?"],
    [/Cela supprimera sa configuration HA Reporting et les appareils qu'il contient\./g,"This will delete its HA Reporting configuration and the devices it contains."],
    [/Les historiques Home Assistant et VictoriaMetrics ne seront PAS supprimés\./g,"Home Assistant and VictoriaMetrics histories will NOT be deleted."],
    [/Les historiques ne seront pas supprimés\./g,"Histories will not be deleted."],
    [/Aucun historique Home Assistant\/VictoriaMetrics n'est supprimé\./g,"No Home Assistant/VictoriaMetrics history is deleted."],
    [/indisponible actuellement/g,"currently unavailable"],
    [/appareil\(s\)/g,"device(s)"],
    [/source\(s\)/g,"source(s)"],
    [/point\(s\)/g,"point(s)"],
    [/trou\(s\)/g,"gap(s)"],
    [/analysée\(s\)/g,"analyzed"],
    [/fallback\(s\) détaillé\(s\)/g,"detailed fallback(s)"],
    [/correction\(s\) mineure\(s\)/g,"minor correction(s)"],
    [/irrégularité\(s\) locale\(s\) brute\(s\)/g,"raw local irregularity/irregularities"],
    [/baisse\(s\) ignorée\(s\)/g,"ignored decrease(s)"],
    [/nouvelle\(s\) tentative\(s\)/g,"retry/retries"],
    [/historique\(s\)/g,"history item(s)"],
    [/reconstruite ·/g,"reconstructed ·"],
    [/directe ·/g,"direct ·"],
    [/reconstruit ·/g,"reconstructed ·"],
    [/direct ·/g,"direct ·"]
  ];
  for(const [pattern,replacement] of replacements) value=value.replace(pattern,replacement);
  return value;
}

function hrTranslateValue(value){
  const exact=hrTranslateExact(value);
  return exact === value ? hrTranslateDynamic(value) : exact;
}

function hrTranslateElement(element){
  if(!(element instanceof Element)) return;
  if(element.closest("script,style,pre,.seriesPreview")) return;
  for(const attribute of ["placeholder","title","aria-label","data-tooltip"]){
    if(element.hasAttribute(attribute)){
      element.setAttribute(attribute, hrTranslateValue(element.getAttribute(attribute)));
    }
  }
}

function hrTranslateTree(root=document){
  const walker=document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const textNodes=[];
  while(walker.nextNode()) textNodes.push(walker.currentNode);
  for(const node of textNodes){
    if(node.parentElement?.closest("script,style,pre,.seriesPreview")) continue;
    const translated=hrTranslateValue(node.nodeValue);
    if(translated !== node.nodeValue) node.nodeValue=translated;
  }
  if(root instanceof Element) hrTranslateElement(root);
  const elements=(root.querySelectorAll ? root.querySelectorAll("*") : []);
  for(const element of elements) hrTranslateElement(element);
}

function hrBindLanguageSettings(){
  const ui=document.getElementById("uiLanguage");
  if(ui){
    ui.value=HR_CURRENT_LANGUAGE;
    ui.addEventListener("change",()=>{
      const value=hrNormalizeLanguage(ui.value);
      localStorage.setItem("ha_reporting_language",value);
      window.location.reload();
    });
  }
  const report=document.getElementById("defaultReportLanguage");
  if(report){
    report.value=hrDefaultReportLanguage();
    report.addEventListener("change",()=>{
      const value=hrNormalizeLanguage(report.value);
      localStorage.setItem("ha_reporting_default_report_language",value);
    });
  }
}

function hrLocalizeNativeDialogs(){
  if(HR_CURRENT_LANGUAGE === "fr") return;
  const originalAlert=window.alert?.bind(window);
  const originalConfirm=window.confirm?.bind(window);
  const originalPrompt=window.prompt?.bind(window);
  if(originalAlert) window.alert=(message)=>originalAlert(hrTranslateValue(message));
  if(originalConfirm) window.confirm=(message)=>originalConfirm(hrTranslateValue(message));
  if(originalPrompt) window.prompt=(message,defaultValue)=>originalPrompt(hrTranslateValue(message),defaultValue);
}

function hrInitI18n(){
  document.documentElement.lang=HR_CURRENT_LANGUAGE;
  hrTranslateTree(document.body);
  hrBindLanguageSettings();
  hrLocalizeNativeDialogs();
  const observer=new MutationObserver(mutations=>{
    for(const mutation of mutations){
      for(const node of mutation.addedNodes){
        if(node.nodeType === Node.TEXT_NODE){
          const translated=hrTranslateValue(node.nodeValue);
          if(translated !== node.nodeValue) node.nodeValue=translated;
        }else if(node.nodeType === Node.ELEMENT_NODE){
          hrTranslateTree(node);
        }
      }
      if(mutation.type === "characterData"){
        const translated=hrTranslateValue(mutation.target.nodeValue);
        if(translated !== mutation.target.nodeValue) mutation.target.nodeValue=translated;
      }
    }
  });
  observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  window.__haReportingI18nObserver=observer;
}

window.hrT=hrT;
window.hrCurrentLanguage=hrCurrentLanguage;
window.hrDefaultReportLanguage=hrDefaultReportLanguage;
window.hrTranslateValue=hrTranslateValue;
hrInitI18n();
