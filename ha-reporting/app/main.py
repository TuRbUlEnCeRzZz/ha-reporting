import json
import logging
import os
import re
import unicodedata
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import yaml

PORT = 8099
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HA_STATES_URL = "http://supervisor/core/api/states"
CATALOG_DIR = Path("/config/catalogs")
CATEGORY_FILE = Path("/config/categories.yaml")

CATALOG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CATEGORIES = [
    {"id": "refrigeration", "name": "Réfrigération"},
    {"id": "appliance", "name": "Électroménager"},
    {"id": "climate", "name": "Climat"},
    {"id": "computer", "name": "Informatique"},
    {"id": "lighting", "name": "Éclairage"},
    {"id": "energy", "name": "Énergie"},
    {"id": "water", "name": "Eau"},
    {"id": "ventilation", "name": "Ventilation"},
    {"id": "multimedia", "name": "Multimédia"},
    {"id": "other", "name": "Autre"},
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ha-reporting")


def stable_id(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value


def metric_guess(entity):
    attrs = entity.get("attributes") or {}
    device_class = str(attrs.get("device_class") or "").lower()
    unit = str(attrs.get("unit_of_measurement") or "")
    entity_id = str(entity.get("entity_id") or "").lower()

    if device_class == "power" or unit == "W":
        return "power"
    if device_class == "energy" or unit in ("kWh", "Wh"):
        return "energy_total"
    if device_class == "voltage" or unit == "V":
        return "voltage"
    if device_class == "current" or unit == "A":
        return "current"
    if device_class == "temperature" or unit in ("°C", "°F"):
        return "temperature"
    if device_class == "humidity":
        return "humidity"
    if (device_class == "duration" and unit == "h") or (
        unit == "h" and ("time" in entity_id or "runtime" in entity_id)
    ):
        return "runtime"
    if unit == "cycles" or "counter" in entity_id:
        return "cycles"
    return "state"


def home_assistant_states():
    if not TOKEN:
        raise RuntimeError("SUPERVISOR_TOKEN unavailable")

    request = urllib.request.Request(
        HA_STATES_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.loads(response.read())

    result = []
    for entity in data:
        attrs = entity.get("attributes") or {}
        entity_id = entity.get("entity_id", "")
        result.append(
            {
                "entity_id": entity_id,
                "domain": entity_id.split(".", 1)[0] if "." in entity_id else "",
                "state": entity.get("state"),
                "friendly_name": attrs.get("friendly_name", ""),
                "unit": attrs.get("unit_of_measurement", ""),
                "device_class": attrs.get("device_class", ""),
                "metric_guess": metric_guess(entity),
            }
        )
    return result


def get_categories():
    custom = []
    if CATEGORY_FILE.exists():
        raw = yaml.safe_load(CATEGORY_FILE.read_text(encoding="utf-8")) or {}
        custom = raw.get("categories") or []

    result = []
    seen = set()
    for category in DEFAULT_CATEGORIES + custom:
        category_id = category.get("id")
        if category_id and category_id not in seen:
            seen.add(category_id)
            result.append(category)
    return result


def create_category(name):
    name = str(name or "").strip()
    category_id = stable_id(name)
    if not name or not category_id:
        raise ValueError("Nom de catégorie requis")

    custom = []
    if CATEGORY_FILE.exists():
        raw = yaml.safe_load(CATEGORY_FILE.read_text(encoding="utf-8")) or {}
        custom = raw.get("categories") or []

    if not any(c.get("id") == category_id for c in custom):
        custom.append({"id": category_id, "name": name})
        CATEGORY_FILE.write_text(
            yaml.safe_dump({"categories": custom}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    return {"id": category_id, "name": name}


def catalog_path(catalog_id):
    return CATALOG_DIR / f"{stable_id(catalog_id)}.yaml"


def list_catalogs():
    output = []
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            output.append(
                {
                    "id": data.get("id", path.stem),
                    "name": data.get("name", path.stem),
                    "file": path.name,
                    "devices": len(data.get("devices") or {}),
                }
            )
        except Exception as exc:
            output.append(
                {"id": path.stem, "name": path.name, "file": path.name, "error": str(exc)}
            )
    return output


def load_catalog(catalog_id):
    path = catalog_path(catalog_id)
    if not path.exists():
        raise FileNotFoundError(f"Catalogue introuvable: {catalog_id}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def create_catalog(payload):
    name = str(payload.get("name") or "").strip()
    catalog_id = stable_id(name)
    if not name or not catalog_id:
        raise ValueError("Nom du catalogue requis")

    path = catalog_path(catalog_id)
    if path.exists():
        raise ValueError(f"Le catalogue '{catalog_id}' existe déjà")

    data = {
        "catalog_version": 1,
        "id": catalog_id,
        "name": name,
        "defaults": {"provider": payload.get("provider") or "victoria_metrics"},
        "devices": {},
    }
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    log.info("Catalog created: %s", path.name)
    return data


def sensors_to_mapping(items):
    result = {}
    used = set()

    for item in items or []:
        entity_id = str(item.get("entity_id") or "").strip()
        metric = str(item.get("metric") or "").strip()
        if not entity_id or not metric:
            continue

        key = stable_id(item.get("key") or entity_id.split(".", 1)[-1])
        base_key = key
        suffix = 2
        while key in used:
            key = f"{base_key}_{suffix}"
            suffix += 1

        used.add(key)
        sensor = {"entity_id": entity_id, "metric": metric}
        if item.get("unit"):
            sensor["unit"] = str(item["unit"])
        result[key] = sensor

    return result


def add_device(catalog_id, payload):
    data = load_catalog(catalog_id)

    name = str(payload.get("name") or "").strip()
    device_id = stable_id(name)
    if not name or not device_id:
        raise ValueError("Nom de l'appareil requis")

    devices = data.setdefault("devices", {})
    if device_id in devices:
        raise ValueError(f"L'appareil '{device_id}' existe déjà dans ce catalogue")

    sensors = sensors_to_mapping(payload.get("sensors"))
    if not sensors:
        raise ValueError("Sélectionnez au moins une entité")

    devices[device_id] = {
        "name": name,
        "category": payload.get("category") or "other",
        "enabled": True,
        "sensors": sensors,
    }

    catalog_path(catalog_id).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    log.info(
        "Device added: %s -> catalog %s (%d sensors)",
        device_id,
        catalog_id,
        len(sensors),
    )
    return {"catalog_id": catalog_id, "device_id": device_id}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send_payload(self, status, payload, content_type="application/json; charset=utf-8"):
        if isinstance(payload, bytes):
            body = payload
        else:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path.endswith("/api/entities"):
                return self.send_payload(200, {"entities": home_assistant_states()})
            if path.endswith("/api/catalogs"):
                return self.send_payload(200, {"catalogs": list_catalogs()})
            if path.endswith("/api/categories"):
                return self.send_payload(200, {"categories": get_categories()})
            if "/api/catalog/" in path:
                catalog_id = path.rsplit("/", 1)[-1]
                return self.send_payload(200, {"catalog": load_catalog(catalog_id)})
            if path.endswith("/app.js"):
                return self.send_payload(
                    200, Path("/app/app.js").read_bytes(), "application/javascript; charset=utf-8"
                )
            if path.endswith("/style.css"):
                return self.send_payload(
                    200, Path("/app/style.css").read_bytes(), "text/css; charset=utf-8"
                )
            return self.send_payload(
                200, Path("/app/index.html").read_bytes(), "text/html; charset=utf-8"
            )
        except Exception as exc:
            log.exception("GET failed")
            self.send_payload(400, {"error": str(exc)})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self.json_body()

            if path.endswith("/api/catalogs"):
                return self.send_payload(200, {"catalog": create_catalog(payload)})

            if path.endswith("/api/categories"):
                return self.send_payload(
                    200, {"category": create_category(payload.get("name"))}
                )

            if "/api/catalog/" in path and path.endswith("/devices"):
                catalog_id = path.split("/api/catalog/", 1)[1].rsplit("/devices", 1)[0].strip("/")
                return self.send_payload(200, add_device(catalog_id, payload))

            self.send_payload(404, {"error": "Not found"})
        except Exception as exc:
            log.exception("POST failed")
            self.send_payload(400, {"error": str(exc)})


log.info("Starting HA Reporting catalog manager on port %d", PORT)
try:
    log.info(
        "Home Assistant API connection successful: %d entities",
        len(home_assistant_states()),
    )
except Exception as exc:
    log.error("Home Assistant API initial check failed: %s", exc)

ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
