let entities = [];
let catalogs = [];
let reports = [];
let documents = [];
let editingReportId = null;
let previewReportId = null;
let categories = [];
let currentCatalog = null;
let editingDeviceId = null;
let existingSensorKeyByEntity = new Map();
let metricOverrideByEntity = new Map();
let analysisCatalogId = null;
let analysisDeviceId = null;
let selected = new Set();
let modalSaveHandler = null;

const metricTypes = [
  "power","energy_total","voltage","current",
  "temperature","humidity","runtime","cycles","state"
];

const $ = id => document.getElementById(id);

function esc(value){
  return String(value ?? "").replace(/[&<>"]/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"
  }[c]));
}

function slug(value){
  return String(value || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g,"")
    .toLowerCase().trim()
    .replace(/[^a-z0-9]+/g,"_")
    .replace(/^_+|_+$/g,"");
}

function syncHomeAssistantTheme(){
  const mappings = {
    "--hr-bg":["--primary-background-color"],
    "--hr-secondary-bg":["--secondary-background-color"],
    "--hr-card":["--card-background-color","--ha-card-background"],
    "--hr-input":["--card-background-color","--primary-background-color"],
    "--hr-text":["--primary-text-color"],
    "--hr-secondary":["--secondary-text-color"],
    "--hr-divider":["--divider-color"],
    "--hr-primary":["--primary-color"],
    "--hr-primary-text":["--text-primary-color"],
    "--hr-error":["--error-color"],
    "--hr-success":["--success-color"],
    "--hr-header-bg":["--app-header-background-color","--card-background-color"],
    "--hr-radius":["--ha-card-border-radius"],
    "--hr-shadow":["--ha-card-box-shadow"],

    "--hr-glass-card-bg":["--liquid-glass-card-bg","--ha-card-background","--card-background-color"],
    "--hr-glass-card-hover":["--liquid-glass-card-bg-hover","--ha-card-background","--card-background-color"],
    "--hr-glass-border":["--liquid-glass-border","--divider-color"],
    "--hr-glass-border-soft":["--liquid-glass-border-soft","--divider-color"],
    "--hr-glass-edge":["--liquid-glass-edge"],
    "--hr-glass-sheen":["--liquid-glass-sheen"],
    "--hr-glass-tint-a":["--liquid-glass-tint-a"],
    "--hr-glass-shadow":["--liquid-glass-shadow","--ha-card-box-shadow"],
    "--hr-glass-shadow-hover":["--liquid-glass-shadow-hover","--ha-card-box-shadow"],
    "--hr-glass-blur":["--liquid-glass-card-blur"],
    "--hr-dialog-bg":["--dialog-background-color","--card-background-color"],
    "--hr-dialog-blur":["--liquid-glass-dialog-blur"]
  };

  try{
    if(!window.parent || window.parent === window) return;

    const doc = window.parent.document;
    const candidates = [
      doc.documentElement,
      doc.body,
      doc.querySelector("home-assistant"),
      doc.querySelector("home-assistant-main"),
      doc.querySelector("ha-drawer"),
      doc.querySelector("ha-panel-lovelace")
    ].filter(Boolean);

    const readVariable = names => {
      for(const element of candidates){
        const style = window.parent.getComputedStyle(element);
        for(const name of names){
          const value = style.getPropertyValue(name).trim();
          if(value) return value;
        }
      }
      return "";
    };

    for(const [localVar, sourceVars] of Object.entries(mappings)){
      const value = readVariable(sourceVars);
      if(value) document.documentElement.style.setProperty(localVar, value);
    }
  }catch(_){
    // If the parent is not directly readable, the generic light/dark fallbacks remain active.
  }
}
async function showProviders(push=true){
  setPage("providersPage", {}, push);
  await loadCatalogs();
  populateSeriesCatalogs();
  await loadProviders();
}

function renderCapabilities(capabilities){
  const names = {
    series:"series",
    first:"first",
    last:"last",
    min:"min",
    max:"max",
    mean:"mean",
    sum:"sum",
    max_timestamp:"max + timestamp",
    state_duration:"state duration",
    state_changes:"state changes",
    report_rollup:"report stats"
  };
  $("vmCapabilities").innerHTML = Object.entries(names).map(([key,label]) =>
    `<span class="capability ${capabilities && capabilities[key] ? "" : "off"}">${esc(label)}</span>`
  ).join("");
}

function renderProviderStatus(status){
  const badge = $("vmBadge");
  badge.className = "providerBadge";

  if(!status || !status.configured){
    badge.textContent = "Non configuré";
    $("vmStatusText").textContent = "";
  }else if(status.available){
    badge.textContent = "Connecté";
    badge.classList.add("ok");
    $("vmStatusText").textContent = "✓ " + status.message;
    $("vmStatusText").classList.remove("error");
  }else{
    badge.textContent = "Indisponible";
    badge.classList.add("error");
    $("vmStatusText").textContent = "Erreur : " + status.message;
    $("vmStatusText").classList.add("error");
  }

  renderCapabilities(status && status.details ? status.details.capabilities : {});
}

function selectedCatalogObject(){
  return catalogs.find(c => c.id === $("seriesCatalog").value);
}

function populateSeriesCatalogs(){
  const usable = catalogs.filter(c => !c.error && (c.devices || []).length);
  $("seriesCatalog").innerHTML = usable.length
    ? usable.map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join("")
    : '<option value="">Aucun catalogue avec appareil</option>';
  populateSeriesDevices();
}

function populateSeriesDevices(){
  const catalog = selectedCatalogObject();
  const devices = catalog ? (catalog.devices || []) : [];
  $("seriesDevice").innerHTML = devices.length
    ? devices.map(d => `<option value="${esc(d.id)}">${esc(d.name)}</option>`).join("")
    : '<option value="">Aucun appareil</option>';
  populateSeriesSensors();
}

function populateSeriesSensors(){
  const catalog = selectedCatalogObject();
  const device = catalog
    ? (catalog.devices || []).find(d => d.id === $("seriesDevice").value)
    : null;
  const sensors = device ? (device.entities || []) : [];

  $("seriesSensor").innerHTML = sensors.length
    ? sensors.map(s =>
        `<option value="${esc(s.key)}">${esc(s.entity_id)} · ${esc(s.metric)}</option>`
      ).join("")
    : '<option value="">Aucun capteur</option>';
}

function formatSeriesNumber(value, unit=""){
  if(value === null || value === undefined) return "—";
  const n = Number(value);
  if(Number.isFinite(n)){
    const abs = Math.abs(n);
    const digits = abs >= 100 ? 1 : abs >= 10 ? 2 : 3;
    return `${n.toFixed(digits)}${unit ? " " + unit : ""}`;
  }
  return `${value}${unit ? " " + unit : ""}`;
}

function localDateTime(timestamp){
  if(timestamp === null || timestamp === undefined) return "—";
  return new Date(Number(timestamp) * 1000).toLocaleString();
}

function renderSeriesResult(result){
  const stats = result.statistics || {};
  const analysis = result.analysis || {};
  const metricStats = analysis.statistics || {};
  const quality = analysis.quality || {};
  const source = result.source || {};
  const unit = source.unit || "";
  const max = metricStats.max || stats.max || {};
  const last = metricStats.last || stats.last || {};

  const hasData = Number(stats.points || 0) > 0;
  $("seriesBadge").textContent = hasData ? "Données reçues" : "Sans historique";
  $("seriesBadge").className = "providerBadge " + (hasData ? "ok" : "");

  let businessStats = "";

  if(["energy_total","runtime","cycles"].includes(source.metric)){
    businessStats = `
      <div class="seriesStat accentStat">
        <div class="label">Variation période</div>
        <div class="value">${formatSeriesNumber(metricStats.delta,unit)}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Reset(s)</div>
        <div class="value">${esc(metricStats.resets_detected ?? 0)}</div>
      </div>`;
  }else if(source.metric === "power"){
    businessStats = `
      <div class="seriesStat accentStat">
        <div class="label">Pic</div>
        <div class="value">${formatSeriesNumber(max.value,unit)}</div>
        <div class="subvalue">${esc(localDateTime(max.timestamp))}</div>
      </div>
      <div class="seriesStat">
        <div class="label">P95</div>
        <div class="value">${formatSeriesNumber(metricStats.p95,unit)}</div>
      </div>`;
  }else{
    businessStats = `
      <div class="seriesStat accentStat">
        <div class="label">Minimum</div>
        <div class="value">${formatSeriesNumber((metricStats.min||{}).value,unit)}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Maximum</div>
        <div class="value">${formatSeriesNumber((metricStats.max||{}).value,unit)}</div>
      </div>`;
  }

  const coverage = quality.period_coverage_percent;
  const density = quality.sample_density_percent;
  const densityClass = density == null ? "" : density >= 95 ? "good" : density >= 80 ? "warn" : "bad";

  $("seriesResult").classList.remove("hidden");
  $("seriesResult").innerHTML = `
    <div class="seriesMeta">
      ${esc(source.entity_id)} · ${esc(source.metric)} · provider ${esc(result.provider)} · pas ${esc(result.period.step)} s
    </div>

    <h4>Analyse métier</h4>
    <div class="seriesSummary businessSummary">
      ${businessStats}
      <div class="seriesStat">
        <div class="label">Moyenne</div>
        <div class="value">${formatSeriesNumber(metricStats.mean ?? stats.mean,unit)}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Dernier</div>
        <div class="value">${formatSeriesNumber(last.value,unit)}</div>
      </div>
    </div>

    <h4>Qualité des données</h4>
    <div class="qualityGrid">
      <div class="seriesStat">
        <div class="label">Couverture période</div>
        <div class="value">${coverage == null ? "—" : Number(coverage).toFixed(1) + " %"}</div>
      </div>
      <div class="seriesStat ${densityClass}">
        <div class="label">Densité disponible</div>
        <div class="value">${density == null ? "—" : Number(density).toFixed(1) + " %"}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Points reçus / période</div>
        <div class="value">${esc(quality.received_points ?? stats.points)} / ${esc(quality.expected_points ?? "—")}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Trous détectés</div>
        <div class="value">${esc(quality.gap_count ?? "—")}</div>
      </div>
    </div>

    <details class="jsonDetails">
      <summary>Voir le JSON normalisé</summary>
      <div class="seriesPreview">${esc(JSON.stringify({
        provider:result.provider,
        source:result.source,
        period:result.period,
        statistics:result.statistics,
        analysis:result.analysis,
        preview:result.preview
      }, null, 2))}</div>
    </details>
  `;
}

