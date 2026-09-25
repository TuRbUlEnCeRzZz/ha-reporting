import json, logging, os, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PORT=8099
TOKEN=os.environ.get("SUPERVISOR_TOKEN","")
URL="http://supervisor/core/api/states"
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s: %(message)s",datefmt="%H:%M:%S")
log=logging.getLogger("ha-reporting")

def guess(e):
    a=e.get("attributes") or {}; dc=str(a.get("device_class") or "").lower()
    u=str(a.get("unit_of_measurement") or ""); eid=str(e.get("entity_id") or "").lower()
    if dc=="power" or u=="W": return "power"
    if dc=="energy" or u in ("kWh","Wh"): return "energy_total"
    if dc=="temperature" or u in ("°C","°F"): return "temperature"
    if dc=="humidity" or u=="%": return "humidity"
    if u=="h" and ("time" in eid or "runtime" in eid): return "runtime"
    if u=="cycles" or "counter" in eid: return "cycles"
    return "state"

def states():
    if not TOKEN: raise RuntimeError("SUPERVISOR_TOKEN unavailable")
    r=urllib.request.Request(URL,headers={"Authorization":"Bearer "+TOKEN,"Content-Type":"application/json"})
    with urllib.request.urlopen(r,timeout=10) as x: data=json.loads(x.read())
    return [{"entity_id":e.get("entity_id"),"state":e.get("state"),
      "friendly_name":(e.get("attributes") or {}).get("friendly_name",""),
      "unit":(e.get("attributes") or {}).get("unit_of_measurement",""),
      "device_class":(e.get("attributes") or {}).get("device_class",""),
      "metric_guess":guess(e)} for e in data]

HTML="""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>HA Reporting</title>
<style>
body{font:14px system-ui;margin:0;background:#f4f6f8;color:#202124}header{padding:22px;background:white;border-bottom:1px solid #ddd}
main{max-width:1200px;margin:auto;padding:24px}.card{background:white;border:1px solid #ddd;border-radius:12px;padding:18px}
.toolbar{display:flex;gap:10px;margin-bottom:14px}input{flex:1;padding:11px;border:1px solid #ccc;border-radius:8px}
button{padding:10px 14px;border:0;border-radius:8px;background:#03a9f4;color:white;font-weight:bold}table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:9px;border-bottom:1px solid #eee}th{font-size:12px;color:#687078}.mono{font-family:monospace}.status{color:#687078;margin:10px 0}
@media(prefers-color-scheme:dark){body{background:#11151a;color:#eef2f5}header,.card,input{background:#1b2027;color:#eef2f5;border-color:#343b44}th,td{border-color:#343b44}}
</style></head><body><header><h1>HA Reporting</h1><div>0.1.0-alpha.3 · Explorateur d'entités Home Assistant</div></header>
<main><div class="card"><div class="toolbar"><input id="q" placeholder="Rechercher : vinotheque, temperature, prise_eve…"><button onclick="load()">Actualiser</button></div>
<div id="s" class="status">Chargement…</div><div style="overflow:auto"><table><thead><tr><th>Entité</th><th>Nom</th><th>État</th><th>Unité</th><th>Device class</th><th>Métrique proposée</th></tr></thead><tbody id="r"></tbody></table></div></div></main>
<script>
let all=[];const q=document.getElementById('q'),r=document.getElementById('r'),s=document.getElementById('s');
function esc(v){return String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function draw(){let n=q.value.toLowerCase(),a=all.filter(e=>Object.values(e).join(' ').toLowerCase().includes(n));s.textContent=a.length+' entité(s) affichée(s) sur '+all.length;r.innerHTML=a.slice(0,500).map(e=>'<tr><td class="mono">'+esc(e.entity_id)+'</td><td>'+esc(e.friendly_name)+'</td><td>'+esc(e.state)+'</td><td>'+esc(e.unit)+'</td><td>'+esc(e.device_class)+'</td><td>'+esc(e.metric_guess)+'</td></tr>').join('')}
async function load(){s.textContent='Chargement…';try{let x=await fetch('api/entities'),d=await x.json();if(!x.ok)throw Error(d.error||x.status);all=d.entities;draw()}catch(e){s.textContent='Erreur : '+e.message}}
q.addEventListener('input',draw);load();
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self,*_): pass
    def out(self,code,b,ct):
        self.send_response(code);self.send_header("Content-Type",ct);self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(b)
    def do_GET(self):
        p=urlparse(self.path).path
        if p.endswith("/api/entities"):
            try:self.out(200,json.dumps({"entities":states()},ensure_ascii=False).encode(),"application/json; charset=utf-8")
            except Exception as e:log.exception("HA API error");self.out(502,json.dumps({"error":str(e)}).encode(),"application/json")
        else:self.out(200,HTML.encode(),"text/html; charset=utf-8")

log.info("Starting Ingress UI on 0.0.0.0:%d",PORT)
try: log.info("Home Assistant API connection successful: %d entities",len(states()))
except Exception as e: log.error("Home Assistant API initial check failed: %s",e)
ThreadingHTTPServer(("0.0.0.0",PORT),H).serve_forever()
