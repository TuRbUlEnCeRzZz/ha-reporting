"""HA Reporting companion integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import HaReportingApiError, HaReportingClient
from .const import CONF_BASE_URL, DOMAIN, SERVICE_RUN_REPORT

CONF_REPORT_ID = "report_id"
CONF_AI_ANALYSIS = "ai_analysis"
CONF_GENERATE_PDF = "generate_pdf"
CONF_THEME = "theme"
CONF_DESTINATIONS = "destinations"

RUN_REPORT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REPORT_ID): cv.string,
        vol.Optional(CONF_AI_ANALYSIS): cv.boolean,
        vol.Optional(CONF_GENERATE_PDF, default=True): cv.boolean,
        vol.Optional(CONF_THEME, default="dark"): vol.In(["dark", "light"]),
        vol.Optional(CONF_DESTINATIONS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


def _loaded_client(hass: HomeAssistant) -> HaReportingClient:
    clients: dict[str, HaReportingClient] = hass.data.get(DOMAIN, {}).get("clients", {})
    for entry_id, client in clients.items():
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.state is ConfigEntryState.LOADED:
            return client
    raise ServiceValidationError(
        "HA Reporting n'est pas configuré ou l'intégration n'est pas chargée"
    )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register HA Reporting actions independently of config-entry loading."""
    hass.data.setdefault(DOMAIN, {}).setdefault("clients", {})

    async def async_run_report(call: ServiceCall) -> dict[str, Any] | None:
        client = _loaded_client(hass)
        payload: dict[str, Any] = {
            CONF_REPORT_ID: call.data[CONF_REPORT_ID],
            CONF_GENERATE_PDF: call.data[CONF_GENERATE_PDF],
            CONF_THEME: call.data[CONF_THEME],
            CONF_DESTINATIONS: list(call.data[CONF_DESTINATIONS]),
        }
        if CONF_AI_ANALYSIS in call.data:
            payload[CONF_AI_ANALYSIS] = call.data[CONF_AI_ANALYSIS]
        try:
            job = await client.async_run_report(payload)
        except HaReportingApiError as exc:
            raise ServiceValidationError(str(exc)) from exc

        response = {
            "job_id": job.get("id"),
            "status": job.get("status"),
            "deduplicated": bool(job.get("deduplicated")),
            "report_id": job.get("report_id"),
        }
        return response if call.return_response else None

    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_REPORT,
        async_run_report,
        schema=RUN_REPORT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one HA Reporting add-on endpoint."""
    session = async_get_clientsession(hass)
    client = HaReportingClient(session, entry.data[CONF_BASE_URL])
    try:
        await client.async_health()
    except HaReportingApiError as exc:
        raise ConfigEntryNotReady(str(exc)) from exc
    hass.data.setdefault(DOMAIN, {}).setdefault("clients", {})[entry.entry_id] = client
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HA Reporting endpoint."""
    hass.data.get(DOMAIN, {}).get("clients", {}).pop(entry.entry_id, None)
    return True