async function testCatalogSeries(){
  const catalogId = $("seriesCatalog").value;
  const deviceId = $("seriesDevice").value;
  const sensorKey = $("seriesSensor").value;

  if(!catalogId || !deviceId || !sensorKey){
    $("seriesStatusText").textContent = "Sélection incomplète";
    $("seriesStatusText").classList.add("error");
    return;
  }

  $("seriesStatusText").textContent = "Interrogation en cours…";
  $("seriesStatusText").classList.remove("error");
  $("seriesResult").classList.add("hidden");

  const response = await fetch("api/data/test-series", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      catalog_id:catalogId,
      device_id:deviceId,
      sensor_key:sensorKey,
      hours:Number($("seriesHours").value),
      step:300
    })
  });
  const data = await response.json();

  if(!response.ok){
    $("seriesStatusText").textContent = "Erreur : " + data.error;
    $("seriesStatusText").classList.add("error");
    $("seriesBadge").textContent = "Erreur";
    $("seriesBadge").className = "providerBadge error";
    return;
  }

  $("seriesStatusText").textContent = "✓ Série normalisée reçue";
  $("seriesStatusText").classList.remove("error");
  renderSeriesResult(data.result);
}

async function loadProviders(){
  const response = await fetch("api/providers");
  const data = await response.json();
  const vm = (data.providers || []).find(p => p.id === "victoria_metrics");
  if(!vm) return;
  $("vmUrl").value = vm.url || "";
  renderProviderStatus(vm.status);
}

function periodTypeLabel(type){
  return ({
    day:"Jour",
    week:"Semaine",
    month:"Mois",
    quarter:"Trimestre",
    semester:"Semestre",
    year:"Année",
    custom:"Personnalisée"
  })[type] || type;
}

function periodModeLabel(mode){
  return mode === "previous" ? "précédente complète" : mode === "custom" ? "" : "en cours";
}

async function showReports(push=true){
  setPage("reportsPage", {}, push);
  await loadReports();
}

async function loadReports(){
  const response = await fetch("api/reports");
  const data = await response.json();
  reports = data.reports || [];
  renderReports();
}

function renderReports(){
  if(!reports.length){
    $("reportList").innerHTML = '<div class="card empty">Aucun rapport défini.</div>';
    return;
  }

  $("reportList").innerHTML = reports.map(report => {
    if(report.error){
      return `<div class="reportCard"><div class="error">${esc(report.error)}</div></div>`;
    }

    const period = report.period || {};
    const custom = period.type === "custom"
      ? `${esc(period.start || "")} → ${esc(period.end || "")}`
      : `${periodTypeLabel(period.type)} ${periodModeLabel(period.mode)}`;

    const comparisons = report.comparisons || {};
    const comparisonLabels = [];
    if(Number(comparisons.previous_periods || 0) > 0) comparisonLabels.push(`N-1…N-${comparisons.previous_periods} période(s)`);
    if(Number(comparisons.previous_years || 0) > 0) comparisonLabels.push(`N-1…N-${comparisons.previous_years} an(s)`);

    return `
      <div class="reportCard">
        <div class="reportHeader">
          <div>
            <div class="reportTitle">${esc(report.name)}</div>
            <div class="reportMeta">${esc(report.id)} · ${esc((report.catalog_names || []).join(", "))}</div>
            <span class="reportPeriodPill">${custom}</span>
            ${comparisonLabels.length ? `<span class="reportPeriodPill">${esc(comparisonLabels.join(" · "))}</span>` : ""}
            ${(report.ai_analysis || {}).enabled ? `<span class="reportPeriodPill">Analyse IA · no-thinking</span>` : ""}
            <span class="reportPeriodPill">PDF natif local</span>
          </div>
          <div class="reportActions">
            <button class="primary" onclick="previewReport('${esc(report.id)}')">Aperçu</button>
            <button onclick="showReportForm('${esc(report.id)}')">Modifier</button>
            <button class="danger" onclick="deleteReportDefinition('${esc(report.id)}','${esc(report.name)}')">Supprimer</button>
          </div>
        </div>
      </div>`;
  }).join("");
}

function updateReportPeriodFields(){
  const custom = $("reportPeriodType").value === "custom";
  $("customPeriodFields").classList.toggle("hidden", !custom);
  $("reportPeriodModeLabel").classList.toggle("hidden", custom);
}

function renderReportCatalogChoices(selectedIds=[]){
  const selected = new Set(selectedIds || []);
  $("reportCatalogChoices").innerHTML = catalogs.length
    ? catalogs.filter(c => !c.error).map(c => `
        <label class="choiceItem">
          <input type="checkbox" class="reportCatalogCheck" value="${esc(c.id)}" ${selected.has(c.id) ? "checked" : ""}>
          <span>${esc(c.name)} <span class="muted">(${c.device_count} appareil(s))</span></span>
        </label>`).join("")
    : '<div class="muted">Aucun catalogue disponible.</div>';
}

async function ensureEntityInventory(){
  if(entities.length) return;
  const data = await (await fetch("api/entities")).json();
  entities = data.entities || [];
}

function updateReportAiFields(){
  const enabled = $("reportAiEnabled").checked;
  $("reportAiEntity").disabled = !enabled;
  $("reportAiTimeout").disabled = !enabled;
}

async function populateReportAiEntities(selectedId=""){
  await ensureEntityInventory();
  const aiTasks = entities
    .filter(entity => entity.domain === "ai_task")
    .sort((a,b) => String(a.friendly_name || a.entity_id).localeCompare(String(b.friendly_name || b.entity_id)));

  const options = [
    '<option value="">Entité AI Task préférée de Home Assistant</option>',
    ...aiTasks.map(entity => `<option value="${esc(entity.entity_id)}">${esc(entity.friendly_name || entity.entity_id)} · ${esc(entity.entity_id)}</option>`)
  ];

  if(selectedId && !aiTasks.some(entity => entity.entity_id === selectedId)){
    options.push(`<option value="${esc(selectedId)}">${esc(selectedId)} · indisponible actuellement</option>`);
  }

  $("reportAiEntity").innerHTML = options.join("");
  $("reportAiEntity").value = selectedId || "";
  updateReportAiFields();
}

