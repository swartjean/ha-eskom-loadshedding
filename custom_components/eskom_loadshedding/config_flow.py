"""Adds config flow for the Eskom Loadshedding Interface."""

from collections import OrderedDict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import selector

from .const import (  # pylint: disable=unused-import
    CONF_API_KEY,
    CONF_AREA_ID,
    CONF_AREA_NAME,
    CONF_AREA_REGION,
    CONF_SCAN_PERIOD,
    CONF_SCHEDULE_ID,
    DEFAULT_SCAN_PERIOD,
    DOMAIN,
    MIN_SCAN_PERIOD,
    PLATFORMS,
)
from .eskom_interface import EskomInterface
from .esp_normalizers import EskomAuthError


def _area_choice_label(item: dict) -> str:
    """Formats an areas_search result for the selection dropdown."""
    parts = [part for part in (item.get("municipality"), item.get("province")) if part]
    suffix = f" - {', '.join(parts)}" if parts else ""
    return f"{item.get('name', item['id'])}{suffix}"


def _pick_schedule_id(area: dict) -> str:
    """Picks the loadshedding schedule id from a v3 /area response.

    Prefers the auto_enabled schedule, then the first loadshedding-type
    schedule, then the first schedule of any type.
    """
    schedules = [s for s in area.get("schedules") or [] if isinstance(s, dict)]
    for schedule in schedules:
        if schedule.get("auto_enabled"):
            return schedule.get("id", "")
    for schedule in schedules:
        if schedule.get("type") == "loadshedding":
            return schedule.get("id", "")
    return schedules[0].get("id", "") if schedules else ""


def _area_entry_data(area: dict) -> dict:
    """Builds the config entry data block from a v3 /area response."""
    region = ", ".join(
        part
        for part in (area.get("municipality", ""), area.get("province", ""))
        if part
    )
    return {
        CONF_AREA_ID: area.get("id", ""),
        CONF_SCHEDULE_ID: _pick_schedule_id(area),
        CONF_AREA_NAME: area.get("name", ""),
        CONF_AREA_REGION: region,
    }


async def _validate_key(hass, api_key: str):
    """Validates an EskomSePush API token via /status (1 credit).

    Returns None when accepted, "auth" for a rejected key, or
    "cannot_connect" for failures that say nothing about the key
    (quota exhaustion, network problems).
    """
    session = async_create_clientsession(hass)
    interface = EskomInterface(session=session, api_key=api_key)
    try:
        await interface.async_query_api("/status")
    except EskomAuthError:
        return "auth"
    except Exception:  # pylint: disable=broad-except
        return "cannot_connect"
    return None


async def _search_areas(hass, api_key: str, area_search: str):
    """Performs an area search, returning None on any failure."""
    try:
        session = async_create_clientsession(hass)
        interface = EskomInterface(session=session, api_key=api_key)
        return await interface.async_search_areas(area_search)
    except Exception:  # pylint: disable=broad-except
        return None


async def _get_area(hass, api_key: str, area_id: str):
    """Fetches area metadata for a selected area, returning None on failure."""
    try:
        session = async_create_clientsession(hass)
        interface = EskomInterface(session=session, api_key=api_key)
        return await interface.async_get_area(area_id)
    except Exception:  # pylint: disable=broad-except
        return None


class EskomFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Eskom Loadshedding Interface."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self.api_key = ""
        self.area_list = []

    async def async_step_user(self, user_input=None):
        self._errors = {}

        if user_input is not None:
            # Validate the API key passed in by the user
            error = await _validate_key(self.hass, user_input[CONF_API_KEY])
            if error is None:
                # Store info to use in next step
                self.api_key = user_input[CONF_API_KEY]

                # Proceed to the next configuration step
                return await self.async_step_area_search()

            self._errors["base"] = error

            return await self._show_user_config_form(user_input)

        user_input = {}
        user_input[CONF_API_KEY] = ""

        return await self._show_user_config_form(user_input)

    async def async_step_area_search(self, user_input=None):
        """Collect area search information from the user"""
        self._errors = {}

        if user_input is not None:
            # Perform an area search using the user input and check whether any matches were found
            areas = await _search_areas(
                self.hass, self.api_key, user_input["area_search"]
            )

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
                area = await _get_area(
                    self.hass, self.api_key, user_input["area_selection"]
                )
                # Reject areas without a usable schedule: an entry created
                # from one could never load
                if area is None or not _pick_schedule_id(area):
                    self._errors["base"] = "bad_area"
                else:
                    # Create the entry, saving the API key and area details
                    return self.async_create_entry(
                        title="Loadshedding Status",
                        data=_area_entry_data(area),
                        options={
                            CONF_API_KEY: self.api_key,
                        },
                    )
            else:
                self._errors["base"] = "no_area_selection"

        # Reformat the areas as label/value pairs for the selector
        area_options = [
            {"label": _area_choice_label(item), "value": item["id"]}
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

    async def async_step_reauth(self, entry_data):
        """Handle reauth when the ESP API rejects the token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Ask for a replacement API key."""
        errors = {}
        if user_input is not None:
            error = await _validate_key(self.hass, user_input[CONF_API_KEY])
            if error is None:
                entry = self._get_reauth_entry()
                changed = self.hass.config_entries.async_update_entry(
                    entry,
                    options={**entry.options, CONF_API_KEY: user_input[CONF_API_KEY]},
                )
                # The update listener (added after a successful setup) reloads
                # on change; reload explicitly when it can't have fired: no
                # listener yet (auth failed during first refresh) or the same
                # key was re-entered (no change event)
                if not (changed and entry.update_listeners):
                    self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EskomOptionsFlowHandler()

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


class EskomOptionsFlowHandler(config_entries.OptionsFlow):
    """Eskom config flow options handler."""

    def __init__(self):
        """Initialize options flow."""
        self._errors = {}
        self._pending_options = {}
        self._effective_key = ""
        self.area_list = []

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}
        options = dict(self.config_entry.options)
        effective_key = options.get(CONF_API_KEY) or self.config_entry.data.get(
            CONF_API_KEY, ""
        )

        if user_input is not None:
            # Empty/omitted key = "unchanged": never store it, never let it
            # shadow a legacy entry.data fallback. Only re-validate a real
            # change, so options stay editable while ESP is unreachable.
            submitted_key = (user_input.get(CONF_API_KEY) or "").strip()
            error = None
            if not submitted_key or submitted_key == effective_key:
                user_input.pop(CONF_API_KEY, None)
            else:
                error = await _validate_key(self.hass, submitted_key)
                if error is None:
                    user_input[CONF_API_KEY] = submitted_key
                    effective_key = submitted_key
                else:
                    self._errors["base"] = error
            if error is None:
                # Set a minimum scan period
                if int(user_input[CONF_SCAN_PERIOD]) < MIN_SCAN_PERIOD:
                    user_input[CONF_SCAN_PERIOD] = MIN_SCAN_PERIOD
                area_search = (user_input.pop("area_search", "") or "").strip()
                options.update(user_input)
                if area_search:
                    # Re-selecting the area: search now, pick in the next step
                    areas = await _search_areas(self.hass, effective_key, area_search)
                    area_list = (areas or {}).get("areas") or []
                    if not area_list:
                        self._errors["base"] = "bad_area"
                    else:
                        self._pending_options = options
                        self._effective_key = effective_key
                        self.area_list = area_list
                        return await self.async_step_area_selection()
                else:
                    return self.async_create_entry(title="", data=options)

        data_schema = OrderedDict()
        data_schema[
            vol.Optional(
                CONF_SCAN_PERIOD,
                default=options.get(CONF_SCAN_PERIOD, DEFAULT_SCAN_PERIOD),
            )
        ] = int
        data_schema[vol.Optional(CONF_API_KEY, default=effective_key)] = str
        data_schema[vol.Optional("area_search", default="")] = str
        for x in sorted(PLATFORMS):
            data_schema[vol.Required(x, default=options.get(x, True))] = bool

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

    async def async_step_area_selection(self, user_input=None):
        """Apply a re-selected area to the config entry"""
        self._errors = {}

        if user_input is not None and "area_selection" in user_input:
            area = await _get_area(
                self.hass, self._effective_key, user_input["area_selection"]
            )
            # Reject areas without a usable schedule: the entry could never
            # load with one
            if area is None or not _pick_schedule_id(area):
                self._errors["base"] = "bad_area"
            else:
                new_data = dict(self.config_entry.data)
                new_data.update(_area_entry_data(area))
                # Commit data + options atomically: one listener fire, one
                # reload. The flow-finish options write then sees no change
                # and fires nothing.
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data, options=self._pending_options
                )
                ir.async_delete_issue(self.hass, DOMAIN, "v2_area_migrated")
                return self.async_create_entry(title="", data=self._pending_options)

        area_options = [
            {"label": _area_choice_label(item), "value": item["id"]}
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
