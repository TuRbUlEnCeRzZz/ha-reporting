from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class ExportProviderError(RuntimeError):
    """Raised when a destination cannot accept an export."""


class ExportProvider(ABC):
    """Destination-independent contract for exporting a locally stored report."""

    provider_id = "base"
    name = "Export provider"

    @property
    def capabilities(self) -> dict[str, bool]:
        return {
            "manual_export": True,
            "connection_test": True,
            "custom_filename": True,
            "automatic_export": False,
        }

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def export(self, document_path: Path, filename: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError
