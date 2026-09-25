import json,logging,os,re,urllib.request
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
import yaml
PORT=8099; TOKEN=os.environ.get("SUPERVISOR_TOKEN",""); HA="http://supervisor/core/api/states"
DIR=Path("/config/catalogs"); DIR.mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s: %(message)s",datefmt="%H:%M:%S"); log=logging.getLogger("ha-reporting")

def guess(e):
 a=e.get("attributes") or {}; dc=str(a.get("device_class") or "").lower(); u=str(a.get("unit_of_measurement") or ""); eid=e.get("entity_id","").lower()
 if dc=="power" or u=="W":return "power"
 if dc=="energy" or u in ("kWh","Wh"):return "energy_total"
 if dc=="voltage" or u=="V":return "voltage"
 if dc=="current" or u=="A":return "current"
 if dc=="temperature" or u in ("°C","°F"):return "temperature"
 if dc=="humidity":return "humidity"
 if (dc=="duration" and u=="h") or (u=="h" and ("time" in eid or "runtime" in eid)):return "runtime"
 if u=="cycles" or "counter" in eid:return "cycles"
 return "state"

def states():
 if not TOKEN:raise RuntimeError("SUPERVISOR_TOKEN unavailable")
 q=urllib.request.Request(HA,headers={"Authorization":"Bearer "+TOKEN})
 with urllib.request.urlopen(q,timeout=10) as r:data=json.loads(r.read())
 return [{"entity_id":e.get("entity_id"),"state":e.get("state"),"friendly_name":(e.get("attributes") or {}).get("friendly_name",""),"unit":(e.get("attributes") or {}).get("unit_of_measurement",""),"device_class":(e.get("attributes") or {}).get("device_class",""),"metric_guess":guess(e)} for e in data]

def sid(v):return re.sub(r"[^a-z0-9_]+","_",str(v).strip().lower().replace(" ","_")).strip("_")

def catalogs():
 out=[]
 for p in sorted(list(DIR.glob("*.yaml"))+list(DIR.glob("*.yml"))):
  try:
   d=yaml.safe_load(p.read_text()) or {};out.append({"file":p.name,"id":d.get("id",p.stem),"name":d.get("name",p.stem),"devices":len(d.get("devices") or {})})
  except Exception as e:out.append({"file":p.name,"name":p.name,"error":str(e)})
 return out

def save(x):
 cid=sid(x.get("id") or x.get("name")); name=str(x.get("name") or "").strip(); d=x.get("device") or {}; did=sid(d.get("id") or d.get("name")); dn=str(d.get("name") or "").strip()
 if not cid or not name or not did or not dn:raise ValueError("Catalog and device names/IDs are required")
 ss={}; used=set()
 for s in d.get("sensors") or []:
  eid=str(s.get("entity_id") or "").strip(); metric=str(s.get("metric") or "").strip()
  if not eid or not metric:continue
  k=sid(s.get("key") or eid.split(".",1)[-1]); root=k;n=2
  while k in used:k=f"{root}_{n}";n+=1
  used.add(k); item={"entity_id":eid,"metric":metric}
  if s.get("unit"):item["unit"]=str(s["unit"])
  ss[k]=item
 if not ss:raise ValueError("Select at least one entity")
 doc={"catalog_version":1,"id":cid,"name":name,"defaults":{"provider":x.get("provider") or "victoria_metrics"},"devices":{did:{"name":dn,"category":d.get("category") or "other","enabled":True,"sensors":ss}}}
 p=DIR/f"{cid}.yaml";p.write_text(yaml.safe_dump(doc,allow_unicode=True,sort_keys=False),encoding="utf-8");log.info("Catalog saved: %s",p.name);return {"ok":True,"file":p.name}

class H(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def send(self,n,x,ct="application/json; charset=utf-8"):
  b=x if isinstance(x,bytes) else json.dumps(x,ensure_ascii=False).encode();self.send_response(n);self.send_header("Content-Type",ct);self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
 def do_GET(self):
  p=urlparse(self.path).path
  if p.endswith("/api/entities"):
   try:self.send(200,{"entities":states()})
   except Exception as e:log.exception("HA API");self.send(502,{"error":str(e)})
  elif p.endswith("/api/catalogs"):self.send(200,{"catalogs":catalogs()})
  elif p.endswith("/app.js"):self.send(200,Path("/app/app.js").read_bytes(),"application/javascript; charset=utf-8")
  elif p.endswith("/style.css"):self.send(200,Path("/app/style.css").read_bytes(),"text/css; charset=utf-8")
  else:self.send(200,Path("/app/index.html").read_bytes(),"text/html; charset=utf-8")
 def do_POST(self):
  if not urlparse(self.path).path.endswith("/api/catalogs"):return self.send(404,{"error":"Not found"})
  try:
   n=int(self.headers.get("Content-Length","0"));self.send(200,save(json.loads(self.rfile.read(n) or b"{}")))
  except Exception as e:log.exception("Save");self.send(400,{"error":str(e)})
log.info("Starting catalog editor on port %d",PORT)
try:log.info("Home Assistant API connection successful: %d entities",len(states()))
except Exception as e:log.error("HA API check failed: %s",e)
ThreadingHTTPServer(("0.0.0.0",PORT),H).serve_forever()
