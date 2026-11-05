// Exercise new-device category selection, including the browser's first-option default.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../ha-reporting/app/app.js'), 'utf8');
const elements = new Map();
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
  esc:s=>s, loadCatalogs:async()=>{},
  catalogs:[{id:'home', name:'Maison', devices:[{id:'tv', name:'TV PC salon', category:'computer', entities:[]}]}],
  fetch:async()=>({json:async()=>({categories:[{id:'refrigeration', name:'Réfrigération'}, {id:'other', name:'Autre'}, {id:'computer', name:'Informatique'}]})})
};
vm.createContext(sandbox);
for (const name of ['loadCategories', 'addDeviceTo', 'editDeviceSensors']) {
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
  console.log('6 device category checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
