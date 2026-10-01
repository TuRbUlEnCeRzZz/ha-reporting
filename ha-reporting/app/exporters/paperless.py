from __future__ import annotations

import json
import mimetypes
import os
import shutil
import threading
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import ExportProvider, ExportProviderError


USER_AGENT = "HA-Reporting/0.2.0-rc.4"
SHARE_ROOT = Path("/share")
_CONSUME_COPY_LOCK = threading.Lock()


class PaperlessExportProvider(ExportProvider):
    provider_id = "paperless"
    name = "Paperless-ngx"

    def __init__(
        self,
        base_url: str = "",
        token: str = "",
        timeout_seconds: int = 30,
        *,
        mode: str = "api",
        consume_path: str = "",
        share_root: Path | str | None = None,
    ):
        self.base_url = str(base_url or "").strip().rstrip("/")
        self.token = str(token or "").strip()
        self.timeout_seconds = int(timeout_seconds or 30)
        self.mode = str(mode or "consume_folder").strip().lower()
        self.consume_path = str(consume_path or "").strip()
        self.share_root = Path(share_root) if share_root is not None else SHARE_ROOT

    @property
    def configured(self) -> bool:
        if self.mode == "consume_folder":
            return bool(self.consume_path)
        if self.mode == "api":
            return bool(self.base_url and self.token)
        return False

    @property
    def capabilities(self) -> dict[str, bool]:
        caps = super().capabilities.copy()
        caps["consume_folder"] = True
        caps["api"] = True
        caps["tokenless_consume"] = True
        return caps

    def _ensure_mode(self) -> None:
        if self.mode not in {"consume_folder", "api"}:
            raise ExportProviderError(f"Mode Paperless-ngx inconnu: {self.mode}")

    def _ensure_api_configured(self) -> None:
        self._ensure_mode()
        if not self.base_url:
            raise ExportProviderError("URL Paperless-ngx non configurée")
        if not self.token:
            raise ExportProviderError("Token API Paperless-ngx non configuré")
        if not (self.base_url.startswith("http://") or self.base_url.startswith("https://")):
            raise ExportProviderError("L'URL Paperless-ngx doit commencer par http:// ou https://")

    def _consume_directory(self, *, require_writable: bool = True) -> Path:
        self._ensure_mode()
        if not self.consume_path:
            raise ExportProviderError("Dossier consume Paperless-ngx non configuré")

        root = self.share_root.resolve()
        raw = Path(self.consume_path)
        candidate = raw if raw.is_absolute() else root / raw
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root)
        except (ValueError, OSError) as exc:
            raise ExportProviderError(f"Le dossier consume doit se trouver sous {root}") from exc

        if not resolved.exists():
            raise ExportProviderError(f"Dossier consume introuvable: {resolved}")
        if not resolved.is_dir():
            raise ExportProviderError(f"Le chemin consume n'est pas un dossier: {resolved}")
        if require_writable and not os.access(resolved, os.W_OK):
            raise ExportProviderError(f"Dossier consume non accessible en écriture: {resolved}")
        return resolved

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Token {self.token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    @staticmethod
    def _decode_response(raw: bytes, status: int) -> Any:
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return {"status_code": status}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def _open(self, request: urllib.request.Request) -> tuple[int, Any]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                status = int(getattr(response, "status", 200))
                body = self._decode_response(response.read(), status)
                return status, body
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            if len(detail) > 500:
                detail = detail[:500] + "…"
            raise ExportProviderError(f"Paperless HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ExportProviderError(f"Connexion Paperless impossible: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ExportProviderError("Délai de connexion Paperless dépassé") from exc

    @staticmethod
    def _safe_filename(filename: str) -> str:
        filename = str(filename or "").strip()
        if not filename or filename in {".", ".."} or Path(filename).name != filename:
            raise ExportProviderError("Nom de fichier Paperless invalide")
        return filename

    @staticmethod
    def _available_target(directory: Path, filename: str) -> Path:
        requested = directory / filename
        if not requested.exists():
            return requested
        stem = requested.stem
        suffix = requested.suffix
        index = 2
        while True:
            candidate = directory / f"{stem}_{index}{suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    def _test_consume_folder(self) -> dict[str, Any]:
        directory = self._consume_directory()
        # Test create/delete permissions without dropping a consumable file that
        # Paperless could try to ingest while the connection test is running.
        probe = directory / f".ha-reporting-write-test-{uuid.uuid4().hex}"
        try:
            probe.mkdir()
            probe.rmdir()
        except OSError as exc:
            try:
                probe.rmdir()
            except OSError:
                pass
            raise ExportProviderError(f"Écriture impossible dans le dossier consume: {exc}") from exc
        return {
            "provider": self.provider_id,
            "name": self.name,
            "mode": "consume_folder",
            "configured": True,
            "reachable": True,
            "consume_path": str(directory),
            "message": "Dossier consume Paperless-ngx accessible en écriture",
        }

    def _test_api(self) -> dict[str, Any]:
        self._ensure_api_configured()
        url = f"{self.base_url}/api/documents/?page_size=1"
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        status, body = self._open(request)
        if status < 200 or status >= 300:
            raise ExportProviderError(f"Paperless a répondu HTTP {status}")
        return {
            "provider": self.provider_id,
            "name": self.name,
            "mode": "api",
            "configured": True,
            "reachable": True,
            "status_code": status,
            "message": "Connexion API Paperless-ngx réussie",
            "response_type": type(body).__name__,
        }

    def test_connection(self) -> dict[str, Any]:
        self._ensure_mode()
        if self.mode == "consume_folder":
            return self._test_consume_folder()
        return self._test_api()

    @staticmethod
    def _multipart(document_path: Path, filename: str) -> tuple[bytes, str]:
        boundary = f"ha-reporting-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(filename)[0] or "application/pdf"
        payload = document_path.read_bytes()
        safe_filename = str(filename).replace('"', "_")
        chunks = [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="document"; filename="{safe_filename}"\r\n'.encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            payload,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    def _export_consume(self, document_path: Path, filename: str) -> dict[str, Any]:
        directory = self._consume_directory()
        filename = self._safe_filename(filename)
        document_path = Path(document_path)
        if not document_path.is_file():
            raise ExportProviderError("Le PDF local à exporter est introuvable")

        with _CONSUME_COPY_LOCK:
            target = self._available_target(directory, filename)
            temp = directory / f".ha-reporting-{uuid.uuid4().hex}.part"
            try:
                with document_path.open("rb") as source, temp.open("xb") as destination:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
                    destination.flush()
                    os.fsync(destination.fileno())
                os.replace(temp, target)
            except OSError as exc:
                try:
                    temp.unlink(missing_ok=True)
                except OSError:
                    pass
                raise ExportProviderError(f"Copie vers le dossier consume impossible: {exc}") from exc

        return {
            "provider": self.provider_id,
            "name": self.name,
            "mode": "consume_folder",
            "status": "completed",
            "delivery_status": "deposited",
            "filename": target.name,
            "target_path": str(target),
            "remote_reference": None,
            "message": "PDF déposé dans le dossier consume Paperless-ngx",
        }

    def _export_api(self, document_path: Path, filename: str) -> dict[str, Any]:
        self._ensure_api_configured()
        document_path = Path(document_path)
        filename = self._safe_filename(filename)
        if not document_path.is_file():
            raise ExportProviderError("Le PDF local à exporter est introuvable")
        body, content_type = self._multipart(document_path, filename)
        request = urllib.request.Request(
            f"{self.base_url}/api/documents/post_document/",
            data=body,
            headers=self._headers(content_type),
            method="POST",
        )
        status, response = self._open(request)
        if status < 200 or status >= 300:
            raise ExportProviderError(f"Paperless a répondu HTTP {status}")

        remote_reference = None
        if isinstance(response, dict):
            remote_reference = response.get("task_id") or response.get("id") or response.get("task")
        elif isinstance(response, str):
            remote_reference = response.strip('"') or None

        return {
            "provider": self.provider_id,
            "name": self.name,
            "mode": "api",
            "status": "completed",
            "status_code": status,
            "filename": filename,
            "remote_reference": remote_reference,
            "response": response,
            "message": "PDF envoyé via l'API Paperless-ngx",
        }

    def export(self, document_path: Path, filename: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_mode()
        if self.mode == "consume_folder":
            return self._export_consume(document_path, filename)
        return self._export_api(document_path, filename)
