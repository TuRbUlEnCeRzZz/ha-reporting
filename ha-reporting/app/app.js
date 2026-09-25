let entities = [];
let catalogs = [];
let categories = [];
let currentCatalog = null;
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
    state_changes:"state changes"
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

  $("seriesBadge").textContent = stats.points ? "Données reçues" : "Aucune donnée";
  $("seriesBadge").className = "providerBadge " + (stats.points ? "ok" : "error");

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

  const coverage = quality.coverage_percent;
  const qualityClass = coverage == null ? "" : coverage >= 95 ? "good" : coverage >= 80 ? "warn" : "bad";

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
      <div class="seriesStat ${qualityClass}">
        <div class="label">Couverture</div>
        <div class="value">${coverage == null ? "—" : Number(coverage).toFixed(1) + " %"}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Points reçus / attendus</div>
        <div class="value">${esc(quality.received_points ?? stats.points)} / ${esc(quality.expected_points ?? "—")}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Trous détectés</div>
        <div class="value">${esc(quality.gap_count ?? "—")}</div>
      </div>
      <div class="seriesStat">
        <div class="label">Plus grand trou</div>
        <div class="value">${quality.largest_gap_seconds == null ? "—" : Math.round(quality.largest_gap_seconds) + " s"}</div>
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

function setPage(page, state={}, push=true){
  ["homePage","providersPage","catalogPage","devicePage"].forEach(id => $(id).classList.add("hidden"));
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
  selected.clear();
  $("deviceTitle").textContent = `Ajouter un appareil à « ${name} »`;
  $("deviceName").value = "";
  $("deviceId").value = "";
  $("query").value = "";
  $("saveMessage").textContent = "";
  setPage("devicePage", {catalogId:id, catalogName:name}, push);
  await loadCategories();
  await loadEntities();
}

$("backButton").addEventListener("click", () => history.back());
$("newCatalogButton").addEventListener("click", () => showNewCatalog());
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
  if(state.page === "providersPage") await showProviders(false);
  else if(state.page === "catalogPage") showNewCatalog(false);
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
      <td><select class="metricSelect">${metricOptions(e.metric_guess)}</select></td>
    </tr>`).join("");

  document.querySelectorAll(".entityCheck").forEach(box => {
    box.addEventListener("change", event => {
      const id = event.target.closest("tr").dataset.id;
      event.target.checked ? selected.add(id) : selected.delete(id);
      drawStatusOnly(shown.length);
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
      entity_id: entityId,
      metric: visibleMetrics.get(entityId) || entity.metric_guess,
      unit: entity.unit
    };
  });

  const response = await fetch(`api/catalog/${encodeURIComponent(currentCatalog)}/devices`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      name:$("deviceName").value,
      category:$("category").value,
      sensors
    })
  });
  const data = await response.json();

  if(!response.ok){
    $("saveMessage").textContent = "Erreur : " + data.error;
    $("saveMessage").classList.add("error");
    return;
  }
  $("saveMessage").classList.remove("error");
  $("saveMessage").textContent = "✓ Appareil ajouté";
  setTimeout(() => showHome(), 500);
});

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
