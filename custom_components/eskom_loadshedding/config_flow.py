"""Adds config flow for the Eskom Loadshedding Interface."""
from collections import OrderedDict

from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

from .const import (  # pylint: disable=unused-import
    CONF_SCAN_PERIOD,
    DEFAULT_SCAN_PERIOD,
    DOMAIN,
    MIN_SCAN_PERIOD,
    PLATFORMS,
)


class EskomFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Eskom Loadshedding Interface."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(
        self, user_input=None  # pylint: disable=bad-continuation
    ):
        """Handle a flow initialized by the user."""
        self._errors = {}

        return self.async_create_entry(title="Home", data={},)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EskomOptionsFlowHandler(config_entry)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form."""
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({}), errors=self._errors,
        )


class EskomOptionsFlowHandler(config_entries.OptionsFlow):
    """Eskom config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            # Set a minimum scan period
            if int(user_input[CONF_SCAN_PERIOD]) >= MIN_SCAN_PERIOD:
                self.options.update(user_input)
                return await self._update_options()
            else:
                self.options[CONF_SCAN_PERIOD] = MIN_SCAN_PERIOD
                return await self._update_options()

        data_schema = OrderedDict()
        data_schema[
            vol.Optional(
                CONF_SCAN_PERIOD,
                default=self.options.get(CONF_SCAN_PERIOD, DEFAULT_SCAN_PERIOD),
            )
        ] = int

        for x in sorted(PLATFORMS):
            data_schema[vol.Required(x, default=self.options.get(x, True))] = bool

        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema))

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(title="Home", data=self.options)
