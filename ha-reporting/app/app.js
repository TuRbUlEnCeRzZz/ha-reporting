let entities = [];
let currentCatalog = null;
let selected = new Set();

const metricTypes = [
  "power","energy_total","voltage","current",
  "temperature","humidity","runtime","cycles","state"
];

const byId = id => document.getElementById(id);

function escapeHtml(value){
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

byId("catalogName").addEventListener("input", () => {
  byId("catalogId").value = slug(byId("catalogName").value);
});
byId("deviceName").addEventListener("input", () => {
  byId("deviceId").value = slug(byId("deviceName").value);
});

function hidePages(){
  ["homePage","catalogPage","devicePage"].forEach(id => byId(id).classList.add("hidden"));
}

function showHome(){
  hidePages();
  byId("homePage").classList.remove("hidden");
  loadCatalogs();
}

function showNewCatalog(){
  hidePages();
  byId("catalogPage").classList.remove("hidden");
  byId("catalogName").value = "";
  byId("catalogId").value = "";
  byId("catalogMessage").textContent = "";
}

async function loadCatalogs(){
  const data = await (await fetch("api/catalogs")).json();
  byId("catalogList").innerHTML = data.catalogs.length
    ? data.catalogs.map(c => `
      <div class="catalogRow">
        <div>
          <b>${escapeHtml(c.name)}</b><br>
          <small>${escapeHtml(c.id)} · ${c.devices || 0} appareil(s)</small>
        </div>
        <button onclick="addDeviceTo('${escapeHtml(c.id)}','${escapeHtml(c.name)}')">+ Appareil</button>
      </div>`).join("")
    : "Aucun catalogue.";
}

async function createCatalog(){
  const response = await fetch("api/catalogs", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      name:byId("catalogName").value,
      provider:byId("provider").value
    })
  });
  const data = await response.json();

  if(!response.ok){
    byId("catalogMessage").textContent = "Erreur : " + data.error;
    return;
  }

  addDeviceTo(data.catalog.id, data.catalog.name);
}

async function addDeviceTo(id, name){
  currentCatalog = id;
  selected.clear();

  hidePages();
  byId("devicePage").classList.remove("hidden");
  byId("deviceTitle").textContent = `Ajouter un appareil à « ${name} »`;
  byId("deviceName").value = "";
  byId("deviceId").value = "";
  byId("query").value = "";
  byId("saveMessage").textContent = "";

  await loadCategories();
  drawEntities();
}

async function loadCategories(){
  const data = await (await fetch("api/categories")).json();
  byId("category").innerHTML = data.categories
    .map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)}</option>`)
    .join("");
}

async function createCategory(){
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
  byId("category").value = data.category.id;
}

function metricOptions(selectedMetric){
  return metricTypes
    .map(m => `<option ${m === selectedMetric ? "selected" : ""}>${m}</option>`)
    .join("");
}

function shouldAutoSelect(entity){
  return entity.domain === "sensor"
    && !entity.entity_id.includes("_day")
    && !entity.entity_id.includes("_month")
    && ["power","energy_total","runtime","cycles","state"].includes(entity.metric_guess);
}

function drawEntities(){
  if(!entities.length){
    byId("entityRows").innerHTML = "";
    return;
  }

  let shown = entities;
  const query = byId("query").value.trim().toLowerCase();

  if(query){
    shown = shown.filter(e =>
      Object.values(e).join(" ").toLowerCase().includes(query)
    );
  }
  if(byId("sensorOnly").checked){
    shown = shown.filter(e => e.domain === "sensor");
  }
  if(byId("selectedOnly").checked){
    shown = shown.filter(e => selected.has(e.entity_id));
  }

  byId("entityStatus").textContent =
    `${shown.length} résultat(s) · ${selected.size} sélectionnée(s)`;

  byId("entityRows").innerHTML = shown.slice(0,300).map(e => `
    <tr data-id="${escapeHtml(e.entity_id)}">
      <td><input class="entityCheck" type="checkbox" ${selected.has(e.entity_id) ? "checked" : ""}></td>
      <td class="mono">${escapeHtml(e.entity_id)}</td>
      <td>${escapeHtml(e.state)}</td>
      <td>${escapeHtml(e.unit)}</td>
      <td>${escapeHtml(e.device_class)}</td>
      <td><select class="metricSelect">${metricOptions(e.metric_guess)}</select></td>
    </tr>`).join("");

  document.querySelectorAll(".entityCheck").forEach(box => {
    box.addEventListener("change", event => {
      const id = event.target.closest("tr").dataset.id;
      event.target.checked ? selected.add(id) : selected.delete(id);
      byId("entityStatus").textContent =
        `${shown.length} résultat(s) · ${selected.size} sélectionnée(s)`;
    });
  });
}

async function loadEntities(){
  const data = await (await fetch("api/entities")).json();
  entities = data.entities;

  const query = byId("query").value.trim().toLowerCase();
  if(!selected.size && query){
    entities
      .filter(shouldAutoSelect)
      .filter(e => e.entity_id.toLowerCase().includes(query))
      .forEach(e => selected.add(e.entity_id));
  }

  drawEntities();
}

byId("query").addEventListener("input", drawEntities);
byId("sensorOnly").addEventListener("change", drawEntities);
byId("selectedOnly").addEventListener("change", drawEntities);

async function saveDevice(){
  const metricByEntity = new Map();

  document.querySelectorAll("#entityRows tr").forEach(row => {
    metricByEntity.set(row.dataset.id, row.querySelector(".metricSelect").value);
  });

  const sensors = [...selected].map(entityId => {
    const entity = entities.find(e => e.entity_id === entityId);
    return {
      entity_id: entityId,
      metric: metricByEntity.get(entityId) || entity.metric_guess,
      unit: entity.unit
    };
  });

  const response = await fetch(`api/catalog/${currentCatalog}/devices`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      name:byId("deviceName").value,
      category:byId("category").value,
      sensors
    })
  });
  const data = await response.json();

  if(!response.ok){
    byId("saveMessage").textContent = "Erreur : " + data.error;
    return;
  }

  byId("saveMessage").textContent = "✓ Appareil ajouté";
  setTimeout(showHome, 700);
}

loadCatalogs();
loadCategories();
loadEntities();
