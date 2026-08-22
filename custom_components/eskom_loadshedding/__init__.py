"""
Custom integration to integrate the Eskom Loadshedding Interface with Home Assistant.

For more details about this integration, please refer to
https://github.com/swartjean/ha-eskom-loadshedding
"""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core_config import Config
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_API_KEY,
    CONF_AREA_ID,
    CONF_AREA_NAME,
    CONF_AREA_REGION,
    CONF_SCAN_PERIOD,
    CONF_SCHEDULE_ID,
    DEFAULT_SCAN_PERIOD,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)
from .eskom_interface import EskomInterface
from .esp_normalizers import EskomAuthError

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Setting up this integration using YAML is not supported."""
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Migrate a v1 (EskomSePush API 2.0) config entry to v2 (API 3.0).

    The v2.0 API's hyphenated area ids (e.g. eskde-10-fourways) embed the
    v3 schedule id as their first two segments (per ESP's own migration
    guidance), so schedules and events keep working automatically. The v3
    area id (za_…) cannot be derived, so area name/region attributes stay
    empty until the user re-selects their area; a repair issue prompts them.
    """
    if entry.version > 1:
        return True

    old_area_id = entry.data.get("area_id", "")
    schedule_id = "-".join(old_area_id.split("-")[:2])
    if "-" not in schedule_id:
        # Malformed/legacy area id: underivable — load with an empty schedule
        # and let the repair issue guide re-selection
        schedule_id = ""
    new_data = {
        "legacy_area_id": old_area_id,
        CONF_SCHEDULE_ID: schedule_id,
        CONF_AREA_ID: "",
        CONF_AREA_NAME: "",
        CONF_AREA_REGION: "",
    }
    # Preserve a key stored in data by pre-1.1.2 versions
    if entry.data.get("api_key") and not entry.options.get(CONF_API_KEY):
        new_data["api_key"] = entry.data["api_key"]

    hass.config_entries.async_update_entry(entry, data=new_data, version=2)
    ir.async_create_issue(
        hass,
        DOMAIN,
        "v2_area_migrated",
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="v2_area_migrated",
        learn_more_url="https://github.com/swartjean/ha-eskom-loadshedding#readme",
    )
    _LOGGER.info(
        "Migrated config entry to EskomSePush API 3.0 (schedule id: %s). "
        "Re-select your area from the integration options to restore the "
        "area name/region attributes",
        schedule_id,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    scan_period = timedelta(
        seconds=entry.options.get(CONF_SCAN_PERIOD, DEFAULT_SCAN_PERIOD)
    )

    # Fetch the configured API key and area details and create the client
    api_key = entry.options.get(CONF_API_KEY, entry.data.get("api_key"))
    session = async_get_clientsession(hass)
    client = EskomInterface(
        session=session,
        api_key=api_key,
        schedule_id=entry.data.get(CONF_SCHEDULE_ID),
        area_id=entry.data.get(CONF_AREA_ID),
        area_info={
            "name": entry.data.get(CONF_AREA_NAME, ""),
            "region": entry.data.get(CONF_AREA_REGION, ""),
        },
    )

    coordinator = EskomDataUpdateCoordinator(hass, entry, scan_period, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    enabled_platforms = [p for p in PLATFORMS if entry.options.get(p, True)]
    coordinator.platforms = enabled_platforms
    await hass.config_entries.async_forward_entry_setups(entry, enabled_platforms)

    if not entry.update_listeners:
        entry.add_update_listener(async_reload_entry)

    return True


class EskomDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass, entry, scan_period, client: EskomInterface):
        """Initialize."""
        self.client = client

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=scan_period,
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.async_get_data()
        except EskomAuthError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except Exception as exception:
            raise UpdateFailed(exception) from exception


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, coordinator.platforms
    )

    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