function localFilenamePreview(){
  const template = ($("reportFilenameTemplate")?.value || "{report_id}_{period_start}_{period_end}").trim();
  const now = new Date();
  const yyyy = String(now.getFullYear()).padStart(4,"0");
  const mm = String(now.getMonth()+1).padStart(2,"0");
  const dd = String(now.getDate()).padStart(2,"0");
  const reportName = $("reportName")?.value || "rapport";
  const reportId = editingReportId || slug(reportName) || "rapport";
  const replacements = {
    report_id:reportId, report_name:reportName, year:yyyy, month:mm, day:dd,
    period_start:`${yyyy}-${mm}-${dd}`, period_end:`${yyyy}-${mm}-${dd}`,
    period_type:$("reportPeriodType")?.value || "month",
    generated_date:`${yyyy}-${mm}-${dd}`,
    generated_datetime:`${yyyy}-${mm}-${dd}_${String(now.getHours()).padStart(2,"0")}-${String(now.getMinutes()).padStart(2,"0")}-${String(now.getSeconds()).padStart(2,"0")}`,
    comparison:"none"
  };
  let name = template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_m,key) => Object.prototype.hasOwnProperty.call(replacements,key) ? replacements[key] : `{${key}}`);
  name = name.replace(/[<>:"/\\|?*\x00-\x1f]/g,"_").replace(/\s+/g,"_").replace(/_+/g,"_").replace(/^[ ._]+|[ ._]+$/g,"") || "rapport";
  if(!name.toLowerCase().endsWith(".pdf")) name += ".pdf";
  if($("reportFilenamePreview")) $("reportFilenamePreview").textContent = name;
}

async function showReportForm(reportId=null, push=true){
  await loadCatalogs();
  editingReportId = reportId;

  let report = null;
  if(reportId){
    report = reports.find(r => r.id === reportId);
    if(!report){
      await loadReports();
      report = reports.find(r => r.id === reportId);
    }
  }

  $("reportFormTitle").textContent = report ? `Modifier · ${report.name}` : "Nouveau rapport";
  $("reportName").value = report ? report.name : "";
  $("reportName").disabled = false;
  $("reportId").value = report ? report.id : "";
  $("reportFormMessage").textContent = "";

  const period = report ? (report.period || {}) : {type:"month",mode:"current"};
  $("reportPeriodType").value = period.type || "month";
  $("reportPeriodMode").value = period.mode === "previous" ? "previous" : "current";
  $("reportCustomStart").value = period.start || "";
  $("reportCustomEnd").value = period.end || "";

  const comparisons = report ? (report.comparisons || {}) : {};
  $("reportPreviousPeriods").value = String(comparisons.previous_periods || 0);
  $("reportPreviousYears").value = String(comparisons.previous_years || 0);

  const aiAnalysis = report ? (report.ai_analysis || {}) : {};
  $("reportAiEnabled").checked = Boolean(aiAnalysis.enabled);
  $("reportAiTimeout").value = String(aiAnalysis.timeout_seconds || 600);
  await populateReportAiEntities(aiAnalysis.entity_id || "");

  const output = report ? (report.output || {}) : {};
  $("reportFilenameTemplate").value = output.filename_template || "{report_id}_{period_start}_{period_end}";
  $("reportDuplicatePolicy").value = output.duplicate_policy || "version";

  renderReportCatalogChoices(report ? report.catalogs : []);
  updateReportPeriodFields();
  localFilenamePreview();

  setPage("reportFormPage", {reportId}, push);
}

function reportPayloadFromForm(){
  const catalogIds = [...document.querySelectorAll(".reportCatalogCheck:checked")]
    .map(el => el.value);

  const periodType = $("reportPeriodType").value;
  const period = periodType === "custom"
    ? {
        type:"custom",
        start:$("reportCustomStart").value,
        end:$("reportCustomEnd").value
      }
    : {
        type:periodType,
        mode:$("reportPeriodMode").value
      };

  return {
    name:$("reportName").value,
    catalogs:catalogIds,
    period,
    comparisons:{
      previous_periods:Number($("reportPreviousPeriods").value || 0),
      previous_years:Number($("reportPreviousYears").value || 0)
    },
    ai_analysis:{
      enabled:$("reportAiEnabled").checked,
      entity_id:$("reportAiEntity").value || "",
      mode:"no_thinking_expected",
      timeout_seconds:Number($("reportAiTimeout").value || 600)
    },
    output:{
      filename_template:$("reportFilenameTemplate").value || "{report_id}_{period_start}_{period_end}",
      duplicate_policy:$("reportDuplicatePolicy").value || "version"
    }
  };
}

async function saveReportDefinition(){
  const editing = Boolean(editingReportId);
  const url = editing
    ? `api/report/${encodeURIComponent(editingReportId)}`
    : "api/reports";

  const response = await fetch(url, {
    method:editing ? "PATCH" : "POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(reportPayloadFromForm())
  });
  const data = await response.json();

  if(!response.ok){
    $("reportFormMessage").textContent = "Erreur : " + data.error;
    $("reportFormMessage").classList.add("error");
    return;
  }

  $("reportFormMessage").classList.remove("error");
  $("reportFormMessage").textContent = editing ? "✓ Rapport modifié" : "✓ Rapport créé";
  setTimeout(() => showReports(), 450);
}

async function deleteReportDefinition(reportId, name){
  if(!confirm(`Supprimer la définition du rapport « ${name} » ?\n\nAucun historique Home Assistant/VictoriaMetrics n'est supprimé.`)) return;

  const response = await fetch(`api/report/${encodeURIComponent(reportId)}`, {method:"DELETE"});
  const data = await response.json();
  if(!response.ok){
    alert(data.error);
    return;
  }
  await loadReports();
}

async function previewReport(reportId, push=true){
  previewReportId = reportId;
  const report = reports.find(r => r.id === reportId);
  $("reportPreviewTitle").textContent = report ? `Aperçu · ${report.name}` : "Aperçu du rapport";
  $("reportPreviewSubtitle").textContent = "Résolution de la période et du périmètre. Le rapport peut ensuite être exécuté sur les données réelles.";
  $("reportPreviewStatus").textContent = "Résolution en cours…";
  $("reportPreviewResult").classList.add("hidden");
  $("reportHtmlButton").classList.add("hidden");
  $("reportPdfButton").classList.add("hidden");

  setPage("reportPreviewPage", {reportId}, push);

  const response = await fetch(`api/report/${encodeURIComponent(reportId)}/preview`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:"{}"
  });
  const data = await response.json();

  if(!response.ok){
    $("reportPreviewStatus").textContent = "Erreur : " + data.error;
    $("reportPreviewStatus").classList.add("error");
    return;
  }

  $("reportPreviewStatus").classList.remove("error");
  $("reportPreviewStatus").textContent = "✓ Plan de rapport résolu";
  renderReportPlan(data.plan);
}

function renderReportPlan(plan){
  const period = plan.resolved_period || {};
  const scope = plan.scope || {};
  const strategy = (plan.execution || {}).strategy || {};
  const catalogsHtml = (plan.catalogs || []).map(c => `
    <div class="planCatalog">
      <div class="planCatalogHeader">
        ${esc(c.name)} · ${esc(c.device_count)} appareil(s) · ${esc(c.source_count)} source(s)
      </div>
      ${(c.devices || []).map(d => `
        <div class="planDevice">
          <div>
            <b>${esc(d.name)}</b>
            <div class="planDeviceMeta">${esc(d.id)} · ${esc(d.category)}</div>
          </div>
          <div>${esc(d.source_count)} source(s)</div>
        </div>`).join("")}
    </div>`).join("");

  $("reportPreviewResult").classList.remove("hidden");
  $("reportPreviewResult").innerHTML = `
    <div class="periodHero">
      <div class="periodLabel">${esc(period.label)}</div>
      <div class="periodMeta">
        Fuseau ${esc(period.timezone)} · ${esc(period.start)} → ${esc(period.end)} · sémantique ${esc(period.semantics)}
      </div>
    </div>

    <div class="planSummary">
      <div class="seriesStat"><div class="label">Catalogues</div><div class="value">${esc(scope.catalog_count)}</div></div>
      <div class="seriesStat"><div class="label">Appareils</div><div class="value">${esc(scope.device_count)}</div></div>
      <div class="seriesStat"><div class="label">Sources</div><div class="value">${esc(scope.source_count)}</div></div>
      <div class="seriesStat"><div class="label">Comparaisons</div><div class="value">${esc(scope.comparison_period_count || 0)}</div></div>
      <div class="seriesStat"><div class="label">Requêtes estimées</div><div class="value">${esc(scope.estimated_source_queries || scope.source_count)}</div></div>
      <div class="seriesStat"><div class="label">Mode prévu</div><div class="value">${strategy.base_mode === "provider_rollup" ? "Optimisé" : "Détaillé"}</div></div>
    </div>

    ${(plan.output || {}).filename_preview ? `
      <div class="outputPreviewBox">
        <b>Sortie PDF native</b>
        <span>${esc(plan.output.filename_preview)}</span>
        <small>Stockage local persistant · doublons : ${esc(plan.output.duplicate_policy || "version")}</small>
      </div>` : ""}

    ${strategy.base_mode === "provider_rollup" ? `
      <div class="optimizationNote">
        Longue période : statistiques calculées côté DataProvider/VictoriaMetrics.
        Environ ${Number(strategy.estimated_detailed_points || 0).toLocaleString()} points détaillés n'ont pas besoin d'être transférés au moteur de rapport.
      </div>` : ""}

    ${(plan.comparison_targets || []).length ? `
      <div class="comparisonPlanBox">
        <h3>Périodes de comparaison</h3>
        ${(plan.comparison_targets || []).map(target => `
          <div class="comparisonPlanRow">
            <b>${esc(target.label)}</b>
            <span>${esc(target.resolved_period.start)} → ${esc(target.resolved_period.end)}</span>
          </div>`).join("")}
      </div>` : ""}

    ${catalogsHtml}

    <details class="jsonDetails">
      <summary>Voir le JSON du plan de rapport</summary>
      <div class="seriesPreview">${esc(JSON.stringify(plan, null, 2))}</div>
    </details>
  `;
}

function reportSourceCardData(source, period){
  return metricCardData(source, period);
}

function renderExecutedSource(source, period){
  const status = source.status || "error";
  const quality = (source.analysis || {}).quality || {};

  if(status === "no_data"){
    return `
      <div class="executedSource noDataCard">
        <div class="executedSourceHeader">
          <div>
            <div class="executedSourceName">${esc(source.sensor_key)}</div>
            <div class="executedSourceEntity">${esc(source.entity_id)}</div>
          </div>
          <span class="metricPill">${esc(source.metric)}</span>
        </div>
        <div class="sourceMessage">Pas d'historique disponible sur cette période.</div>
      </div>`;
  }

  if(status === "error" || status === "unsupported"){
    return `
      <div class="executedSource errorCard">
        <div class="executedSourceHeader">
          <div>
            <div class="executedSourceName">${esc(source.sensor_key)}</div>
            <div class="executedSourceEntity">${esc(source.entity_id)}</div>
          </div>
          <span class="metricPill">${esc(source.metric)}</span>
        </div>
        <div class="sourceMessage">${esc(source.message || status)}</div>
      </div>`;
  }

  const card = reportSourceCardData(source, period);
  const cells = (card.cells || []).map(cell => `
    <div class="executedMetric">
      <div class="executedMetricLabel">${esc(cell.label)}</div>
      <div class="executedMetricValue">${cell.value}</div>
      ${cell.sub ? `<div class="sourceSub">${esc(cell.sub)}</div>` : ""}
    </div>
  `).join("");

  const validation = (source.analysis || {}).validation || {};
  const messages = [
    ...(validation.issues || []),
    ...(validation.warnings || [])
  ];
  if(source.retrieval_mode === "series_fallback"){
    messages.unshift("Vérification sur les points bruts utilisée pour ce runtime.");
  } else if((source.verification || {}).classification === "minor_corrections"){
    const verification = source.verification || {};
    const count = ((verification.diagnostic || {}).negative_transitions ?? 0);
    const rawAnomalies = Number((verification.raw_statistics || {}).anomalies_ignored || 0);
    messages.unshift(`${count} correction(s) mineure(s) runtime vérifiée(s) sur les points bruts ; fallback évité.${rawAnomalies ? ` ${rawAnomalies} irrégularité(s) locale(s) brute(s) signalée(s) par le contrôle détaillé.` : ""}`);
  }

  return `
    <div class="executedSource ${(status === "invalid" || card.invalid) ? "errorCard" : ""}">
      <div class="executedSourceHeader">
        <div>
          <div class="executedSourceName">${esc(source.sensor_key)}</div>
          <div class="executedSourceEntity">${esc(source.entity_id)}</div>
        </div>
        <span class="metricPill">${esc(source.metric)}</span>
      </div>
      <div class="executedMetrics">${cells}</div>
      ${(card.note || messages.length) ? `
        <div class="metricNotes">
          ${card.note ? `<span>${esc(card.note)}</span>` : ""}
          ${messages.map(message => `<span class="${status === "invalid" ? "error" : ""}">${esc(message)}</span>`).join("")}
        </div>` : ""}
      <div class="sourceFooter">
        ${qualityBadge(quality)}
        <span>${esc(source.points ?? 0)} point(s)</span>
        <span>${quality.gap_count == null ? "trous —" : `${esc(quality.gap_count)} trou(s)`}</span>
      </div>
    </div>`;
}

