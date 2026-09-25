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
  const pairs = {
    "--hr-bg":"--primary-background-color",
    "--hr-card":"--card-background-color",
    "--hr-text":"--primary-text-color",
    "--hr-secondary":"--secondary-text-color",
    "--hr-divider":"--divider-color",
    "--hr-primary":"--primary-color",
    "--hr-primary-text":"--text-primary-color",
    "--hr-error":"--error-color",
    "--hr-success":"--success-color"
  };
  try{
    const parentStyle = window.parent && window.parent !== window
      ? getComputedStyle(window.parent.document.documentElement)
      : null;
    if(!parentStyle) return;
    for(const [ours, theirs] of Object.entries(pairs)){
      const value = parentStyle.getPropertyValue(theirs).trim();
      if(value) document.documentElement.style.setProperty(ours, value);
    }
    const radius = parentStyle.getPropertyValue("--ha-card-border-radius").trim();
    if(radius) document.documentElement.style.setProperty("--hr-radius", radius);
  }catch(_){
    // Cross-origin or unavailable parent: CSS light/dark fallbacks remain active.
  }
}

function setPage(page, state={}, push=true){
  ["homePage","catalogPage","devicePage"].forEach(id => $(id).classList.add("hidden"));
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
window.addEventListener("popstate", async event => {
  const state = event.state || {page:"homePage"};
  if(state.page === "catalogPage") showNewCatalog(false);
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
          <button onclick="editDevice('${esc(c.id)}','${esc(d.id)}')">Modifier</button>
          <button class="danger" onclick="deleteDevice('${esc(c.id)}','${esc(d.id)}','${esc(d.name)}')">Supprimer</button>
        </div>
      </div>`).join("");

    return `
      <div class="catalogCard">
        <div class="catalogHeader">
          <button class="chevron" onclick="toggleCatalog('${esc(c.id)}',this)" aria-label="Dérouler">▶</button>
          <div class="catalogMain" onclick="toggleCatalog('${esc(c.id)}',this.parentElement.querySelector('.chevron'))">
            <div>
              <div class="catalogTitle">${esc(c.name)}</div>
              <div class="catalogMeta">${esc(c.id)} · ${c.device_count} appareil(s) · ${esc(c.provider)}</div>
            </div>
          </div>
          <div class="catalogActions">
            <button onclick="addDeviceTo('${esc(c.id)}','${esc(c.name)}')">+ Appareil</button>
            <button onclick="renameCatalog('${esc(c.id)}')">Modifier</button>
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
  if(button) button.textContent = open ? "▼" : "▶";
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
