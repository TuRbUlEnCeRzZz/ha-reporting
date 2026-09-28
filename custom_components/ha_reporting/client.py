"""Local API client for the HA Reporting add-on."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientResponseError, ClientSession


class HaReportingApiError(Exception):
    """Raised when the HA Reporting add-on API cannot be used."""


class HaReportingClient:
    """Small async client for the add-on automation API."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")

    async def async_health(self) -> None:
        try:
            async with self._session.get(
                f"{self.base_url}/api/automation/report-jobs", timeout=10
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except Exception as exc:
            raise HaReportingApiError(str(exc)) from exc
        if not isinstance(payload, dict) or "jobs" not in payload:
            raise HaReportingApiError("Réponse inattendue de HA Reporting")

    async def async_run_report(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            async with self._session.post(
                f"{self.base_url}/api/automation/report-jobs",
                json=data,
                timeout=15,
            ) as response:
                response.raise_for_status()
                payload = await response.json()
        except ClientResponseError as exc:
            raise HaReportingApiError(
                f"HA Reporting HTTP {exc.status}: {exc.message}"
            ) from exc
        except Exception as exc:
            raise HaReportingApiError(str(exc)) from exc
        job = payload.get("job") if isinstance(payload, dict) else None
        if not isinstance(job, dict) or not job.get("id"):
            raise HaReportingApiError("HA Reporting n'a pas renvoyé de job valide")
        return job