function signedValue(value, unit=""){
  if(value == null || Number.isNaN(Number(value))) return "—";
  const number = Number(value);
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toFixed(Math.abs(number) >= 100 ? 1 : 2)}${unit ? " " + unit : ""}`;
}

function comparisonStatusLabel(status){
  return ({
    comparable:"Comparable",
    partial:"Partielle",
    reconstructed:"Reconstruite",
    unavailable:"Indisponible"
  })[status] || status;
}

function comparisonSourceCard(source){
  const status = source.comparison_status || "unavailable";
  const unit = source.unit || "";
  const values = source.values || [];
  const showRelative = values.some(
    value => value.relative_change_applicable !== false
  );

  const rows = values.map(value => `
    <div class="comparisonValueRow ${showRelative ? "" : "noRelative"}">
      <div class="comparisonMetricName">${esc(value.label)}</div>
      <div><span class="comparisonMiniLabel">N</span>${formatSeriesNumber(value.base,unit)}</div>
      <div><span class="comparisonMiniLabel">Réf.</span>${formatSeriesNumber(value.reference,unit)}</div>
      <div><span class="comparisonMiniLabel">Écart</span>${signedValue(value.absolute_change,unit)}</div>
      ${showRelative ? `<div><span class="comparisonMiniLabel">%</span>${value.relative_change_percent == null ? "—" : signedValue(value.relative_change_percent,"%")}</div>` : ""}
    </div>`).join("");

  const bq = source.base_quality || {};
  const rq = source.reference_quality || {};
  const qualityText = `N couverture ${bq.period_coverage_percent == null ? "—" : Number(bq.period_coverage_percent).toFixed(1)+" %"} · ` +
    `Réf. couverture ${rq.period_coverage_percent == null ? "—" : Number(rq.period_coverage_percent).toFixed(1)+" %"}`;

  return `
    <div class="comparisonSource comparison-${status}">
      <div class="executedSourceHeader">
        <div>
          <div class="executedSourceName">${esc(source.sensor_key)}</div>
          <div class="executedSourceEntity">${esc(source.entity_id)}</div>
        </div>
        <div class="comparisonPills">
          <span class="metricPill">${esc(source.metric)}</span>
          <span class="comparisonStatus ${status}">${esc(comparisonStatusLabel(status))}</span>
        </div>
      </div>
      ${rows || `<div class="sourceMessage">Comparaison non calculable.</div>`}
      <div class="comparisonQuality">${esc(qualityText)}</div>
      ${(source.reasons || []).length ? `<div class="metricNotes">${source.reasons.map(r => `<span>${esc(r)}</span>`).join("")}</div>` : ""}
    </div>`;
}

function renderComparisonTarget(target){
  const summary = target.summary || {};
  const catalogs = (target.catalogs || []).map(catalog => `
    <div class="comparisonCatalog">
      <h4>${esc(catalog.name)}</h4>
      ${(catalog.devices || []).map(device => `
        <div class="comparisonDevice">
          <div class="comparisonDeviceTitle">${esc(device.name)}</div>
          <div class="comparisonSourceGrid">
            ${(device.sources || []).map(comparisonSourceCard).join("")}
          </div>
        </div>`).join("")}
    </div>`).join("");

  return `
    <section class="comparisonTarget">
      <div class="comparisonTargetHeader">
        <div>
          <h3>${esc(target.label)}</h3>
          <div class="muted">${esc(target.resolved_period.start)} → ${esc(target.resolved_period.end)}</div>
        </div>
      </div>
      <div class="comparisonSummary">
        <div class="seriesStat good"><div class="label">Comparables</div><div class="value">${esc(summary.sources_comparable || 0)}</div></div>
        <div class="seriesStat"><div class="label">Partielles</div><div class="value">${esc(summary.sources_partial || 0)}</div></div>
        <div class="seriesStat"><div class="label">Reconstruites</div><div class="value">${esc(summary.sources_reconstructed || 0)}</div></div>
        <div class="seriesStat"><div class="label">Indisponibles</div><div class="value">${esc(summary.sources_unavailable || 0)}</div></div>
      </div>
      ${catalogs}
    </section>`;
}

function renderAiAnalysis(result){
  const ai = result.ai_analysis || {};
  if(!ai.enabled) return "";

  if(ai.status === "completed"){
    const entity = ai.entity_id || "entité AI Task préférée";
    const duration = Number(ai.duration_seconds || 0).toFixed(2);
    return `
      <section class="aiAnalysisCard">
        <div class="aiAnalysisHeader">
          <div>
            <h3>Analyse IA</h3>
            <div class="muted">Interprétation automatique des statistiques. Les données, graphiques et indicateurs ci-dessous constituent la référence et permettent de vérifier, nuancer ou contester cette analyse.</div>
          </div>
          <span class="badge">AI Task · no-thinking</span>
        </div>
        <div class="aiAnalysisText">${esc(ai.text || "")}</div>
        <div class="muted">${esc(entity)} · ${duration} s · aucune série brute transmise au modèle</div>
      </section>`;
  }

  if(ai.status === "pending" || ai.status === "running"){
    return `
      <section class="aiAnalysisCard">
        <div class="aiAnalysisHeader">
          <div><h3>Analyse IA</h3><div class="muted">Le rapport est terminé ; l’interprétation IA continue séparément.</div></div>
          <span class="badge">${ai.status === "running" ? "en cours" : "en attente"}</span>
        </div>
        <div class="aiAnalysisText">Analyse locale en cours… Vous pouvez continuer à utiliser HA Reporting.${ai.timeout_seconds ? ` Délai maximal configuré : ${esc(ai.timeout_seconds)} s.` : ""}</div>
      </section>`;
  }

  return `
    <section class="aiAnalysisCard aiAnalysisError">
      <div class="aiAnalysisHeader">
        <div><h3>Analyse IA</h3><div class="muted">Analyse indisponible</div></div>
        <span class="badge">erreur</span>
      </div>
      <div class="aiAnalysisText">${esc(ai.error || "AI Task indisponible")}</div>
    </section>`;
}

function renderExecutedReport(result){
  const summary = result.summary || {};
  const period = result.resolved_period || {};
  const exec = result.execution || {};

  const catalogHtml = (result.catalogs || []).map(catalog => `
    <section class="executedCatalog">
      <h3 class="executedCatalogTitle">${esc(catalog.name)}</h3>
      ${(catalog.devices || []).map(device => `
        <div class="executedDevice">
          <div class="executedDeviceHeader">
            <div>
              <div class="executedDeviceTitle">${esc(device.device.name)}</div>
              <div class="executedDeviceMeta">
                ${esc(device.device.id)} · ${esc(device.device.category)} ·
                ${esc(device.summary.sources_ok)}/${esc(device.summary.sources_total)} source(s) analysée(s)
              </div>
            </div>
          </div>
          <div class="executedSourceGrid">
            ${(device.sources || []).map(source => renderExecutedSource(source, device.period || {})).join("")}
          </div>
        </div>`).join("")}
    </section>`).join("");

  $("reportPreviewResult").classList.remove("hidden");
  $("reportPreviewResult").innerHTML = `
    <div class="periodHero">
      <div class="periodLabel">${esc(period.label)}</div>
      <div class="periodMeta">
        Fuseau ${esc(period.timezone)} · ${esc(period.start)} → ${esc(period.end)}
      </div>
      <div class="executionMeta">
        Exécution réelle ·
        ${exec.analysis_mode === "provider_rollup"
          ? `mode optimisé DataProvider · qualité nominale ${esc(exec.quality_nominal_step_seconds)} s`
          : `série détaillée · pas ${esc(exec.sampling_step_seconds)} s`} ·
        ${Number(exec.duration_seconds || 0).toFixed(2)} s
        ${summary.sources_runtime_verified ? ` · ${esc(summary.sources_runtime_verified)} runtime(s) vérifié(s)` : ""}
        ${summary.sources_fallback ? ` · ${esc(summary.sources_fallback)} fallback(s) détaillé(s)` : ""}
      </div>
    </div>

    <div class="reportExecutionSummary">
      <div class="seriesStat"><div class="label">Appareils</div><div class="value">${esc(summary.devices_total)}</div></div>
      <div class="seriesStat good"><div class="label">Sources OK</div><div class="value">${esc(summary.sources_ok)}</div></div>
      <div class="seriesStat"><div class="label">Sans données</div><div class="value">${esc(summary.sources_no_data)}</div></div>
      <div class="seriesStat ${summary.sources_error ? "bad" : ""}"><div class="label">Erreurs</div><div class="value">${esc(summary.sources_error)}</div></div>
      <div class="seriesStat ${summary.sources_invalid ? "bad" : ""}"><div class="label">Invalides</div><div class="value">${esc(summary.sources_invalid)}</div></div>
      <div class="seriesStat"><div class="label">Non supportées</div><div class="value">${esc(summary.sources_unsupported)}</div></div>
      <div class="seriesStat"><div class="label">Fallbacks</div><div class="value">${esc(summary.sources_fallback ?? 0)}</div></div>
    </div>

    ${renderAiAnalysis(result)}

    ${catalogHtml}

    ${(result.comparisons || {}).enabled ? `
      <section class="comparisonsSection">
        <h2>Comparaisons N / N-x</h2>
        <p class="muted">Les écarts sont calculés uniquement lorsque les deux périodes fournissent des statistiques comparables. La qualité de chaque côté reste visible.</p>
        ${((result.comparisons || {}).targets || []).map(renderComparisonTarget).join("")}
      </section>` : ""}

    <details class="jsonDetails">
      <summary>Voir le JSON complet du rapport exécuté</summary>
      <div class="seriesPreview">${esc(JSON.stringify(result, null, 2))}</div>
    </details>
  `;
}

async function runAiAnalysis(reportId, result){
  const configuredTimeout = Number((((result.report || {}).ai_analysis || {}).timeout_seconds) || ((result.ai_analysis || {}).timeout_seconds) || 600);
  const deadline = Date.now() + (configuredTimeout + 30) * 1000;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  try{
    const startResponse = await fetch(`api/report/${encodeURIComponent(reportId)}/ai-analysis`, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:"{}"
    });
    const startData = await startResponse.json();
    if(!startResponse.ok) throw new Error(startData.error || "Impossible de démarrer l'analyse IA");
    result.ai_analysis = startData.ai_analysis || {enabled:true,status:"running",timeout_seconds:configuredTimeout};
    renderExecutedReport(result);

    let consecutiveNetworkErrors = 0;
    while(Date.now() < deadline){
      const ai = result.ai_analysis || {};
      if(ai.status === "completed" || ai.status === "error" || ai.status === "disabled") break;

      await sleep(2000);
      try{
        const statusResponse = await fetch(`api/report/${encodeURIComponent(reportId)}/ai-analysis`, {cache:"no-store"});
        const statusData = await statusResponse.json();
        if(!statusResponse.ok) throw new Error(statusData.error || "État AI Task indisponible");
        consecutiveNetworkErrors = 0;
        result.ai_analysis = statusData.ai_analysis || {enabled:true,status:"error",error:"État IA absent"};
        if(statusData.execution && typeof statusData.execution === "object"){
          result.execution = {...(result.execution || {}), ...statusData.execution};
        }
        renderExecutedReport(result);
      }catch(error){
        consecutiveNetworkErrors += 1;
        // A transient Ingress/browser fetch failure must not fail the AI job itself.
        if(consecutiveNetworkErrors >= 5){
          $("reportPreviewStatus").textContent =
            `✓ Rapport exécuté · analyse IA toujours en cours (suivi réseau temporairement indisponible)`;
        }
      }
    }

    const finalAi = result.ai_analysis || {};
    if(finalAi.status === "completed"){
      $("reportPreviewStatus").textContent += " · analyse IA OK";
    }else if(finalAi.status === "error"){
      $("reportPreviewStatus").textContent += " · analyse IA en erreur";
    }else{
      result.ai_analysis = {
        ...finalAi,
        enabled:true,
        status:"error",
        error:`Le suivi de l'analyse IA a dépassé ${configuredTimeout + 30} s. Le job serveur peut être consulté en relançant l'aperçu.`
      };
      renderExecutedReport(result);
      $("reportPreviewStatus").textContent += " · suivi IA expiré";
    }
  }catch(error){
    const message = String(error && error.message ? error.message : error);
    result.ai_analysis = {enabled:true,status:"error",error:message};
    renderExecutedReport(result);
    $("reportPreviewStatus").textContent += " · analyse IA en erreur";
  }
}


async function executeReport(reportId){
  $("reportPreviewStatus").textContent = "Exécution du rapport…";
  $("reportPreviewStatus").classList.remove("error");
  $("executeReportButton").disabled = true;

  try{
    const response = await fetch(`api/report/${encodeURIComponent(reportId)}/execute`, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:"{}"
    });
    const data = await response.json();

    if(!response.ok){
      $("reportPreviewStatus").textContent = "Erreur : " + data.error;
      $("reportPreviewStatus").classList.add("error");
      return;
    }

    const comparisonCount = (data.result.comparisons || {}).target_count || 0;
    const ai = data.result.ai_analysis || {};
    $("reportPreviewStatus").textContent =
      `✓ Rapport exécuté · ${data.result.summary.sources_ok}/${data.result.summary.sources_total} source(s) OK` +
      (comparisonCount ? ` · ${comparisonCount} comparaison(s)` : "") +
      (ai.enabled ? " · analyse IA en cours" : "");

    renderExecutedReport(data.result);
    $("reportHtmlButton").classList.remove("hidden");
    $("reportPdfButton").classList.remove("hidden");

    if(ai.enabled && (ai.status === "pending" || ai.status === "running")){
      runAiAnalysis(reportId, data.result);
    }
  }finally{
    $("executeReportButton").disabled = false;
  }
}

function currentUiTheme(){
  try{
    const probe=document.createElement("span");
    probe.style.color="var(--hr-bg)";
    probe.style.position="absolute";
    probe.style.opacity="0";
    document.body.appendChild(probe);
    const color=getComputedStyle(probe).color;
    probe.remove();
    const values=(color.match(/[\d.]+/g)||[]).slice(0,3).map(Number);
    if(values.length===3){
      const luminance=(0.2126*values[0])+(0.7152*values[1])+(0.0722*values[2]);
      return luminance < 145 ? "dark" : "light";
    }
  }catch(_){ }
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

async function generateNativePdf(){
  if(!previewReportId) return;
  const button=$("reportPdfButton");
  const old=button.textContent;
  button.disabled=true;
  button.textContent="Génération PDF…";
  try{
    const response=await fetch(`api/report/${encodeURIComponent(previewReportId)}/pdf`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({theme:currentUiTheme()})});
    const data=await response.json();
    if(!response.ok) throw new Error(data.error || "Génération PDF impossible");
    const doc=data.document || {};
    $("reportPreviewStatus").textContent += ` · PDF local : ${doc.filename || "généré"}`;
    button.textContent="PDF généré ✓";
  }catch(error){
    $("reportPreviewStatus").textContent += ` · PDF : ${String(error.message || error)}`;
    $("reportPreviewStatus").classList.add("error");
  }finally{
    button.disabled=false;
    setTimeout(()=>{button.textContent=old;},1800);
  }
}

function formatBytes(bytes){
  const n=Number(bytes||0);
  if(n<1024) return `${n} o`;
  if(n<1024*1024) return `${(n/1024).toFixed(1)} Ko`;
  return `${(n/1024/1024).toFixed(1)} Mo`;
}

async function showDocuments(push=true){
  setPage("documentsPage",{},push);
  await loadDocuments();
}

async function loadDocuments(){
  const response=await fetch("api/documents",{cache:"no-store"});
  const data=await response.json();
  documents=data.documents||[];
  renderDocuments();
}

function renderDocuments(){
  if(!documents.length){
    $("documentList").innerHTML='<div class="card empty">Aucun PDF natif généré.</div>';
    return;
  }
  $("documentList").innerHTML=documents.map(doc=>`
    <div class="documentCard">
      <div class="documentInfo">
        <div class="reportTitle">${esc(doc.filename)}</div>
        <div class="reportMeta">${esc(doc.report_name || doc.report_id)} · ${esc(doc.generated_at || "")} · ${esc(formatBytes(doc.size_bytes))}</div>
        <span class="reportPeriodPill">${esc((doc.period||{}).label || "")}</span>
        <span class="reportPeriodPill">PDF local</span>
      </div>
      <div class="reportActions">
        <button onclick="downloadDocument('${esc(doc.id)}')">Télécharger</button>
        <button class="danger" onclick="deleteDocument('${esc(doc.id)}','${esc(doc.filename)}')">Supprimer</button>
      </div>
    </div>`).join("");
}

function downloadDocument(id){
  window.open(`api/document/${encodeURIComponent(id)}/download`,"_blank","noopener");
}

async function deleteDocument(id,filename){
  if(!confirm(`Supprimer le document local « ${filename} » ?`)) return;
  const response=await fetch(`api/document/${encodeURIComponent(id)}`,{method:"DELETE"});
  const data=await response.json();
  if(!response.ok){alert(data.error||"Suppression impossible");return;}
  await loadDocuments();
}

function setPage(page, state={}, push=true){
  ["homePage","reportsPage","documentsPage","reportFormPage","reportPreviewPage","deviceAnalysisPage","providersPage","catalogPage","devicePage"].forEach(id => $(id).classList.add("hidden"));
  $(page).classList.remove("hidden");
  $("backButton").classList.toggle("hidden", page === "homePage");
  if(push) history.pushState({page, ...state}, "", "");
}

function showHome(push=true){
  currentCatalog = null;
  setPage("homePage", {}, push);
  loadCatalogs();
}

function showNewCatalog(push=true){
  $("catalogName").value = "";
  $("catalogId").value = "";
  $("catalogMessage").textContent = "";
  setPage("catalogPage", {}, push);
}

async function addDeviceTo(id, name, push=true){
  currentCatalog = id;
  editingDeviceId = null;
  existingSensorKeyByEntity.clear();
  metricOverrideByEntity.clear();
  selected.clear();
  $("deviceTitle").textContent = `Ajouter un appareil à « ${name} »`;
  $("deviceEditorHelp").textContent = "Sélectionne les sources à associer au nouvel appareil.";
  $("deviceName").value = "";
  $("deviceName").disabled = false;
  $("deviceId").value = "";
  $("category").disabled = false;
  $("saveDeviceButton").textContent = "Ajouter l'appareil";
  $("query").value = "";
  $("saveMessage").textContent = "";
  setPage("devicePage", {catalogId:id, catalogName:name}, push);
  await loadCategories();
  await loadEntities();
}

$("backButton").addEventListener("click", () => history.back());
$("newCatalogButton").addEventListener("click", () => showNewCatalog());
$("reportsButton").addEventListener("click", () => showReports());
$("documentsButton").addEventListener("click", () => showDocuments());
$("refreshDocumentsButton").addEventListener("click", () => loadDocuments());
$("newReportButton").addEventListener("click", () => showReportForm());
$("saveReportButton").addEventListener("click", saveReportDefinition);
$("reportPeriodType").addEventListener("change", () => { updateReportPeriodFields(); localFilenamePreview(); });
$("reportFilenameTemplate").addEventListener("input", localFilenamePreview);
$("reportAiEnabled").addEventListener("change", updateReportAiFields);
$("reportName").addEventListener("input", () => {
  if(!editingReportId) $("reportId").value = slug($("reportName").value);
  localFilenamePreview();
});
$("refreshReportPreviewButton").addEventListener("click", () => {
  if(previewReportId) previewReport(previewReportId, false);
});
$("executeReportButton").addEventListener("click", () => {
  if(previewReportId) executeReport(previewReportId);
});
$("reportHtmlButton").addEventListener("click", () => {
  if(!previewReportId) return;
  window.open(`api/report/${encodeURIComponent(previewReportId)}/html`, "_blank", "noopener");
});
$("reportPdfButton").addEventListener("click", generateNativePdf);
$("providersButton").addEventListener("click", () => showProviders());
$("seriesCatalog").addEventListener("change", populateSeriesDevices);
$("seriesDevice").addEventListener("change", populateSeriesSensors);
$("seriesTestButton").addEventListener("click", testCatalogSeries);

$("vmTestButton").addEventListener("click", async () => {
  $("vmStatusText").textContent = "Test en cours…";
  $("vmStatusText").classList.remove("error");
  const response = await fetch("api/providers/victoria_metrics/test", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({url:$("vmUrl").value})
  });
  const data = await response.json();
  if(!response.ok){
    $("vmStatusText").textContent = "Erreur : " + data.error;
    $("vmStatusText").classList.add("error");
    return;
  }
  renderProviderStatus(data.status);
  if(data.status.available){
    $("vmStatusText").textContent = "✓ Connexion VictoriaMetrics réussie";
    $("vmStatusText").classList.remove("error");
  }
});

$("vmSaveButton").addEventListener("click", async () => {
  const response = await fetch("api/providers/victoria_metrics", {
    method:"PATCH",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({url:$("vmUrl").value})
  });
  const data = await response.json();

  if(!response.ok){
    $("vmStatusText").textContent = "Erreur d'enregistrement : " + data.error;
    $("vmStatusText").classList.add("error");
    return;
  }

  renderProviderStatus(data);

  if(data.available){
    $("vmStatusText").textContent = "✓ Configuration enregistrée · VictoriaMetrics connecté";
    $("vmStatusText").classList.remove("error");
  }else{
    $("vmStatusText").textContent = "✓ Configuration enregistrée · ⚠ " + data.message;
    $("vmStatusText").classList.add("error");
  }
});
window.addEventListener("popstate", async event => {
  const state = event.state || {page:"homePage"};
  if(state.page === "reportPreviewPage") await previewReport(state.reportId, false);
  else if(state.page === "reportFormPage") await showReportForm(state.reportId || null, false);
  else if(state.page === "reportsPage") await showReports(false);
  else if(state.page === "documentsPage") await showDocuments(false);
  else if(state.page === "deviceAnalysisPage") await showDeviceAnalysis(state.catalogId, state.deviceId, false);
  else if(state.page === "providersPage") await showProviders(false);
  else if(state.page === "catalogPage") showNewCatalog(false);
  else if(state.page === "devicePage" && state.editDeviceId) await editDeviceSensors(state.catalogId, state.editDeviceId, false);
  else if(state.page === "devicePage") await addDeviceTo(state.catalogId, state.catalogName, false);
  else showHome(false);
});

$("catalogName").addEventListener("input", () => $("catalogId").value = slug($("catalogName").value));
$("deviceName").addEventListener("input", () => $("deviceId").value = slug($("deviceName").value));

async function loadCatalogs(){
  const response = await fetch("api/catalogs");
  const data = await response.json();
  catalogs = data.catalogs || [];
  renderCatalogs();
  if(!$("providersPage").classList.contains("hidden")){
    populateSeriesCatalogs();
  }
}

function renderCatalogs(){
  if(!catalogs.length){
    $("catalogList").innerHTML = '<div class="card empty">Aucun catalogue.</div>';
    return;
  }

  $("catalogList").innerHTML = catalogs.map(c => {
    if(c.error){
      return `<div class="catalogCard"><div class="catalogHeader"><div class="catalogMain"><div><div class="catalogTitle">${esc(c.name)}</div><div class="catalogMeta error">${esc(c.error)}</div></div></div></div></div>`;
    }

    const devices = (c.devices || []).map(d => `
      <div class="deviceRow">
        <div>
          <div class="deviceName">${esc(d.name)}</div>
          <div class="catalogMeta">${esc(d.id)}</div>
        </div>
        <div><span class="badge">${esc(d.category_name)}</span></div>
        <div>${d.sensors} capteur(s)</div>
        <div class="deviceActions">
          <button class="hasTooltip" data-tooltip="Ajouter, retirer ou modifier les capteurs de l’appareil" title="Modifier les capteurs de l’appareil" onclick="editDeviceSensors('${esc(c.id)}','${esc(d.id)}')">Capteurs</button>
          <button onclick="showDeviceAnalysis('${esc(c.id)}','${esc(d.id)}')">Analyser</button>
          <button class="hasTooltip" data-tooltip="Modifier le nom et la catégorie de l’appareil" title="Modifier le nom et la catégorie de l’appareil" aria-label="Modifier le nom et la catégorie de l’appareil" onclick="editDevice('${esc(c.id)}','${esc(d.id)}')">Modifier</button>
          <button class="danger" onclick="deleteDevice('${esc(c.id)}','${esc(d.id)}','${esc(d.name)}')">Supprimer</button>
        </div>
      </div>`).join("");

    return `
      <div class="catalogCard">
        <div class="catalogHeader">
          <button class="disclosureButton" onclick="toggleCatalog('${esc(c.id)}',this)" aria-label="Développer le catalogue" title="Développer le catalogue">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M9.29 6.71a1 1 0 0 0 0 1.41L13.17 12l-3.88 3.88a1 1 0 1 0 1.42 1.41l4.58-4.58a1 1 0 0 0 0-1.42l-4.58-4.58a1 1 0 0 0-1.42 0z"></path>
            </svg>
          </button>
          <div class="catalogMain" onclick="toggleCatalog('${esc(c.id)}',this.parentElement.querySelector('.disclosureButton'))">
            <div>
              <div class="catalogTitle">${esc(c.name)}</div>
              <div class="catalogMeta">${esc(c.id)} · ${c.device_count} appareil(s) · ${esc(c.provider)}</div>
            </div>
          </div>
          <div class="catalogActions">
            <button onclick="addDeviceTo('${esc(c.id)}','${esc(c.name)}')">+ Appareil</button>
            <button class="hasTooltip" data-tooltip="Modifier le nom du catalogue" title="Modifier le nom du catalogue" aria-label="Modifier le nom du catalogue" onclick="renameCatalog('${esc(c.id)}')">Modifier</button>
            <button class="danger" onclick="deleteCatalog('${esc(c.id)}','${esc(c.name)}')">Supprimer</button>
          </div>
        </div>
        <div id="details-${esc(c.id)}" class="catalogDetails hidden">
          ${devices || '<div class="empty">Aucun appareil dans ce catalogue.</div>'}
        </div>
      </div>`;
  }).join("");
}

function toggleCatalog(id, button){
  const details = $("details-" + id);
  const open = details.classList.toggle("hidden") === false;
  if(button){
    button.classList.toggle("open", open);
    button.setAttribute("aria-expanded", String(open));
    button.setAttribute("aria-label", open ? "Réduire le catalogue" : "Développer le catalogue");
    button.setAttribute("title", open ? "Réduire le catalogue" : "Développer le catalogue");
  }
}

async function createCatalog(){
  const response = await fetch("api/catalogs", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({name:$("catalogName").value, provider:$("provider").value})
  });
  const data = await response.json();
  if(!response.ok){
    $("catalogMessage").textContent = "Erreur : " + data.error;
    $("catalogMessage").classList.add("error");
    return;
  }
  await addDeviceTo(data.catalog.id, data.catalog.name);
}
$("createCatalogButton").addEventListener("click", createCatalog);

async function renameCatalog(id){
  const catalog = catalogs.find(c => c.id === id);
  openModal("Modifier le catalogue", `
    <label>Nom
      <input id="modalCatalogName" value="${esc(catalog.name)}">
    </label>
    <label>ID stable
      <input value="${esc(catalog.id)}" disabled>
    </label>
  `, async () => {
    const response = await fetch("api/catalog/" + encodeURIComponent(id), {
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({name:$("modalCatalogName").value})
    });
    const data = await response.json();
    if(!response.ok) throw new Error(data.error);
    closeModal();
    await loadCatalogs();
  });
}

async function deleteCatalog(id, name){
  const ok = confirm(
    `Supprimer le catalogue « ${name} » ?\n\n` +
    `Cela supprimera sa configuration HA Reporting et les appareils qu'il contient.\n` +
    `Les historiques Home Assistant et VictoriaMetrics ne seront PAS supprimés.`
  );
  if(!ok) return;

  const response = await fetch("api/catalog/" + encodeURIComponent(id), {method:"DELETE"});
  const data = await response.json();
  if(!response.ok){
    alert(data.error);
    return;
  }
  await loadCatalogs();
}

