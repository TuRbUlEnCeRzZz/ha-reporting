import json
import logging
import math
import os
import re
import time
import unicodedata
import threading
import copy
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

import yaml

from providers.victoriametrics import VictoriaMetricsProvider
from models_normalized import NormalizedSeries
from analysis.device import DeviceAnalysisEngine
from periods.engine import PeriodEngine
from comparisons.engine import ComparisonEngine
from rendering.html_report import render_report_html
from analysis.ai_report import analyze_report_with_ai

PORT = 8099
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HA_STATES_URL = "http://supervisor/core/api/states"
HA_CONFIG_URL = "http://supervisor/core/api/config"
CATALOG_DIR = Path("/config/catalogs")
CATEGORY_FILE = Path("/config/categories.yaml")
PROVIDER_FILE = Path("/config/providers.yaml")
REPORT_DIR = Path("/config/reports")
REPORT_ROLLUP_THRESHOLD_SECONDS = 45 * 24 * 3600
REPORT_QUALITY_STEP_SECONDS = 300
AI_DEFAULT_TIMEOUT_SECONDS = 600
AI_MIN_TIMEOUT_SECONDS = 60
AI_MAX_TIMEOUT_SECONDS = 1800
AI_HARD_TIMEOUT_GRACE_SECONDS = 5

LAST_REPORT_RESULTS = {}
LAST_REPORT_RESULTS_LOCK = threading.Lock()

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



