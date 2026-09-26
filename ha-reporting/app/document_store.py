from __future__ import annotations

import json
import os
import re
import shutil
import threading
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DOCUMENT_DIR = Path("/config/documents")
DEFAULT_FILENAME_TEMPLATE = "{report_id}_{period_start}_{period_end}"
DEFAULT_DUPLICATE_POLICY = "version"
VALID_DUPLICATE_POLICIES = {"version", "overwrite", "fail"}
_FILENAME_FORBIDDEN_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_TEMPLATE_FIELD_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")
_LOCK = threading.RLock()

SUPPORTED_TEMPLATE_FIELDS = {
    "report_id",
    "report_name",
    "year",
    "month",
    "day",
    "period_start",
    "period_end",
    "period_type",
    "generated_date",
    "generated_datetime",
    "comparison",
}


def validate_output_config(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    template = str(raw.get("filename_template") or DEFAULT_FILENAME_TEMPLATE).strip()
    if not template:
        template = DEFAULT_FILENAME_TEMPLATE

    fields = set(_TEMPLATE_FIELD_RE.findall(template))
    unknown = sorted(fields - SUPPORTED_TEMPLATE_FIELDS)
    if unknown:
        raise ValueError(f"Variable(s) de nom de fichier inconnue(s): {', '.join(unknown)}")
    try:
        template.format_map({field: field for field in SUPPORTED_TEMPLATE_FIELDS})
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Modèle de nom de fichier invalide: {exc}") from exc

    policy = str(raw.get("duplicate_policy") or DEFAULT_DUPLICATE_POLICY).strip().lower()
    if policy not in VALID_DUPLICATE_POLICIES:
        raise ValueError("Politique de doublon invalide (version, overwrite ou fail)")

    return {
        "filename_template": template,
        "duplicate_policy": policy,
        "format": "pdf",
        "local_storage": True,
    }


def _dt(value: Any, timezone_name: str | None = None) -> datetime:
    timezone = ZoneInfo(timezone_name) if timezone_name else None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone)
    if isinstance(value, str) and value:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None and timezone:
            parsed = parsed.replace(tzinfo=timezone)
        return parsed
    return datetime.now(timezone)


def _comparison_token(report: dict[str, Any]) -> str:
    comparisons = report.get("comparisons") or {}
    bits = []
    previous_periods = int(comparisons.get("previous_periods") or 0)
    previous_years = int(comparisons.get("previous_years") or 0)
    if previous_periods:
        bits.append(f"N-{previous_periods}p")
    if previous_years:
        bits.append(f"N-{previous_years}a")
    return "_".join(bits) or "none"


def filename_context(report: dict[str, Any], resolved_period: dict[str, Any], generated_at: datetime | None = None) -> dict[str, str]:
    timezone_name = str(resolved_period.get("timezone") or "UTC")
    generated_at = generated_at or datetime.now(ZoneInfo(timezone_name))
    start = _dt(resolved_period.get("start") or resolved_period.get("start_epoch"), timezone_name)
    end = _dt(resolved_period.get("end") or resolved_period.get("end_epoch"), timezone_name)
    period_spec = report.get("period") or {}

    return {
        "report_id": str(report.get("id") or "report"),
        "report_name": str(report.get("name") or report.get("id") or "report"),
        "year": f"{start.year:04d}",
        "month": f"{start.month:02d}",
        "day": f"{start.day:02d}",
        "period_start": start.strftime("%Y-%m-%d"),
        "period_end": end.strftime("%Y-%m-%d"),
        "period_type": str(period_spec.get("type") or "custom"),
        "generated_date": generated_at.strftime("%Y-%m-%d"),
        "generated_datetime": generated_at.strftime("%Y-%m-%d_%H-%M-%S"),
        "comparison": _comparison_token(report),
    }


def sanitize_filename(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).strip()
    value = _FILENAME_FORBIDDEN_RE.sub("_", value)
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"_+", "_", value)
    value = value.strip(" ._")
    if not value:
        value = "rapport"
    if len(value) > 180:
        value = value[:180].rstrip(" ._")
    if not value.lower().endswith(".pdf"):
        value += ".pdf"
    return value