async function loadCategories(){
  const data = await (await fetch("api/categories")).json();
  categories = data.categories || [];
  $("category").innerHTML = categories.map(c =>
    `<option value="${esc(c.id)}">${esc(c.name)}</option>`
  ).join("");
}

$("addCategoryButton").addEventListener("click", async () => {
  const name = prompt("Nom de la nouvelle catégorie :");
  if(!name) return;
  const response = await fetch("api/categories", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({name})
  });
  const data = await response.json();
  if(!response.ok){
    alert(data.error);
    return;
  }
  await loadCategories();
  $("category").value = data.category.id;
});

function metricOptions(selectedMetric){
  return metricTypes.map(m =>
    `<option ${m === selectedMetric ? "selected" : ""}>${m}</option>`
  ).join("");
}

function shouldAutoSelect(entity){
  return entity.domain === "sensor"
    && !entity.entity_id.includes("_day")
    && !entity.entity_id.includes("_month")
    && ["power","energy_total","runtime","cycles","state"].includes(entity.metric_guess);
}

async function loadEntities(){
  const data = await (await fetch("api/entities")).json();
  entities = data.entities || [];
  drawEntities();
}

function drawEntities(){
  let shown = entities;
  const query = $("query").value.trim().toLowerCase();

  if(query){
    shown = shown.filter(e =>
      Object.values(e).join(" ").toLowerCase().includes(query)
    );
  }
  if($("sensorOnly").checked){
    shown = shown.filter(e => e.domain === "sensor");
  }
  if($("selectedOnly").checked){
    shown = shown.filter(e => selected.has(e.entity_id));
  }

  $("entityStatus").textContent =
    `${shown.length} résultat(s) · ${selected.size} sélectionnée(s)`;

  $("entityRows").innerHTML = shown.slice(0,300).map(e => `
    <tr data-id="${esc(e.entity_id)}">
      <td><input class="entityCheck" type="checkbox" ${selected.has(e.entity_id) ? "checked" : ""}></td>
      <td class="mono">${esc(e.entity_id)}</td>
      <td>${esc(e.state)}</td>
      <td>${esc(e.unit)}</td>
      <td>${esc(e.device_class)}</td>
      <td><select class="metricSelect">${metricOptions(metricOverrideByEntity.get(e.entity_id) || e.metric_guess)}</select></td>
    </tr>`).join("");

  document.querySelectorAll(".entityCheck").forEach(box => {
    box.addEventListener("change", event => {
      const id = event.target.closest("tr").dataset.id;
      event.target.checked ? selected.add(id) : selected.delete(id);
      drawStatusOnly(shown.length);
    });
  });

  document.querySelectorAll(".metricSelect").forEach(select => {
    select.addEventListener("change", event => {
      const id = event.target.closest("tr").dataset.id;
      metricOverrideByEntity.set(id, event.target.value);
    });
  });
}

