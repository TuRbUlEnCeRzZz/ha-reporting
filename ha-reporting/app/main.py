import json
import logging
import os
import re
import time
import unicodedata
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

import yaml

from providers.victoriametrics import VictoriaMetricsProvider
from models_normalized import NormalizedSeries

PORT = 8099
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HA_STATES_URL = "http://supervisor/core/api/states"
CATALOG_DIR = Path("/config/catalogs")
CATEGORY_FILE = Path("/config/categories.yaml")
PROVIDER_FILE = Path("/config/providers.yaml")
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


def stable_id(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii").lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


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

    output = []
    for entity in data:
        attrs = entity.get("attributes") or {}
        entity_id = entity.get("entity_id", "")
        output.append(
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
    return output


def get_categories():
    custom = []
    if CATEGORY_FILE.exists():
        raw = yaml.safe_load(CATEGORY_FILE.read_text(encoding="utf-8")) or {}
        custom = raw.get("categories") or []

    output = []
    seen = set()
    for category in DEFAULT_CATEGORIES + custom:
        cid = category.get("id")
        if cid and cid not in seen:
            seen.add(cid)
            output.append(category)
    return output


def create_category(name):
    name = str(name or "").strip()
    cid = stable_id(name)
    if not name or not cid:
        raise ValueError("Nom de catégorie requis")

    custom = []
    if CATEGORY_FILE.exists():
        raw = yaml.safe_load(CATEGORY_FILE.read_text(encoding="utf-8")) or {}
        custom = raw.get("categories") or []

    existing_ids = {c.get("id") for c in DEFAULT_CATEGORIES + custom}
    if cid in existing_ids:
        return next(c for c in DEFAULT_CATEGORIES + custom if c.get("id") == cid)

    custom.append({"id": cid, "name": name})
    CATEGORY_FILE.write_text(
        yaml.safe_dump({"categories": custom}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    log.info("Custom category created: %s", cid)
    return {"id": cid, "name": name}


def catalog_path(catalog_id):
    return CATALOG_DIR / f"{stable_id(catalog_id)}.yaml"


def load_catalog(catalog_id):
    path = catalog_path(catalog_id)
    if not path.exists():
        raise FileNotFoundError(f"Catalogue introuvable: {catalog_id}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("catalog_version") != 1:
        raise ValueError(f"Version de catalogue non supportée: {data.get('catalog_version')!r}")
    return data


def save_catalog(data):
    catalog_id = data.get("id")
    if not catalog_id:
        raise ValueError("Catalogue sans identifiant")
    catalog_path(catalog_id).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def category_name(category_id):
    for category in get_categories():
        if category.get("id") == category_id:
            return category.get("name", category_id)
    return category_id or "Autre"


def catalog_summary(data, filename=None):
    devices = []
    for device_id, device in (data.get("devices") or {}).items():
        sensors = device.get("sensors") or {}
        devices.append(
            {
                "id": device_id,
                "name": device.get("name", device_id),
                "category": device.get("category", "other"),
                "category_name": category_name(device.get("category", "other")),
                "enabled": bool(device.get("enabled", True)),
                "sensors": len(sensors),
                "entities": [
                    {
                        "key": key,
                        "entity_id": sensor.get("entity_id", ""),
                        "metric": sensor.get("metric", ""),
                        "unit": sensor.get("unit", ""),
                    }
                    for key, sensor in sensors.items()
                ],
            }
        )

    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "file": filename or f"{data.get('id')}.yaml",
        "provider": (data.get("defaults") or {}).get("provider", "victoria_metrics"),
        "devices": devices,
        "device_count": len(devices),
    }


def list_catalogs():
    output = []
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if data.get("catalog_version") != 1:
                raise ValueError("catalog_version must be 1")
            output.append(catalog_summary(data, path.name))
        except Exception as exc:
            output.append(
                {
                    "id": path.stem,
                    "name": path.name,
                    "file": path.name,
                    "device_count": 0,
                    "devices": [],
                    "error": str(exc),
                }
            )
    return output


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
    save_catalog(data)
    log.info("Catalog created: %s", catalog_id)
    return catalog_summary(data)


def rename_catalog(catalog_id, payload):
    data = load_catalog(catalog_id)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Nom du catalogue requis")

    # The stored ID intentionally remains unchanged.
    data["name"] = name
    save_catalog(data)
    log.info("Catalog renamed: %s -> %s", catalog_id, name)
    return catalog_summary(data)


def delete_catalog(catalog_id):
    path = catalog_path(catalog_id)
    if not path.exists():
        raise FileNotFoundError(f"Catalogue introuvable: {catalog_id}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    device_count = len(data.get("devices") or {})
    path.unlink()
    log.warning(
        "Catalog deleted: %s (%d devices). Historical HA/VM data was not touched.",
        catalog_id,
        device_count,
    )
    return {
        "ok": True,
        "catalog_id": catalog_id,
        "devices_removed_from_reporting": device_count,
        "historical_data_deleted": False,
    }


def sensors_to_mapping(items):
    output = {}
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
        output[key] = sensor
    return output


def add_device(catalog_id, payload):
    data = load_catalog(catalog_id)
    name = str(payload.get("name") or "").strip()
    device_id = stable_id(name)
    if not name or not device_id:
        raise ValueError("Nom de l'appareil requis")

    devices = data.setdefault("devices", {})
    if device_id in devices:
        raise ValueError(f"L'appareil '{device_id}' existe déjà")

    sensors = sensors_to_mapping(payload.get("sensors"))
    if not sensors:
        raise ValueError("Sélectionnez au moins une entité")

    devices[device_id] = {
        "name": name,
        "category": payload.get("category") or "other",
        "enabled": True,
        "sensors": sensors,
    }
    save_catalog(data)
    log.info("Device added: %s -> %s", device_id, catalog_id)
    return {"catalog": catalog_summary(data), "device_id": device_id}


def update_device(catalog_id, device_id, payload):
    data = load_catalog(catalog_id)
    devices = data.get("devices") or {}
    if device_id not in devices:
        raise FileNotFoundError(f"Appareil introuvable: {device_id}")

    device = devices[device_id]
    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Nom de l'appareil requis")
        device["name"] = name
    if "category" in payload:
        device["category"] = payload.get("category") or "other"
    if "enabled" in payload:
        device["enabled"] = bool(payload.get("enabled"))

    # Device ID remains unchanged on edits.
    save_catalog(data)
    log.info("Device updated: %s/%s", catalog_id, device_id)
    return {"catalog": catalog_summary(data), "device_id": device_id}


def delete_device(catalog_id, device_id):
    data = load_catalog(catalog_id)
    devices = data.get("devices") or {}
    if device_id not in devices:
        raise FileNotFoundError(f"Appareil introuvable: {device_id}")

    del devices[device_id]
    save_catalog(data)
    log.warning("Device removed from catalog: %s/%s", catalog_id, device_id)
    return {"ok": True, "catalog": catalog_summary(data)}



def provider_config():
    if not PROVIDER_FILE.exists():
        return {"victoria_metrics": {"url": ""}}
    raw = yaml.safe_load(PROVIDER_FILE.read_text(encoding="utf-8")) or {}
    raw.setdefault("victoria_metrics", {"url": ""})
    raw["victoria_metrics"].setdefault("url", "")
    return raw


def save_provider_config(payload):
    url = str(payload.get("url") or "").strip().rstrip("/")
    if url and not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("L'URL doit commencer par http:// ou https://")

    config = provider_config()
    config["victoria_metrics"] = {"url": url}
    PROVIDER_FILE.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    log.info("VictoriaMetrics provider configuration updated")
    return provider_status()


def victoria_provider(url_override=None):
    if url_override is not None:
        url = str(url_override or "").strip().rstrip("/")
    else:
        url = (provider_config().get("victoria_metrics") or {}).get("url", "")
    return VictoriaMetricsProvider(url)


def provider_status(url_override=None):
    provider = victoria_provider(url_override)
    return provider.health_check().as_dict()


def provider_overview():
    status = provider_status()
    return {
        "providers": [
            {
                "id": "victoria_metrics",
                "name": "VictoriaMetrics",
                "url": victoria_provider().base_url,
                "status": status,
            }
        ]
    }


def catalog_sensor_source(catalog_id, device_id, sensor_key):
    catalog = load_catalog(catalog_id)
    devices = catalog.get("devices") or {}

    if device_id not in devices:
        raise FileNotFoundError(f"Appareil introuvable: {device_id}")

    sensors = devices[device_id].get("sensors") or {}
    if sensor_key not in sensors:
        raise FileNotFoundError(f"Capteur introuvable: {sensor_key}")

    source = dict(sensors[sensor_key])
    source["key"] = sensor_key
    return source


def normalized_series_test(payload):
    catalog_id = str(payload.get("catalog_id") or "").strip()
    device_id = str(payload.get("device_id") or "").strip()
    sensor_key = str(payload.get("sensor_key") or "").strip()

    if not catalog_id or not device_id or not sensor_key:
        raise ValueError("catalog_id, device_id et sensor_key sont requis")

    try:
        hours = float(payload.get("hours", 24))
    except (TypeError, ValueError) as exc:
        raise ValueError("hours doit être un nombre") from exc

    if hours <= 0 or hours > 24 * 31:
        raise ValueError("La période de test doit être comprise entre 0 et 744 heures")

    try:
        step = int(payload.get("step", 300))
    except (TypeError, ValueError) as exc:
        raise ValueError("step doit être un entier") from exc

    if step < 10 or step > 86400:
        raise ValueError("step doit être compris entre 10 et 86400 secondes")

    source = catalog_sensor_source(catalog_id, device_id, sensor_key)
    provider_id = source.get("provider") or (
        (load_catalog(catalog_id).get("defaults") or {}).get(
            "provider", "victoria_metrics"
        )
    )

    if provider_id != "victoria_metrics":
        raise ValueError(
            f"Provider '{provider_id}' non implémenté dans cette version"
        )

    provider = victoria_provider()
    status = provider.health_check()
    if not status.available:
        raise ValueError(f"VictoriaMetrics indisponible: {status.message}")

    end = time.time()
    start = end - hours * 3600

    points = provider.get_series(source, start, end, step)

    normalized = NormalizedSeries(
        provider=provider_id,
        catalog_id=catalog_id,
        device_id=device_id,
        sensor_key=sensor_key,
        entity_id=source.get("entity_id", ""),
        metric=source.get("metric", ""),
        unit=source.get("unit"),
        start=start,
        end=end,
        step=step,
        points=points,
    )

    return normalized.summary()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send_payload(self, status, payload, content_type="application/json; charset=utf-8"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def path_parts_after_catalog(self, path):
        tail = path.split("/api/catalog/", 1)[1]
        return [unquote(part) for part in tail.strip("/").split("/") if part]

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path.endswith("/api/entities"):
                return self.send_payload(200, {"entities": home_assistant_states()})
            if path.endswith("/api/providers"):
                return self.send_payload(200, provider_overview())
            if path.endswith("/api/catalogs"):
                return self.send_payload(200, {"catalogs": list_catalogs()})
            if path.endswith("/api/categories"):
                return self.send_payload(200, {"categories": get_categories()})
            if "/api/catalog/" in path:
                parts = self.path_parts_after_catalog(path)
                return self.send_payload(200, {"catalog": catalog_summary(load_catalog(parts[0]))})
            if path.endswith("/app.js"):
                return self.send_payload(200, Path("/app/app.js").read_bytes(), "application/javascript; charset=utf-8")
            if path.endswith("/style.css"):
                return self.send_payload(200, Path("/app/style.css").read_bytes(), "text/css; charset=utf-8")
            return self.send_payload(200, Path("/app/index.html").read_bytes(), "text/html; charset=utf-8")
        except Exception as exc:
            log.exception("GET failed")
            self.send_payload(400, {"error": str(exc)})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self.json_body()
            if path.endswith("/api/providers/victoria_metrics/test"):
                return self.send_payload(200, {"status": provider_status(payload.get("url"))})
            if path.endswith("/api/data/test-series"):
                return self.send_payload(200, {"result": normalized_series_test(payload)})
            if path.endswith("/api/catalogs"):
                return self.send_payload(200, {"catalog": create_catalog(payload)})
            if path.endswith("/api/categories"):
                return self.send_payload(200, {"category": create_category(payload.get("name"))})
            if "/api/catalog/" in path and path.endswith("/devices"):
                parts = self.path_parts_after_catalog(path)
                return self.send_payload(200, add_device(parts[0], payload))
            return self.send_payload(404, {"error": "Not found"})
        except Exception as exc:
            log.exception("POST failed")
            self.send_payload(400, {"error": str(exc)})

    def do_PATCH(self):
        path = urlparse(self.path).path
        try:
            payload = self.json_body()
            if path.endswith("/api/providers/victoria_metrics"):
                return self.send_payload(200, save_provider_config(payload))
            if "/api/catalog/" in path:
                parts = self.path_parts_after_catalog(path)
                if len(parts) == 1:
                    return self.send_payload(200, {"catalog": rename_catalog(parts[0], payload)})
                if len(parts) == 3 and parts[1] == "device":
                    return self.send_payload(200, update_device(parts[0], parts[2], payload))
            return self.send_payload(404, {"error": "Not found"})
        except Exception as exc:
            log.exception("PATCH failed")
            self.send_payload(400, {"error": str(exc)})

    def do_DELETE(self):
        path = urlparse(self.path).path
        try:
            if "/api/catalog/" in path:
                parts = self.path_parts_after_catalog(path)
                if len(parts) == 1:
                    return self.send_payload(200, delete_catalog(parts[0]))
                if len(parts) == 3 and parts[1] == "device":
                    return self.send_payload(200, delete_device(parts[0], parts[2]))
            return self.send_payload(404, {"error": "Not found"})
        except Exception as exc:
            log.exception("DELETE failed")
            self.send_payload(400, {"error": str(exc)})


log.info("Starting HA Reporting catalog manager on port %d", PORT)
try:
    log.info("Home Assistant API connection successful: %d entities", len(home_assistant_states()))
except Exception as exc:
    log.error("Home Assistant API initial check failed: %s", exc)

ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
