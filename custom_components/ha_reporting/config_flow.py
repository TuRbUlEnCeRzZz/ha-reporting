"""Config flow for HA Reporting."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import HaReportingApiError, HaReportingClient
from .const import CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN


class HaReportingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure the local HA Reporting add-on API."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            base_url = str(user_input[CONF_BASE_URL]).strip().rstrip("/")
            client = HaReportingClient(async_get_clientsession(self.hass), base_url)
            try:
                await client.async_health()
            except HaReportingApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id("ha_reporting_local")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="HA Reporting",
                    data={CONF_BASE_URL: base_url},
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BASE_URL,
                    default=(user_input or {}).get(CONF_BASE_URL, DEFAULT_BASE_URL),
                ): str
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
