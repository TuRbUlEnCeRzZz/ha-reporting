from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .paperless import PaperlessExportProvider

EXPORT_PROVIDER_FILE = Path("/config/export_providers.yaml")
PAPERLESS_MODES = {"consume_folder", "api"}


def _clean_url(value: Any) -> str:
    url = str(value or "").strip().rstrip("/")
    if url and not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("L'URL doit commencer par http:// ou https://")
    return url


def _clean_mode(value: Any) -> str:
    mode = str(value or "consume_folder").strip().lower()
    if mode not in PAPERLESS_MODES:
        raise ValueError(f"Mode Paperless-ngx invalide: {mode}")
    return mode


def load_export_provider_config() -> dict[str, Any]:
    if EXPORT_PROVIDER_FILE.exists():
        raw = yaml.safe_load(EXPORT_PROVIDER_FILE.read_text(encoding="utf-8")) or {}
    else:
        raw = {}
    paperless = raw.setdefault("paperless", {})
    # Backward compatibility with the first beta.11 build: an existing URL+token
    # configuration remains in API mode. New configurations default to consume.
    if "mode" not in paperless:
        paperless["mode"] = "api" if paperless.get("url") and paperless.get("token") else "consume_folder"
    paperless.setdefault("consume_path", "")
    paperless.setdefault("url", "")
    paperless.setdefault("token", "")
    paperless.setdefault("filename_template", "")
    return raw


def save_paperless_config(payload: dict[str, Any]) -> dict[str, Any]:
    config = load_export_provider_config()
    current = config.get("paperless") or {}
    mode = _clean_mode(payload.get("mode", current.get("mode", "consume_folder")))
    consume_path = str(payload.get("consume_path", current.get("consume_path", "")) or "").strip()
    url = _clean_url(payload.get("url", current.get("url", "")))
    token_input = payload.get("token", None)
    token = str(current.get("token") or "") if token_input is None or str(token_input).strip() == "" else str(token_input).strip()
    filename_template = str(payload.get("filename_template", current.get("filename_template", "")) or "").strip()

    # Reuse HA Reporting's filename-template validation. Blank means "use local filename".
    if filename_template:
        from document_store import validate_output_config
        validate_output_config({"filename_template": filename_template, "duplicate_policy": "version"})

    config["paperless"] = {
        "mode": mode,
        "consume_path": consume_path,
        "url": url,
        "token": token,
        "filename_template": filename_template,
    }
    EXPORT_PROVIDER_FILE.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PROVIDER_FILE.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return paperless_overview(config["paperless"])


def paperless_provider(override: dict[str, Any] | None = None) -> PaperlessExportProvider:
    stored = (load_export_provider_config().get("paperless") or {}).copy()
    override = override or {}
    if "mode" in override and str(override.get("mode") or "").strip():
        stored["mode"] = _clean_mode(override.get("mode"))
    if "consume_path" in override:
        stored["consume_path"] = str(override.get("consume_path") or "").strip()
    if "url" in override and str(override.get("url") or "").strip():
        stored["url"] = _clean_url(override.get("url"))
    if "token" in override and str(override.get("token") or "").strip():
        stored["token"] = str(override.get("token") or "").strip()
    return PaperlessExportProvider(
        stored.get("url", ""),
        stored.get("token", ""),
        mode=stored.get("mode", "consume_folder"),
        consume_path=stored.get("consume_path", ""),
    )


def paperless_overview(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or (load_export_provider_config().get("paperless") or {})
    token = str(config.get("token") or "")
    url = str(config.get("url") or "")
    mode = _clean_mode(config.get("mode", "consume_folder"))
    consume_path = str(config.get("consume_path") or "")
    provider = PaperlessExportProvider(url, token, mode=mode, consume_path=consume_path)
    return {
        "id": "paperless",
        "name": "Paperless-ngx",
        "mode": mode,
        "recommended_mode": "consume_folder",
        "available_modes": ["consume_folder", "api"],
        "consume_path": consume_path,
        "url": url,
        "configured": provider.configured,
        "token_configured": bool(token),
        "filename_template": str(config.get("filename_template") or ""),
        "capabilities": provider.capabilities,
    }


def export_provider_overview() -> dict[str, Any]:
    return {"providers": [paperless_overview()]}


def resolve_export_provider(provider_id: str):
    provider_id = str(provider_id or "").strip().lower()
    if provider_id == "paperless":
        return paperless_provider()
    raise ValueError(f"Destination d'export inconnue: {provider_id}")
