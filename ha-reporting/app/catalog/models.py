from dataclasses import dataclass, field
from typing import Any

ALLOWED_METRICS={"power","energy_total","temperature","humidity","runtime","cycles","state"}

@dataclass(frozen=True)
class SensorDefinition:
    key:str
    entity_id:str
    metric:str
    unit:str|None=None
    provider:str|None=None

@dataclass(frozen=True)
class DeviceDefinition:
    device_id:str
    name:str
    category:str|None=None
    enabled:bool=True
    tags:list[str]=field(default_factory=list)
    sensors:dict[str,SensorDefinition]=field(default_factory=dict)
    parameters:dict[str,Any]=field(default_factory=dict)

@dataclass(frozen=True)
class CatalogDefinition:
    catalog_version:int
    catalog_id:str
    name:str
    description:str|None
    default_provider:str
    devices:dict[str,DeviceDefinition]
    source_file:str