function drawStatusOnly(count){
  $("entityStatus").textContent = `${count} résultat(s) · ${selected.size} sélectionnée(s)`;
}

$("query").addEventListener("input", drawEntities);
$("sensorOnly").addEventListener("change", drawEntities);
$("selectedOnly").addEventListener("change", drawEntities);
$("refreshEntitiesButton").addEventListener("click", loadEntities);

$("autoSelectButton").addEventListener("click", () => {
  const query = $("query").value.trim().toLowerCase();
  if(!query){
    alert("Saisis d'abord un terme de recherche, par exemple « vinotheque ».");
    return;
  }
  entities
    .filter(shouldAutoSelect)
    .filter(e => Object.values(e).join(" ").toLowerCase().includes(query))
    .forEach(e => selected.add(e.entity_id));
  drawEntities();
});

$("saveDeviceButton").addEventListener("click", async () => {
  const visibleMetrics = new Map();
  document.querySelectorAll("#entityRows tr").forEach(row => {
    visibleMetrics.set(row.dataset.id, row.querySelector(".metricSelect").value);
  });

  const sensors = [...selected].map(entityId => {
    const entity = entities.find(e => e.entity_id === entityId);
    return {
      key:existingSensorKeyByEntity.get(entityId) || undefined,
      entity_id:entityId,
      metric:visibleMetrics.get(entityId) || metricOverrideByEntity.get(entityId) || entity.metric_guess,
      unit:entity.unit
    };
  });

  const editing = Boolean(editingDeviceId);
  const url = editing
    ? `api/catalog/${encodeURIComponent(currentCatalog)}/device/${encodeURIComponent(editingDeviceId)}`
    : `api/catalog/${encodeURIComponent(currentCatalog)}/devices`;

  const response = await fetch(url, {
    method:editing ? "PATCH" : "POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(
      editing
        ? {sensors}
        : {name:$("deviceName").value, category:$("category").value, sensors}
    )
  });
  const data = await response.json();

  if(!response.ok){
    $("saveMessage").textContent = "Erreur : " + data.error;
    $("saveMessage").classList.add("error");
    return;
  }
  $("saveMessage").classList.remove("error");
  $("saveMessage").textContent = editing ? "✓ Capteurs enregistrés" : "✓ Appareil ajouté";
  setTimeout(() => showHome(), 500);
});

