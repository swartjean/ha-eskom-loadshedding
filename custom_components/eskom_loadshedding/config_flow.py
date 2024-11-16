"""Adds config flow for the Eskom Loadshedding Interface."""

from collections import OrderedDict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import selector

from .const import (  # pylint: disable=unused-import
    CONF_API_KEY,
    CONF_SCAN_PERIOD,
    DEFAULT_SCAN_PERIOD,
    DOMAIN,
    MIN_SCAN_PERIOD,
    PLATFORMS,
)
from .eskom_interface import EskomInterface


class EskomFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Eskom Loadshedding Interface."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        self._errors = {}

        if user_input is not None:
            # Validate the API key passed in by the user
            valid = await self.validate_key(user_input[CONF_API_KEY])
            if valid:
                # Store info to use in next step
                self.api_key = user_input[CONF_API_KEY]

                # Proceed to the next configuration step
                return await self.async_step_area_search()

            self._errors["base"] = "auth"

            return await self._show_user_config_form(user_input)

        user_input = {}
        user_input[CONF_API_KEY] = ""

        return await self._show_user_config_form(user_input)

    async def async_step_area_search(self, user_input=None):
        """Collect area search information from the user"""
        self._errors = {}

        if user_input is not None:
            # Perform an area search using the user input and check whether any matches were found
            areas = await self.search_area(user_input["area_search"])

            if areas:
                # Store the areas for use in the next step
                self.area_list = areas["areas"]

                if self.area_list:
                    return await self.async_step_area_selection()

            self._errors["base"] = "bad_area"

            return await self._show_area_config_form(user_input)

        user_input = {}
        user_input["area_search"] = ""

        return await self._show_area_config_form(user_input)

    async def async_step_area_selection(self, user_input=None):
        """Collect an area selection from the user"""
        self._errors = {}

        if user_input is not None:
            if "area_selection" in user_input:
                # Create the entry, saving the API key and area ID
                return self.async_create_entry(
                    title="Loadshedding Status",
                    data={
                        "area_id": user_input["area_selection"],
                    },
                    options={
                        CONF_API_KEY: self.api_key,
                    },
                )
            self._errors["base"] = "no_area_selection"

        # Reformat the areas as label/value pairs for the selector
        area_options = [
            {"label": f"{item['name']} - {item['region']}", "value": item["id"]}
            for item in self.area_list
        ]

        data_schema = {}
        data_schema["area_selection"] = selector(
            {"select": {"options": area_options, "mode": "dropdown"}}
        )
        return self.async_show_form(
            step_id="area_selection",
            data_schema=vol.Schema(data_schema),
            errors=self._errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EskomOptionsFlowHandler(config_entry)

    async def _show_user_config_form(self, user_input):
        """Show the configuration form."""
        data_schema = {
            vol.Required(CONF_API_KEY, default=user_input[CONF_API_KEY]): str
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

    async def _show_area_config_form(self, user_input):
        """Show the configuration form."""
        data_schema = {
            vol.Required("area_search", default=user_input["area_search"]): str
        }

        return self.async_show_form(
            step_id="area_search",
            data_schema=vol.Schema(data_schema),
            errors=self._errors,
        )

    async def validate_key(self, api_key: str) -> bool:
        """Validates an EskomSePush API token."""
        # Perform an api allowance check using the provided token
        try:
            session = async_create_clientsession(self.hass)
            interface = EskomInterface(session=session, api_key=api_key)
            data = await interface.async_query_api("/api_allowance")
            if "error" in data:
                return False
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False

    async def search_area(self, area_search: str) -> dict:
        """Performs an area search using the EskomSePush API"""
        session = async_create_clientsession(self.hass)
        interface = EskomInterface(session=session, api_key=self.api_key)
        return await interface.async_search_areas(area_search)


class EskomOptionsFlowHandler(config_entries.OptionsFlow):
    """Eskom config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self._errors = {}
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            # Validate the API key
            valid = await self.validate_key(user_input[CONF_API_KEY])
            if valid:
                # Set a minimum scan period
                if int(user_input[CONF_SCAN_PERIOD]) < MIN_SCAN_PERIOD:
                    user_input[CONF_SCAN_PERIOD] = MIN_SCAN_PERIOD

                # Update all options
                self.options.update(user_input)
                return await self._update_options()
            self._errors["base"] = "auth"

        data_schema = OrderedDict()
        data_schema[
            vol.Optional(
                CONF_SCAN_PERIOD,
                default=self.options.get(CONF_SCAN_PERIOD, DEFAULT_SCAN_PERIOD),
            )
        ] = int

        data_schema[
            vol.Optional(
                CONF_API_KEY,
                default=self.options.get(CONF_API_KEY, self.options.get(CONF_API_KEY)),
            )
        ] = str

        for x in sorted(PLATFORMS):
            data_schema[vol.Required(x, default=self.options.get(x, True))] = bool

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(title="Home", data=self.options)

    async def validate_key(self, api_key: str) -> bool:
        """Validates an EskomSePush API token."""
        # Perform an api allowance check using the provided token
        try:
            session = async_create_clientsession(self.hass)
            interface = EskomInterface(session=session, api_key=api_key)
            data = await interface.async_query_api("/api_allowance")

            if "error" in data:
                return False
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False
