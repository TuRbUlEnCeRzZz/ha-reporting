// Exercise new-device category selection, including the browser's first-option default.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../ha-reporting/app/app.js'), 'utf8');
const elements = new Map();
const patches = [];
let saveModal;
function element(id) {
  if (!elements.has(id)) {
    const node = {value:'', disabled:false, textContent:''};
    Object.defineProperty(node, 'innerHTML', {set(html) {
      this.value = html.match(/value="([^"]+)"/)?.[1] || '';
    }});
    elements.set(id, node);
  }
  return elements.get(id);
}
const sandbox = {
  $:element, existingSensorKeyByEntity:new Map(), metricOverrideByEntity:new Map(),
  deriveEnergyByEntity:new Map(), selected:new Set(), setPage(){}, loadEntities:async()=>{},
  esc:s=>s, loadCatalogs:async()=>{}, closeModal(){},
  openModal(title, html, save) {
    element('modalDeviceName').value = html.match(/id="modalDeviceName" value="([^"]*)"/)[1];
    const select = html.match(/<select id="modalDeviceCategory">([^]*?)<\/select>/)[1];
    const options = [...select.matchAll(/<option value="([^"]*)"([^>]*)>/g)];
    // A browser selects the first option when none explicitly matches.
    element('modalDeviceCategory').value = (options.find(option => /\bselected\b/.test(option[2])) || options[0])[1];
    saveModal = save;
  },
  catalogs:[{id:'home', name:'Maison', devices:[{id:'tv', name:'TV PC salon', category:'computer', entities:[]}]}],
  fetch:async(url, options)=>{
    if (options?.method === 'PATCH') {
      patches.push(JSON.parse(options.body));
      return {ok:true, json:async()=>({})};
    }
    return {json:async()=>({categories:[{id:'refrigeration', name:'Réfrigération'}, {id:'other', name:'Autre'}, {id:'computer', name:'Informatique'}]})};
  }
};
vm.createContext(sandbox);
for (const name of ['loadCategories', 'addDeviceTo', 'editDeviceSensors', 'editDevice']) {
  const match = source.match(new RegExp(`^async function ${name}\\([^]*?^}`, 'm'));
  assert.ok(match, name);
  vm.runInContext(match[0], sandbox);
}
(async()=>{
  await sandbox.loadCategories();
  assert.equal(element('category').value,'refrigeration');
  await sandbox.addDeviceTo('home','Maison');
  assert.equal(element('category').value,'other');
  assert.equal(element('category').disabled,false);
  await sandbox.editDeviceSensors('home','tv');
  assert.equal(element('category').value,'computer');
  assert.equal(element('category').disabled,true);
  assert.equal(sandbox.catalogs[0].devices[0].category,'computer');
  await sandbox.editDevice('home','tv');
  element('modalDeviceName').value = 'TV renommée';
  await saveModal();
  assert.equal(patches.at(-1).category,'computer');
  assert.equal(patches.at(-1).name,'TV renommée');

  sandbox.catalogs[0].devices.push({id:'fan', name:'Ventilation', category:'legacy_ventilation', entities:[]});
  await sandbox.editDevice('home','fan');
  element('modalDeviceName').value = 'Ventilation renommée';
  await saveModal();
  assert.equal(patches.at(-1).category,'legacy_ventilation');
  assert.equal(patches.at(-1).name,'Ventilation renommée');
  assert.equal(sandbox.catalogs[0].devices[1].category,'legacy_ventilation');
  // An explicit user change remains possible, without changing the saved default.
  await sandbox.editDevice('home','fan');
  element('modalDeviceCategory').value = 'other';
  await saveModal();
  assert.equal(patches.at(-1).category,'other');
  assert.equal(sandbox.catalogs[0].devices[1].category,'legacy_ventilation');
  console.log('13 device category checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