async function editDeviceSensors(catalogId, deviceId, push=true){
  await loadCatalogs();

  const catalog = catalogs.find(c => c.id === catalogId);
  const device = catalog ? (catalog.devices || []).find(d => d.id === deviceId) : null;
  if(!catalog || !device){
    alert("Catalogue ou appareil introuvable");
    return;
  }

  currentCatalog = catalogId;
  editingDeviceId = deviceId;
  selected.clear();
  existingSensorKeyByEntity.clear();
  metricOverrideByEntity.clear();

  for(const sensor of (device.entities || [])){
    selected.add(sensor.entity_id);
    existingSensorKeyByEntity.set(sensor.entity_id, sensor.key);
    metricOverrideByEntity.set(sensor.entity_id, sensor.metric);
  }

  $("deviceTitle").textContent = `Capteurs · ${device.name}`;
  $("deviceEditorHelp").textContent =
    "Ajoute ou retire des capteurs sans recréer l’appareil. Les clés existantes restent stables.";
  $("deviceName").value = device.name;
  $("deviceName").disabled = true;
  $("deviceId").value = device.id;
  $("category").disabled = true;
  $("saveDeviceButton").textContent = "Enregistrer les capteurs";
  $("query").value = "";
  $("saveMessage").textContent = "";

  await loadCategories();
  $("category").value = device.category;
  await loadEntities();

  setPage("devicePage", {catalogId, catalogName:catalog.name, editDeviceId:deviceId}, push);
}

async function showDeviceAnalysis(catalogId, deviceId, push=true){
  await loadCatalogs();

  const catalog = catalogs.find(c => c.id === catalogId);
  if(!catalog){
    alert("Catalogue introuvable");
    return;
  }

  const device = (catalog.devices || []).find(d => d.id === deviceId);
  if(!device){
    alert("Appareil introuvable");
    return;
  }

  analysisCatalogId = catalogId;
  analysisDeviceId = deviceId;

  $("analysisDeviceTitle").textContent = `Analyse · ${device.name}`;
  $("analysisDeviceMeta").textContent =
    `${catalog.name} · ${device.category_name} · ${device.sensors} source(s)`;

  $("deviceAnalysisStatus").textContent = "";
  $("deviceAnalysisResult").classList.add("hidden");
  $("deviceAnalysisResult").innerHTML = "";

  setPage(
    "deviceAnalysisPage",
    {catalogId, deviceId},
    push
  );
}

function qualityBadge(quality){
  const coverage = quality && quality.period_coverage_percent;
  const density = quality && quality.sample_density_percent;
  const densityApplicable = quality && quality.density_applicable !== false;

  const coverageText = coverage == null
    ? "couverture —"
    : `couverture ${Number(coverage).toFixed(1)} %`;

  const densityClass = (!densityApplicable || density == null)
    ? ""
    : density >= 95 ? "good" : density >= 80 ? "warn" : "bad";

  const densityText = !densityApplicable
    ? "densité n/a"
    : density == null
      ? "densité —"
      : `densité ${Number(density).toFixed(1)} %`;

  return `
    <span class="qualityPill">${coverageText}</span>
    <span class="qualityPill ${densityClass}">${densityText}</span>`;
}

function metricCardData(source, period){
  const analysis = source.analysis || {};
  const stats = analysis.statistics || {};
  const validation = analysis.validation || {};
  const unit = source.unit || "";
  const periodHours = period && period.duration_seconds
    ? Number(period.duration_seconds) / 3600
    : null;

  const item = {
    cells: [],
    note: "",
    invalid: validation.valid === false,
    warnings: validation.warnings || [],
    issues: validation.issues || []
  };

  if(source.metric === "power"){
    const peak = stats.max || {};
    item.cells = [
      {
        label:"Pic",
        value:formatSeriesNumber(peak.value,unit),
        sub:localDateTime(peak.timestamp)
      },
      {
        label:"P95",
        value:formatSeriesNumber(stats.p95,unit)
      },
      {
        label:"Moyenne",
        value:formatSeriesNumber(stats.mean,unit)
      }
    ];
    return item;
  }

  if(source.metric === "temperature" || source.metric === "humidity" ||
     source.metric === "voltage" || source.metric === "current"){
    const min = stats.min || {};
    const max = stats.max || {};
    item.cells = [
      {
        label:"Minimum",
        value:formatSeriesNumber(min.value,unit),
        sub:localDateTime(min.timestamp)
      },
      {
        label:"Moyenne",
        value:formatSeriesNumber(stats.mean,unit)
      },
      {
        label:"Maximum",
        value:formatSeriesNumber(max.value,unit),
        sub:localDateTime(max.timestamp)
      }
    ];
    return item;
  }

  if(source.metric === "energy_total"){
    item.cells = [
      {
        label:"Consommation période",
        value:formatSeriesNumber(stats.delta,unit)
      },
      {
        label:"Début compteur",
        value:formatSeriesNumber((stats.first||{}).value,unit)
      },
      {
        label:"Fin compteur",
        value:formatSeriesNumber((stats.last||{}).value,unit)
      }
    ];
    const mode = String(stats.mode || "").includes("reconstructed") ? "reconstruite" : "directe";
    item.note = `${mode} · ${stats.resets_detected ?? 0} reset(s) · ${stats.anomalies_ignored ?? 0} baisse(s) ignorée(s)`;
    return item;
  }

  if(source.metric === "runtime"){
    const duty = (
      stats.delta != null &&
      periodHours != null &&
      periodHours > 0
    ) ? (Number(stats.delta) / periodHours * 100) : null;

    item.cells = [
      {
        label:"Temps période",
        value:stats.plausible === false
          ? "Incohérent"
          : formatSeriesNumber(stats.delta,unit)
      },
      {
        label:"Taux fonctionnement",
        value:duty == null ? "—" : `${Math.max(0, Math.min(100, duty)).toFixed(1)} %`
      },
      {
        label:"Anomalies ignorées",
        value:String(stats.anomalies_ignored ?? 0)
      }
    ];
    const minor = Number(stats.minor_corrections_accepted || 0);
    item.note = `${stats.resets_detected ?? 0} reset(s)${minor ? ` · ${minor} correction(s) mineure(s)` : ""}`;
    return item;
  }

  if(source.metric === "cycles"){
    item.cells = [
      {
        label:"Cycles période",
        value:formatSeriesNumber(stats.delta,unit)
      },
      {
        label:"Début compteur",
        value:formatSeriesNumber((stats.first||{}).value,unit)
      },
      {
        label:"Fin compteur",
        value:formatSeriesNumber((stats.last||{}).value,unit)
      }
    ];
    const mode = String(stats.mode || "").includes("reconstructed") ? "reconstruit" : "direct";
    item.note = `${mode} · ${stats.resets_detected ?? 0} reset(s) · ${stats.anomalies_ignored ?? 0} baisse(s) ignorée(s)`;
    return item;
  }

  item.cells = [
    {
      label:"Résultat",
      value:"—"
    }
  ];
  return item;
}

