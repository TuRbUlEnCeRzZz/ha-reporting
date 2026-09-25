from dataclasses import dataclass,field
from pathlib import Path
import yaml
from .models import ALLOWED_METRICS,CatalogDefinition,DeviceDefinition,SensorDefinition

class CatalogValidationError(ValueError): pass

@dataclass(frozen=True)
class CatalogError:
    filename:str
    message:str

@dataclass
class CatalogLoadResult:
    catalogs:list[CatalogDefinition]=field(default_factory=list)
    errors:list[CatalogError]=field(default_factory=list)

class CatalogLoader:
    def __init__(self,directory:str): self.directory=Path(directory)

    def load_all(self):
        r=CatalogLoadResult()
        paths=sorted(set(self.directory.glob("*.yaml"))|set(self.directory.glob("*.yml")))
        ids=set()
        for p in paths:
            try:
                c=self.load_file(p)
                if c.catalog_id in ids: raise CatalogValidationError(f"duplicate catalog id '{c.catalog_id}'")
                ids.add(c.catalog_id); r.catalogs.append(c)
            except Exception as e: r.errors.append(CatalogError(p.name,str(e)))
        return r

    def load_file(self,p):
        try: raw=yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as e: raise CatalogValidationError(f"invalid YAML: {e}") from e
        if not isinstance(raw,dict): raise CatalogValidationError("catalog root must be a YAML mapping")
        if raw.get("catalog_version")!=1: raise CatalogValidationError("catalog_version must be 1")
        cid=self.req(raw,"id","catalog"); name=self.req(raw,"name","catalog")
        desc=raw.get("description")
        if desc is not None and not isinstance(desc,str): raise CatalogValidationError("catalog.description must be a string")
        defaults=raw.get("defaults",{})
        if not isinstance(defaults,dict): raise CatalogValidationError("catalog.defaults must be a mapping")
        provider=defaults.get("provider","victoria_metrics")
        if not isinstance(provider,str) or not provider.strip(): raise CatalogValidationError("defaults.provider must be a non-empty string")
        rd=raw.get("devices")
        if not isinstance(rd,dict) or not rd: raise CatalogValidationError("catalog.devices must contain at least one device")
        devices={k:self.device(k,v,provider) for k,v in rd.items()}
        return CatalogDefinition(1,cid,name,desc,provider,devices,p.name)

    def device(self,did,raw,provider):
        if not isinstance(did,str) or not did.strip(): raise CatalogValidationError("device id must be a non-empty string")
        if not isinstance(raw,dict): raise CatalogValidationError(f"device '{did}' must be a mapping")
        name=self.req(raw,"name",f"device '{did}'")
        category=raw.get("category")
        if category is not None and not isinstance(category,str): raise CatalogValidationError(f"device '{did}'.category must be a string")
        enabled=raw.get("enabled",True)
        if not isinstance(enabled,bool): raise CatalogValidationError(f"device '{did}'.enabled must be true or false")
        tags=raw.get("tags",[])
        if not isinstance(tags,list) or not all(isinstance(x,str) for x in tags): raise CatalogValidationError(f"device '{did}'.tags must be a list of strings")
        params=raw.get("parameters",{})
        if not isinstance(params,dict): raise CatalogValidationError(f"device '{did}'.parameters must be a mapping")
        rs=raw.get("sensors")
        if not isinstance(rs,dict) or not rs: raise CatalogValidationError(f"device '{did}'.sensors must contain at least one sensor")
        sensors={}; entities=set()
        for key,val in rs.items():
            s=self.sensor(did,key,val,provider)
            if s.entity_id in entities: raise CatalogValidationError(f"device '{did}' contains duplicate entity_id '{s.entity_id}'")
            entities.add(s.entity_id); sensors[key]=s
        return DeviceDefinition(did,name,category,enabled,tags,sensors,params)

    def sensor(self,did,key,raw,provider):
        if not isinstance(key,str) or not key.strip(): raise CatalogValidationError(f"device '{did}' has an invalid sensor key")
        if not isinstance(raw,dict): raise CatalogValidationError(f"device '{did}'.sensor '{key}' must be a mapping")
        ctx=f"device '{did}'.sensor '{key}'"
        eid=self.req(raw,"entity_id",ctx)
        if "." not in eid: raise CatalogValidationError(f"{ctx}.entity_id '{eid}' does not look like a Home Assistant entity id")
        metric=self.req(raw,"metric",ctx)
        if metric not in ALLOWED_METRICS: raise CatalogValidationError(f"{ctx}.metric '{metric}' unsupported; allowed: {', '.join(sorted(ALLOWED_METRICS))}")
        unit=raw.get("unit")
        if unit is not None and not isinstance(unit,str): raise CatalogValidationError(f"{ctx}.unit must be a string")
        prov=raw.get("provider",provider)
        if not isinstance(prov,str) or not prov.strip(): raise CatalogValidationError(f"{ctx}.provider must be a non-empty string")
        return SensorDefinition(key,eid,metric,unit,prov)

    @staticmethod
    def req(raw,key,ctx):
        v=raw.get(key)
        if not isinstance(v,str) or not v.strip(): raise CatalogValidationError(f"{ctx}.{key} must be a non-empty string")
        return v.strip()