def render_filename(report: dict[str, Any], resolved_period: dict[str, Any], output_config: dict[str, Any] | None = None, generated_at: datetime | None = None) -> str:
    config = validate_output_config(output_config)
    context = filename_context(report, resolved_period, generated_at)
    try:
        rendered = config["filename_template"].format_map(context)
    except KeyError as exc:
        raise ValueError(f"Variable de nom de fichier inconnue: {exc.args[0]}") from exc
    return sanitize_filename(rendered)


def _manifest_path(document_id: str) -> Path:
    return DOCUMENT_DIR / f"{document_id}.json"


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_documents() -> list[dict[str, Any]]:
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    output = []
    for path in DOCUMENT_DIR.glob("*.json"):
        try:
            manifest = _load_manifest(path)
            pdf_path = DOCUMENT_DIR / str(manifest.get("stored_name") or "")
            if pdf_path.is_file():
                manifest["size_bytes"] = pdf_path.stat().st_size
                output.append(manifest)
        except Exception:
            continue
    output.sort(key=lambda item: float(item.get("generated_at_epoch") or 0), reverse=True)
    return output


def get_document(document_id: str) -> dict[str, Any]:
    path = _manifest_path(document_id)
    if not path.is_file():
        raise FileNotFoundError(f"Document introuvable: {document_id}")
    manifest = _load_manifest(path)
    pdf_path = DOCUMENT_DIR / str(manifest.get("stored_name") or "")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Fichier PDF introuvable pour le document: {document_id}")
    manifest["size_bytes"] = pdf_path.stat().st_size
    manifest["path"] = str(pdf_path)
    return manifest


def _existing_by_filename(filename: str) -> dict[str, Any] | None:
    for manifest in list_documents():
        if manifest.get("filename") == filename:
            return manifest
    return None


def _versioned_filename(filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".pdf"
    existing = {item.get("filename") for item in list_documents()}
    if filename not in existing:
        return filename
    index = 2
    while True:
        candidate = f"{stem}_{index}{suffix}"
        if candidate not in existing:
            return candidate
        index += 1


def register_pdf(temp_pdf: Path, *, filename: str, report_id: str, report_name: str, resolved_period: dict[str, Any], output_config: dict[str, Any], generated_at: datetime, pdf_theme: str = "dark") -> dict[str, Any]:
    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
    config = validate_output_config(output_config)
    filename = sanitize_filename(filename)

    with _LOCK:
        existing = _existing_by_filename(filename)
        policy = config["duplicate_policy"]
        if existing:
            if policy == "fail":
                raise FileExistsError(f"Le document '{filename}' existe déjà")
            if policy == "version":
                filename = _versioned_filename(filename)
            elif policy == "overwrite":
                delete_document(str(existing["id"]))

        document_id = f"{generated_at.strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:10]}"
        stored_name = f"{document_id}.pdf"
        target = DOCUMENT_DIR / stored_name
        shutil.move(str(temp_pdf), target)

        manifest = {
            "document_version": 1,
            "id": document_id,
            "report_id": report_id,
            "report_name": report_name,
            "filename": filename,
            "stored_name": stored_name,
            "generated_at": generated_at.isoformat(),
            "generated_at_epoch": generated_at.timestamp(),
            "period": resolved_period,
            "pdf": {"status": "completed", "theme": "light" if pdf_theme == "light" else "dark"},
            "size_bytes": target.stat().st_size,
            "output": config,
            "exports": {},
        }
        _manifest_path(document_id).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest


def delete_document(document_id: str) -> dict[str, Any]:
    with _LOCK:
        manifest = get_document(document_id)
        pdf_path = DOCUMENT_DIR / str(manifest.get("stored_name") or "")
        manifest_path = _manifest_path(document_id)
        if pdf_path.exists():
            pdf_path.unlink()
        if manifest_path.exists():
            manifest_path.unlink()
        return {"ok": True, "document_id": document_id, "filename": manifest.get("filename")}