def home_assistant_config():
    if not TOKEN:
        raise RuntimeError("SUPERVISOR_TOKEN unavailable")

    request = urllib.request.Request(
        HA_CONFIG_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def home_assistant_timezone():
    try:
        return str(home_assistant_config().get("time_zone") or "UTC")
    except Exception as exc:
        log.warning("Unable to read Home Assistant timezone: %s", exc)
        return "UTC"


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

        # Preserve a supplied existing key; generate one only for new sources.
        key = stable_id(item.get("key") or entity_id.split(".", 1)[-1])
        if not key:
            raise ValueError(f"Clé de capteur invalide pour {entity_id}")

        base_key = key
        suffix = 2
        while key in used:
            key = f"{base_key}_{suffix}"
            suffix += 1

        used.add(key)
        sensor = {"entity_id": entity_id, "metric": metric}
        if item.get("unit"):
            sensor["unit"] = str(item["unit"])
        if item.get("provider"):
            sensor["provider"] = str(item["provider"])
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

    if "sensors" in payload:
        sensors = sensors_to_mapping(payload.get("sensors"))
        if not sensors:
            raise ValueError("Un appareil doit contenir au moins un capteur")
        device["sensors"] = sensors

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


def resolve_provider(provider_id):
    if provider_id == "victoria_metrics":
        return victoria_provider()
    raise ValueError(f"Provider '{provider_id}' non implémenté")


def analyze_complete_device(payload):
    catalog_id = str(payload.get("catalog_id") or "").strip()
    device_id = str(payload.get("device_id") or "").strip()

    if not catalog_id or not device_id:
        raise ValueError("catalog_id et device_id sont requis")

    try:
        hours = float(payload.get("hours", 24))
    except (TypeError, ValueError) as exc:
        raise ValueError("hours doit être un nombre") from exc

    if hours <= 0 or hours > 24 * 31:
        raise ValueError("La période doit être comprise entre 0 et 744 heures")

    try:
        step = int(payload.get("step", 300))
    except (TypeError, ValueError) as exc:
        raise ValueError("step doit être un entier") from exc

    if step < 10 or step > 86400:
        raise ValueError("step doit être compris entre 10 et 86400 secondes")

    catalog = load_catalog(catalog_id)
    devices = catalog.get("devices") or {}
    if device_id not in devices:
        raise FileNotFoundError(f"Appareil introuvable: {device_id}")

    end = time.time()
    start = end - hours * 3600

    engine = DeviceAnalysisEngine(resolve_provider)
    return engine.analyze(
        catalog_id=catalog_id,
        catalog_name=catalog.get("name", catalog_id),
        device_id=device_id,
        device=devices[device_id],
        default_provider=(catalog.get("defaults") or {}).get(
            "provider", "victoria_metrics"
        ),
        start=start,
        end=end,
        step=step,
    )


def report_path(report_id):
    return REPORT_DIR / f"{stable_id(report_id)}.yaml"


def load_report(report_id):
    path = report_path(report_id)
    if not path.exists():
        raise FileNotFoundError(f"Rapport introuvable: {report_id}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if data.get("report_version") != 1:
        raise ValueError(f"Version de rapport non supportée: {data.get('report_version')!r}")
    return data


def save_report(data):
    report_id = data.get("id")
    if not report_id:
        raise ValueError("Rapport sans identifiant")
    report_path(report_id).write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _validate_report_catalogs(catalog_ids):
    ids = []
    for raw in catalog_ids or []:
        cid = stable_id(raw)
        if not cid:
            continue
        load_catalog(cid)
        if cid not in ids:
            ids.append(cid)

    if not ids:
        raise ValueError("Sélectionnez au moins un catalogue")
    return ids


def _validated_period_spec(payload):
    raw = payload.get("period") or {}
    period_type = str(raw.get("type") or "month")
    mode = str(raw.get("mode") or "current")

    spec = {"type": period_type}

    if period_type == "custom":
        spec["mode"] = "custom"
        spec["start"] = str(raw.get("start") or "").strip()
        spec["end"] = str(raw.get("end") or "").strip()
    else:
        spec["mode"] = mode

    # Resolve once at save time for validation only.
    PeriodEngine(home_assistant_timezone()).resolve(spec)
    return spec


def _validated_comparisons(payload):
    raw = payload.get("comparisons") or {}

    def count(name):
        try:
            value = int(raw.get(name, 0) or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} doit être un entier") from exc
        if value < 0 or value > 5:
            raise ValueError("Chaque type de comparaison est limité à 5 périodes")
        return value

    return {
        "previous_periods": count("previous_periods"),
        "previous_years": count("previous_years"),
    }


def _ai_timeout_seconds(raw):
    raw = raw or {}
    try:
        value = int(raw.get("timeout_seconds", AI_DEFAULT_TIMEOUT_SECONDS) or AI_DEFAULT_TIMEOUT_SECONDS)
    except (TypeError, ValueError) as exc:
        raise ValueError("Le délai maximal de l'analyse IA doit être un entier") from exc
    if value < AI_MIN_TIMEOUT_SECONDS or value > AI_MAX_TIMEOUT_SECONDS:
        raise ValueError(
            f"Le délai maximal de l'analyse IA doit être compris entre "
            f"{AI_MIN_TIMEOUT_SECONDS} et {AI_MAX_TIMEOUT_SECONDS} secondes"
        )
    return value


def _validated_ai_analysis(payload):
    raw = payload.get("ai_analysis") or {}
    enabled = bool(raw.get("enabled", False))
    entity_id = str(raw.get("entity_id") or "").strip()
    if entity_id and not entity_id.startswith("ai_task."):
        raise ValueError("L'entité d'analyse IA doit appartenir au domaine ai_task")
    return {
        "enabled": enabled,
        "entity_id": entity_id,
        "mode": "no_thinking_expected",
        "timeout_seconds": _ai_timeout_seconds(raw),
    }


def report_summary(data):
    catalog_ids = data.get("catalogs") or []
    catalog_names = []
    for cid in catalog_ids:
        try:
            catalog_names.append(load_catalog(cid).get("name", cid))
        except Exception:
            catalog_names.append(cid)

    return {
        "id": data.get("id"),
        "name": data.get("name", data.get("id")),
        "catalogs": catalog_ids,
        "catalog_names": catalog_names,
        "period": data.get("period") or {},
        "comparisons": data.get("comparisons") or {
            "previous_periods": 0,
            "previous_years": 0,
        },
        "ai_analysis": {
            "enabled": bool((data.get("ai_analysis") or {}).get("enabled", False)),
            "entity_id": str((data.get("ai_analysis") or {}).get("entity_id") or "").strip(),
            "mode": "no_thinking_expected",
            "timeout_seconds": _ai_timeout_seconds(data.get("ai_analysis") or {}),
        },
    }


def list_reports():
    output = []
    for path in sorted(REPORT_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if data.get("report_version") != 1:
                raise ValueError("report_version must be 1")
            output.append(report_summary(data))
        except Exception as exc:
            output.append(
                {
                    "id": path.stem,
                    "name": path.name,
                    "catalogs": [],
                    "catalog_names": [],
                    "period": {},
                    "error": str(exc),
                }
            )
    return output


def create_report(payload):
    name = str(payload.get("name") or "").strip()
    report_id = stable_id(name)
    if not name or not report_id:
        raise ValueError("Nom du rapport requis")

    path = report_path(report_id)
    if path.exists():
        raise ValueError(f"Le rapport '{report_id}' existe déjà")

    data = {
        "report_version": 1,
        "id": report_id,
        "name": name,
        "catalogs": _validate_report_catalogs(payload.get("catalogs")),
        "period": _validated_period_spec(payload),
        "comparisons": _validated_comparisons(payload),
        "ai_analysis": _validated_ai_analysis(payload),
    }
    save_report(data)
    log.info("Report created: %s", report_id)
    return report_summary(data)


def update_report(report_id, payload):
    data = load_report(report_id)

    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError("Nom du rapport requis")
        data["name"] = name

    if "catalogs" in payload:
        data["catalogs"] = _validate_report_catalogs(payload.get("catalogs"))

    if "period" in payload:
        data["period"] = _validated_period_spec(payload)

    if "comparisons" in payload:
        data["comparisons"] = _validated_comparisons(payload)

    if "ai_analysis" in payload:
        data["ai_analysis"] = _validated_ai_analysis(payload)

    save_report(data)
    log.info("Report updated: %s", report_id)
    return report_summary(data)


def delete_report(report_id):
    path = report_path(report_id)
    if not path.exists():
        raise FileNotFoundError(f"Rapport introuvable: {report_id}")
    path.unlink()
    log.warning("Report deleted: %s", report_id)
    return {"ok": True, "report_id": report_id}



def report_retrieval_mode(resolved):
    duration = max(
        0.0,
        resolved.end.timestamp() - resolved.start.timestamp(),
    )
    if duration > REPORT_ROLLUP_THRESHOLD_SECONDS:
        return "provider_rollup"
    return "series"


def report_strategy_summary(resolved, source_count=0, comparison_targets=None):
    targets = list(comparison_targets or [])
    periods = [resolved] + [target["resolved_period"] for target in targets]
    modes = [report_retrieval_mode(period) for period in periods]

    detailed_points = 0
    for period in periods:
        duration = max(
            0.0,
            period.end.timestamp() - period.start.timestamp(),
        )
        detailed_points += int(
            math.ceil(duration / REPORT_QUALITY_STEP_SECONDS)
        ) * int(source_count or 0)

    unique_modes = set(modes)
    mode = modes[0] if len(unique_modes) == 1 else "mixed"

    return {
        "mode": mode,
        "base_mode": modes[0],
        "comparison_modes": modes[1:],
        "rollup_threshold_days": (
            REPORT_ROLLUP_THRESHOLD_SECONDS / 86400
        ),
        "quality_nominal_step_seconds": REPORT_QUALITY_STEP_SECONDS,
        "estimated_detailed_points": detailed_points,
        "raw_series_transfer_expected": all(
            item == "series" for item in modes
        ),
    }


def build_report_plan(report_id):
    report = load_report(report_id)
    timezone_name = home_assistant_timezone()
    resolved = PeriodEngine(timezone_name).resolve(report.get("period") or {})

    catalog_plans = []
    device_count = 0
    source_count = 0

    for catalog_id in report.get("catalogs") or []:
        catalog = load_catalog(catalog_id)
        devices = []

        for device_id, device in (catalog.get("devices") or {}).items():
            if not bool(device.get("enabled", True)):
                continue
            sensors = device.get("sensors") or {}
            devices.append(
                {
                    "id": device_id,
                    "name": device.get("name", device_id),
                    "category": device.get("category", "other"),
                    "source_count": len(sensors),
                }
            )
            device_count += 1
            source_count += len(sensors)

        catalog_plans.append(
            {
                "id": catalog_id,
                "name": catalog.get("name", catalog_id),
                "provider": (catalog.get("defaults") or {}).get("provider", "victoria_metrics"),
                "device_count": len(devices),
                "source_count": sum(d["source_count"] for d in devices),
                "devices": devices,
            }
        )

    comparison_targets = PeriodEngine(timezone_name).comparison_targets(
        resolved,
        report.get("comparisons") or {},
    )

    strategy = report_strategy_summary(
        resolved,
        source_count=source_count,
        comparison_targets=comparison_targets,
    )

    return {
        "report_version": 1,
        "report": report_summary(report),
        "resolved_period": resolved.as_dict(),
        "scope": {
            "catalog_count": len(catalog_plans),
            "device_count": device_count,
            "source_count": source_count,
            "comparison_period_count": len(comparison_targets),
            "estimated_source_queries": source_count * (1 + len(comparison_targets)),
        },
        "comparison_targets": [
            {
                "id": target["id"],
                "kind": target["kind"],
                "offset": target["offset"],
                "label": target["label"],
                "resolved_period": target["resolved_period"].as_dict(),
            }
            for target in comparison_targets
        ],
        "catalogs": catalog_plans,
        "execution": {
            "status": "planned",
            "data_queries_executed": False,
            "strategy": strategy,
            "next_stage": "report_execution_engine",
        },
    }



def _execute_report_period(
    report,
    resolved,
    step=REPORT_QUALITY_STEP_SECONDS,
    retrieval_mode=None,
):
    start_epoch = resolved.start.timestamp()
    end_epoch = resolved.end.timestamp()
    retrieval_mode = retrieval_mode or report_retrieval_mode(resolved)
    started = time.time()
    device_engine = DeviceAnalysisEngine(resolve_provider)

    catalog_results = []
    total_devices = 0
    total_sources = 0
    sources_ok = 0
    sources_no_data = 0
    sources_unsupported = 0
    sources_error = 0
    sources_invalid = 0
    sources_fallback = 0
    sources_runtime_verified = 0

    for catalog_id in report.get("catalogs") or []:
        catalog = load_catalog(catalog_id)
        default_provider = (catalog.get("defaults") or {}).get(
            "provider", "victoria_metrics"
        )
        devices_out = []

        for device_id, device in (catalog.get("devices") or {}).items():
            if not bool(device.get("enabled", True)):
                continue

            result = device_engine.analyze(
                catalog_id=catalog_id,
                catalog_name=catalog.get("name", catalog_id),
                device_id=device_id,
                device=device,
                default_provider=default_provider,
                start=start_epoch,
                end=end_epoch,
                step=step,
                retrieval_mode=retrieval_mode,
            )

            total_devices += 1
            total_sources += result["summary"]["sources_total"]
            sources_ok += result["summary"]["sources_ok"]
            sources_no_data += result["summary"]["sources_no_data"]
            sources_invalid += result["summary"].get("sources_invalid", 0)
            sources_unsupported += result["summary"]["sources_unsupported"]
            sources_error += result["summary"]["sources_error"]
            sources_fallback += result["summary"].get("sources_fallback", 0)
            sources_runtime_verified += result["summary"].get("sources_runtime_verified", 0)
            devices_out.append(result)

        catalog_results.append(
            {
                "id": catalog_id,
                "name": catalog.get("name", catalog_id),
                "provider": default_provider,
                "devices": devices_out,
            }
        )

    finished = time.time()
    return {
        "resolved_period": resolved.as_dict(),
        "execution": {
            "status": "completed",
            "data_queries_executed": True,
            "analysis_mode": retrieval_mode,
            "sampling_step_seconds": (
                step if retrieval_mode == "series" else None
            ),
            "quality_nominal_step_seconds": step,
            "raw_series_transferred": (
                retrieval_mode == "series"
                or sources_fallback > 0
                or sources_runtime_verified > 0
            ),
            "started_at_epoch": started,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
        },
        "summary": {
            "catalogs_total": len(catalog_results),
            "devices_total": total_devices,
            "sources_total": total_sources,
            "sources_ok": sources_ok,
            "sources_no_data": sources_no_data,
            "sources_unsupported": sources_unsupported,
            "sources_error": sources_error,
            "sources_invalid": sources_invalid,
            "sources_fallback": sources_fallback,
            "sources_runtime_verified": sources_runtime_verified,
        },
        "catalogs": catalog_results,
    }


def _cache_report_result(report_id, result):
    with LAST_REPORT_RESULTS_LOCK:
        LAST_REPORT_RESULTS[report_id] = copy.deepcopy(result)


def _cached_report_result(report_id):
    with LAST_REPORT_RESULTS_LOCK:
        result = LAST_REPORT_RESULTS.get(report_id)
        return copy.deepcopy(result) if result is not None else None


def execute_report(report_id):
    """Execute deterministic report calculations only.

    AI interpretation is deliberately decoupled from this request so a slow or
    stuck local model can never keep the report UI in "Exécution en cours".
    """
    report = load_report(report_id)
    timezone_name = home_assistant_timezone()
    period_engine = PeriodEngine(timezone_name)
    resolved = period_engine.resolve(report.get("period") or {})
    step = REPORT_QUALITY_STEP_SECONDS

    full_started = time.time()
    base_mode = report_retrieval_mode(resolved)
    base = _execute_report_period(
        report,
        resolved,
        step=step,
        retrieval_mode=base_mode,
    )
    target_specs = period_engine.comparison_targets(
        resolved,
        report.get("comparisons") or {},
    )

    comparison_engine = ComparisonEngine()
    comparison_targets = []

    for target in target_specs:
        reference_period = target["resolved_period"]
        reference = _execute_report_period(
            report,
            reference_period,
            step=step,
            retrieval_mode=report_retrieval_mode(reference_period),
        )
        comparison_targets.append(
            comparison_engine.compare_target(base, reference, target)
        )

    data_finished = time.time()
    ai_config = report.get("ai_analysis") or {}
    ai_enabled = bool(ai_config.get("enabled"))
    result = {
        "report_version": 1,
        "report": report_summary(report),
        **base,
        "execution": {
            **base["execution"],
            "comparison_periods_executed": len(comparison_targets),
            "strategy": report_strategy_summary(
                resolved,
                source_count=base["summary"]["sources_total"],
                comparison_targets=target_specs,
            ),
            "data_total_duration_seconds": data_finished - full_started,
            "data_finished_at_epoch": data_finished,
            "ai_analysis_duration_seconds": 0.0,
            "finished_at_epoch": data_finished,
            "total_duration_seconds": data_finished - full_started,
        },
        "comparisons": {
            "enabled": bool(comparison_targets),
            "target_count": len(comparison_targets),
            "targets": comparison_targets,
        },
        "ai_analysis": ({
            "enabled": True,
            "status": "pending",
            "entity_id": str(ai_config.get("entity_id") or "").strip() or None,
            "mode": "no_thinking_expected",
            "mode_control": "ai_task_entity_configuration",
            "timeout_seconds": _ai_timeout_seconds(ai_config),
        } if ai_enabled else {
            "enabled": False,
            "status": "disabled",
        }),
    }
    _cache_report_result(report_id, result)
    return result


def execute_ai_analysis(report_id):
    """Run AI interpretation separately with a hard wall-clock deadline.

    The underlying Home Assistant request can theoretically continue in its daemon
    worker after the deadline, but the report server and UI are released reliably.
    """
    report = load_report(report_id)
    ai_config = report.get("ai_analysis") or {}
    result = _cached_report_result(report_id)
    if result is None:
        result = execute_report(report_id)

    if not bool(ai_config.get("enabled")):
        analysis = {"enabled": False, "status": "disabled"}
        result["ai_analysis"] = analysis
        _cache_report_result(report_id, result)
        return analysis

    timeout_seconds = _ai_timeout_seconds(ai_config)
    running = {
        "enabled": True,
        "status": "running",
        "entity_id": str(ai_config.get("entity_id") or "").strip() or None,
        "mode": "no_thinking_expected",
        "mode_control": "ai_task_entity_configuration",
        "timeout_seconds": timeout_seconds,
        "started_at_epoch": time.time(),
    }
    result["ai_analysis"] = running
    _cache_report_result(report_id, result)

    box = {}
    done = threading.Event()

    def worker():
        try:
            box["analysis"] = analyze_report_with_ai(
                result,
                ai_config,
                token=TOKEN,
            )
        except Exception as exc:
            box["analysis"] = {
                **running,
                "status": "error",
                "finished_at_epoch": time.time(),
                "error": str(exc),
            }
        finally:
            done.set()

    started = time.time()
    threading.Thread(target=worker, daemon=True, name=f"ha-report-ai-{report_id}").start()
    if not done.wait(timeout_seconds + AI_HARD_TIMEOUT_GRACE_SECONDS):
        analysis = {
            **running,
            "status": "error",
            "finished_at_epoch": time.time(),
            "duration_seconds": time.time() - started,
            "error": f"Analyse IA interrompue après {timeout_seconds} s (délai maximal configuré).",
        }
    else:
        analysis = box.get("analysis") or {
            **running,
            "status": "error",
            "finished_at_epoch": time.time(),
            "error": "Analyse IA terminée sans résultat.",
        }

    result["ai_analysis"] = analysis
    result["execution"]["ai_analysis_duration_seconds"] = float(analysis.get("duration_seconds") or 0.0)
    result["execution"]["ai_analysis_finished_at_epoch"] = time.time()
    _cache_report_result(report_id, result)
    return analysis


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

    def path_parts_after_report(self, path):
        tail = path.split("/api/report/", 1)[1]
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
            if path.endswith("/api/reports"):
                return self.send_payload(200, {"reports": list_reports()})
            if path.endswith("/api/timezone"):
                return self.send_payload(200, {"timezone": home_assistant_timezone()})
            if "/api/report/" in path and path.endswith("/html"):
                parts = self.path_parts_after_report(path)
                if len(parts) == 2 and parts[1] == "html":
                    rendered_result = _cached_report_result(parts[0]) or execute_report(parts[0])
                    rendered = render_report_html(rendered_result).encode("utf-8")
                    return self.send_payload(200, rendered, "text/html; charset=utf-8")
            if "/api/report/" in path:
                parts = self.path_parts_after_report(path)
                return self.send_payload(200, {"report": report_summary(load_report(parts[0]))})
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
            if path.endswith("/api/data/analyze-device"):
                return self.send_payload(200, {"result": analyze_complete_device(payload)})
            if path.endswith("/api/reports"):
                return self.send_payload(200, {"report": create_report(payload)})
            if "/api/report/" in path and path.endswith("/preview"):
                parts = self.path_parts_after_report(path)
                return self.send_payload(200, {"plan": build_report_plan(parts[0])})
            if "/api/report/" in path and path.endswith("/ai-analysis"):
                parts = self.path_parts_after_report(path)
                return self.send_payload(200, {"ai_analysis": execute_ai_analysis(parts[0])})
            if "/api/report/" in path and path.endswith("/execute"):
                parts = self.path_parts_after_report(path)
                return self.send_payload(200, {"result": execute_report(parts[0])})
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
            if "/api/report/" in path:
                parts = self.path_parts_after_report(path)
                if len(parts) == 1:
                    return self.send_payload(200, {"report": update_report(parts[0], payload)})
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
            if "/api/report/" in path:
                parts = self.path_parts_after_report(path)
                if len(parts) == 1:
                    return self.send_payload(200, delete_report(parts[0]))
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


def main():
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Starting HA Reporting catalog manager on port %d", PORT)
    try:
        log.info("Home Assistant API connection successful: %d entities", len(home_assistant_states()))
    except Exception as exc:
        log.error("Home Assistant API initial check failed: %s", exc)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
