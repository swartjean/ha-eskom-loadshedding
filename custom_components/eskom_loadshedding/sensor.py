"""Sensor platform for Eskom Loadshedding Interface."""

import re
from datetime import datetime

from homeassistant.components.sensor import SensorEntity

from .const import (
    CAPE_TOWN_STATUS_AREA_ID,
    CAPE_TOWN_STATUS_ID,
    CAPE_TOWN_STATUS_NAME,
    DOMAIN,
    LOCAL_STATUS_ID,
    LOCAL_STATUS_NAME,
    LOCAL_STATUS_SENSOR_ICON,
    NATIONAL_SATUS_NAME,
    NATIONAL_STATUS_AREA_ID,
    NATIONAL_STATUS_ID,
    QUOTA_ID,
    QUOTA_NAME,
    QUOTA_SENSOR_ICON,
    STATUS_SENSOR_ICON,
)
from .entity import EskomEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            LoadsheddingStatusSensor(
                coordinator,
                entry,
                area=NATIONAL_STATUS_AREA_ID,
                sensor_id=NATIONAL_STATUS_ID,
                friendly_name=NATIONAL_SATUS_NAME,
            ),
            LoadsheddingStatusSensor(
                coordinator,
                entry,
                area=CAPE_TOWN_STATUS_AREA_ID,
                sensor_id=CAPE_TOWN_STATUS_ID,
                friendly_name=CAPE_TOWN_STATUS_NAME,
            ),
            LoadsheddingAreaInfoSensor(
                coordinator,
                entry,
                sensor_id=LOCAL_STATUS_ID,
                friendly_name=LOCAL_STATUS_NAME,
            ),
            LoadsheddingAPIQuotaSensor(
                coordinator,
                entry,
                sensor_id=QUOTA_ID,
                friendly_name=QUOTA_NAME,
            ),
        ]
    )


class LoadsheddingStatusSensor(EskomEntity, SensorEntity):
    """Eskom Stage Sensor class."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator, config_entry, area: str, sensor_id: str, friendly_name: str
    ):
        """Initialize."""
        self.area = area
        self.sensor_id = sensor_id
        self.friendly_name = friendly_name
        super().__init__(coordinator, config_entry)

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.sensor_id}"

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self.friendly_name

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        value = (
            self.coordinator.data.get("status", {})
            .get("status", {})
            .get(self.area, {})
            .get("stage")
        )
        if value:
            return int(value)

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return STATUS_SENSOR_ICON

    @property
    def extra_state_attributes(self):
        # Gather data from coordinator
        area_name = (
            self.coordinator.data.get("status", {})
            .get("status", {})
            .get(self.area, {})
            .get("name")
        )
        stage_updated = (
            self.coordinator.data.get("status", {})
            .get("status", {})
            .get(self.area, {})
            .get("stage_updated")
        )

        # Convert time strings to datetimes:
        time_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        time_updated = datetime.strptime(stage_updated, time_format)
        return {
            "Area Name": area_name,
            "Time Updated": time_updated,
        }


class LoadsheddingAreaInfoSensor(EskomEntity, SensorEntity):
    """Eskom Area Info Sensor class."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, sensor_id, friendly_name: str):
        """Initialize."""
        self.sensor_id = sensor_id
        self.friendly_name = friendly_name
        super().__init__(coordinator, config_entry)

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.sensor_id}"

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self.friendly_name

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        events = self.coordinator.data.get("area_information", {}).get("events", {})

        if events:
            # Extract the first number in the note as the stage for display as an int
            # This assumes the note is always formatted as "Stage X"
            matches = re.findall(r"\d+", events[0]["note"])
            if matches:
                return int(matches[0])
            return events[0]["note"]
        return 0

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return LOCAL_STATUS_SENSOR_ICON

    @property
    def extra_state_attributes(self):
        # Gather data from coordinator
        events = self.coordinator.data.get("area_information", {}).get("events", {})
        info = self.coordinator.data.get("area_information", {}).get("info", {})

        currently_loadshedding = False

        if events:
            # Determine whether the area is currently loadshedding
            time_format = "%Y-%m-%dT%H:%M:%S%z"
            next_event_start = datetime.strptime(events[0]["start"], time_format)
            next_event_end = datetime.strptime(events[0]["end"], time_format)
            current_time = datetime.now(next_event_start.tzinfo)
            currently_loadshedding = next_event_start <= current_time <= next_event_end

        return {
            "Area": info["name"],
            "Region": info["region"],
            "Currently Loadshedding": currently_loadshedding,
        }


class LoadsheddingAPIQuotaSensor(EskomEntity, SensorEntity):
    """Eskom API Quota Sensor class."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, sensor_id, friendly_name: str):
        """Initialize."""
        self.sensor_id = sensor_id
        self.friendly_name = friendly_name
        super().__init__(coordinator, config_entry)

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.sensor_id}"

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self.friendly_name

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        # Return the number of API calls remaining as the native sensor value
        allowance = self.coordinator.data.get("allowance", {}).get("allowance", {})

        if allowance:
            return int(allowance["limit"]) - int(allowance["count"])

        return None

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return QUOTA_SENSOR_ICON

    @property
    def extra_state_attributes(self):
        # Gather data from coordinator
        allowance = self.coordinator.data.get("allowance", {}).get("allowance", {})

        if allowance:
            return {
                "Remaining": int(allowance["limit"]) - int(allowance["count"]),
                "Count": int(allowance["count"]),
                "Limit": int(allowance["limit"]),
                "Type": allowance["type"],
            }
        return None