function sourceMetricCells(card){
  return (card.cells || []).map(cell => `
    <div class="metricCell">
      <div class="sourceStatLabel">${esc(cell.label)}</div>
      <div class="sourceStatValue">${cell.value}</div>
      ${cell.sub ? `<div class="sourceSub">${esc(cell.sub)}</div>` : ""}
    </div>
  `).join("");
}

function renderDeviceAnalysis(result){
  const summary = result.summary || {};
  const sources = result.sources || [];

  const sourceCards = sources.map(source => {
    if(source.status === "unsupported"){
      return `
        <div class="sourceCard unsupported">
          <div class="sourceHeader">
            <div>
              <div class="sourceTitle">${esc(source.sensor_key)}</div>
              <div class="sourceEntity">${esc(source.entity_id)}</div>
            </div>
            <span class="metricPill">${esc(source.metric)}</span>
          </div>
          <div class="sourceMessage">Non disponible · ${esc(source.message || "")}</div>
        </div>`;
    }

    if(source.status === "no_data"){
      return `
        <div class="sourceCard noDataCard">
          <div class="sourceHeader">
            <div>
              <div class="sourceTitle">${esc(source.sensor_key)}</div>
              <div class="sourceEntity">${esc(source.entity_id)}</div>
            </div>
            <span class="metricPill">${esc(source.metric)}</span>
          </div>
          <div class="sourceMessage">Pas d'historique disponible sur cette période.</div>
        </div>`;
    }

    if(source.status === "error"){
      return `
        <div class="sourceCard errorCard">
          <div class="sourceHeader">
            <div>
              <div class="sourceTitle">${esc(source.sensor_key)}</div>
              <div class="sourceEntity">${esc(source.entity_id)}</div>
            </div>
            <span class="metricPill">${esc(source.metric)}</span>
          </div>
          <div class="sourceMessage">Erreur · ${esc(source.message || "")}</div>
        </div>`;
    }

    const quality = (source.analysis || {}).quality || {};
    const card = metricCardData(source, result.period || {});
    const validation = (source.analysis || {}).validation || {};
    const validationMessages = [
      ...(validation.issues || []),
      ...(validation.warnings || [])
    ];

    return `
      <div class="sourceCard ${card.invalid ? "errorCard" : ""}">
        <div class="sourceHeader">
          <div>
            <div class="sourceTitle">${esc(source.sensor_key)}</div>
            <div class="sourceEntity">${esc(source.entity_id)}</div>
          </div>
          <span class="metricPill">${esc(source.metric)}</span>
        </div>

        <div class="metricGrid metricGrid-${Math.min(3,(card.cells || []).length)}">
          ${sourceMetricCells(card)}
        </div>

        ${(card.note || validationMessages.length) ? `
          <div class="metricNotes">
            ${card.note ? `<span>${esc(card.note)}</span>` : ""}
            ${validationMessages.map(message => `<span class="${card.invalid ? "error" : ""}">${esc(message)}</span>`).join("")}
          </div>` : ""}

        <div class="sourceFooter">
          ${qualityBadge(quality)}
          <span>${esc(source.points ?? 0)} point(s)</span>
          <span>${quality.gap_count == null ? "trous —" : `${esc(quality.gap_count)} trou(s)`}</span>
        </div>
      </div>`;
  }).join("");

  $("deviceAnalysisResult").classList.remove("hidden");
  $("deviceAnalysisResult").innerHTML = `
    <div class="deviceSummary">
      <div class="seriesStat">
        <div class="label">Sources</div>
        <div class="value">${esc(summary.sources_total)}</div>
      </div>
      <div class="seriesStat good">
        <div class="label">Analysées</div>
        <div class="value">${esc(summary.sources_ok)}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Sans historique</div>
        <div class="value">${esc(summary.sources_no_data ?? 0)}</div>
      </div>
      <div class="seriesStat ${summary.sources_invalid ? "bad" : ""}">
        <div class="label">Invalides</div>
        <div class="value">${esc(summary.sources_invalid ?? 0)}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Non supportées</div>
        <div class="value">${esc(summary.sources_unsupported)}</div>
      </div>
      <div class="seriesStat ${summary.sources_error ? "bad" : ""}">
        <div class="label">Erreurs</div>
        <div class="value">${esc(summary.sources_error)}</div>
      </div>
    </div>

    <p class="diagnosticNote">
      La densité d'échantillonnage est un indicateur diagnostique : une densité faible peut provenir
      de redémarrages Home Assistant, d'interruptions, ou simplement d'une source enregistrée de manière clairsemée.
    </p>

    <div class="sourceGrid">${sourceCards}</div>

    <details class="jsonDetails">
      <summary>Voir le JSON complet de l'appareil</summary>
      <div class="seriesPreview">${esc(JSON.stringify(result, null, 2))}</div>
    </details>
  `;
}

async function analyzeCurrentDevice(){
  if(!analysisCatalogId || !analysisDeviceId) return;

  $("deviceAnalysisStatus").textContent = "Analyse en cours…";
  $("deviceAnalysisStatus").classList.remove("error");
  $("deviceAnalysisResult").classList.add("hidden");

  const response = await fetch("api/data/analyze-device", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      catalog_id:analysisCatalogId,
      device_id:analysisDeviceId,
      hours:Number($("analysisHours").value),
      step:300
    })
  });

  const data = await response.json();
  if(!response.ok){
    $("deviceAnalysisStatus").textContent = "Erreur : " + data.error;
    $("deviceAnalysisStatus").classList.add("error");
    return;
  }

  $("deviceAnalysisStatus").textContent =
    `✓ Analyse terminée · ${data.result.summary.sources_ok}/${data.result.summary.sources_total} source(s) analysée(s)`;

  renderDeviceAnalysis(data.result);
}

$("analyzeDeviceButton").addEventListener("click", analyzeCurrentDevice);

async function editDevice(catalogId, deviceId){
  const catalog = catalogs.find(c => c.id === catalogId);
  const device = catalog.devices.find(d => d.id === deviceId);
  await loadCategories();

  openModal("Modifier l'appareil", `
    <label>Nom
      <input id="modalDeviceName" value="${esc(device.name)}">
    </label>
    <label>ID stable
      <input value="${esc(device.id)}" disabled>
    </label>
    <label>Catégorie
      <select id="modalDeviceCategory">
        ${categories.map(c => `<option value="${esc(c.id)}" ${c.id === device.category ? "selected" : ""}>${esc(c.name)}</option>`).join("")}
      </select>
    </label>
  `, async () => {
    const response = await fetch(
      `api/catalog/${encodeURIComponent(catalogId)}/device/${encodeURIComponent(deviceId)}`,
      {
        method:"PATCH",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          name:$("modalDeviceName").value,
          category:$("modalDeviceCategory").value
        })
      }
    );
    const data = await response.json();
    if(!response.ok) throw new Error(data.error);
    closeModal();
    await loadCatalogs();
  });
}

async function deleteDevice(catalogId, deviceId, name){
  if(!confirm(`Retirer « ${name} » de ce catalogue ?\n\nLes historiques ne seront pas supprimés.`)) return;
  const response = await fetch(
    `api/catalog/${encodeURIComponent(catalogId)}/device/${encodeURIComponent(deviceId)}`,
    {method:"DELETE"}
  );
  const data = await response.json();
  if(!response.ok){
    alert(data.error);
    return;
  }
  await loadCatalogs();
}

function openModal(title, body, onSave){
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = body;
  modalSaveHandler = onSave;
  $("editModal").classList.remove("hidden");
}

function closeModal(){
  $("editModal").classList.add("hidden");
  modalSaveHandler = null;
}

$("modalCancel").addEventListener("click", closeModal);
$("editModal").addEventListener("click", event => {
  if(event.target === $("editModal")) closeModal();
});
$("modalSave").addEventListener("click", async () => {
  if(!modalSaveHandler) return;
  try{
    await modalSaveHandler();
  }catch(error){
    alert(error.message);
  }
});

syncHomeAssistantTheme();
history.replaceState({page:"homePage"}, "", "");
showHome(false);
loadCategories();
loadEntities();
