let E=[];
function esc(v){return String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function page(x){list.classList.toggle('hide',x!='list');edit.classList.toggle('hide',x!='edit');if(x=='list')loadCatalogs()}
async function loadCatalogs(){let d=await(await fetch('api/catalogs')).json();catalogs.innerHTML=d.catalogs.length?d.catalogs.map(x=>`<p><b>${esc(x.name)}</b> · ${esc(x.file)} · ${x.devices||0} appareil(s)</p>`).join(''):'Aucun catalogue.'}
function opts(s){return ['power','energy_total','voltage','current','temperature','humidity','runtime','cycles','state'].map(x=>`<option ${x==s?'selected':''}>${x}</option>`).join('')}
function auto(e){return e.entity_id.startsWith('sensor.')&&!e.entity_id.includes('_day')&&!e.entity_id.includes('_month')&&['power','energy_total','runtime','cycles','state'].includes(e.metric_guess)}
function draw(){let n=q.value.toLowerCase(),a=E.filter(e=>Object.values(e).join(' ').toLowerCase().includes(n));status.textContent=a.length+' résultat(s)';rows.innerHTML=a.slice(0,200).map(e=>`<tr data-id="${esc(e.entity_id)}"><td><input class="ck" type="checkbox" ${auto(e)?'checked':''}></td><td class="mono">${esc(e.entity_id)}</td><td>${esc(e.state)}</td><td>${esc(e.unit)}</td><td>${esc(e.device_class)}</td><td><select class="mt">${opts(e.metric_guess)}</select></td></tr>`).join('')}
async function loadEntities(){let d=await(await fetch('api/entities')).json();E=d.entities;draw()}
q.addEventListener('input',draw);
async function save(){let sensors=[];document.querySelectorAll('#rows tr').forEach(t=>{if(t.querySelector('.ck').checked){let e=E.find(x=>x.entity_id==t.dataset.id);sensors.push({entity_id:e.entity_id,metric:t.querySelector('.mt').value,unit:e.unit})}});let body={name:cn.value,id:ci.value,provider:provider.value,device:{name:dn.value,id:di.value,category:cat.value,sensors}};let r=await fetch('api/catalogs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),d=await r.json();saved.textContent=r.ok?'✓ '+d.file:'Erreur: '+d.error}
loadCatalogs();loadEntities();
