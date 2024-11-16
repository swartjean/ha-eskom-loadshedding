"""Sensor platform for Eskom Loadshedding Interface."""

import re
from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import callback

from .const import (
    DEFAULT_CALENDAR_SCAN_PERIOD,
    DOMAIN,
    LOCAL_EVENTS_ID,
    LOCAL_EVENTS_NAME,
    LOCAL_SCHEDULE_ID,
    LOCAL_SCHEDULE_NAME,
)
from .entity import EskomEntity

SCAN_INTERVAL = timedelta(seconds=DEFAULT_CALENDAR_SCAN_PERIOD)


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup calendar platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            LoadsheddingLocalEventCalendar(
                coordinator,
                entry,
                calendar_id=LOCAL_EVENTS_ID,
                friendly_name=LOCAL_EVENTS_NAME,
            ),
            LoadsheddingLocalScheduleCalendar(
                coordinator,
                entry,
                calendar_id=LOCAL_SCHEDULE_ID,
                friendly_name=LOCAL_SCHEDULE_NAME,
            ),
        ]
    )


class LoadsheddingLocalEventCalendar(EskomEntity, CalendarEntity):
    """Loadshedding Local Event Calendar class."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, calendar_id: str, friendly_name: str):
        """Initialize."""
        self.calendar_id = calendar_id
        self.friendly_name = friendly_name
        super().__init__(coordinator, config_entry)

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.calendar_id}"

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self.friendly_name

    @property
    def should_poll(self) -> bool:
        """
        Enable polling for the entity.

        The coordinator is used to query the API, but polling is used to update
        the entity state more frequently.
        """
        return True

    @property
    def event(self):
        # Return the next event
        events = self.coordinator.data.get("area_information", {}).get("events", {})
        if events:
            time_format = "%Y-%m-%dT%H:%M:%S%z"
            next_event_start = datetime.strptime(events[0]["start"], time_format)
            next_event_end = datetime.strptime(events[0]["end"], time_format)
            return CalendarEvent(next_event_start, next_event_end, events[0]["note"])

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Copy the state from the coordinator to this entity
        events = self.coordinator.data.get("area_information", {}).get("events", {})
        if events:
            time_format = "%Y-%m-%dT%H:%M:%S%z"
            next_event_start = datetime.strptime(events[0]["start"], time_format)
            next_event_end = datetime.strptime(events[0]["end"], time_format)
            self._event = CalendarEvent(
                next_event_start, next_event_end, events[0]["note"]
            )

        super()._handle_coordinator_update()

    async def async_get_events(
        self,
        hass,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        # Create calendar events from loadshedding events
        events = self.coordinator.data.get("area_information", {}).get("events", {})
        if events:
            time_format = "%Y-%m-%dT%H:%M:%S%z"
            return [
                CalendarEvent(
                    start=datetime.strptime(event["start"], time_format),
                    end=datetime.strptime(event["end"], time_format),
                    summary=event["note"],
                )
                for event in events
            ]
        return []

    async def async_update(self) -> None:
        """
        Disable update behavior.
        Event updates are performed through the coordinator callback.
        This is simply used to evaluate the entity state
        """


class LoadsheddingLocalScheduleCalendar(EskomEntity, CalendarEntity):
    """Loadshedding Local Schedule Calendar class."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, calendar_id, friendly_name: str):
        """Initialize."""
        self.calendar_id = calendar_id
        self.friendly_name = friendly_name
        super().__init__(coordinator, config_entry)

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.calendar_id}"

    @property
    def name(self):
        """Return the friendly name of the sensor."""
        return self.friendly_name

    @property
    def should_poll(self) -> bool:
        """
        Enable polling for the entity.

        The coordinator is used to query the API, but polling is used to update
        the entity state more frequently.
        """
        return True

    @property
    def event(self):
        # Return the next event
        events = self.coordinator.data.get("area_information", {}).get("events", {})
        if events:
            time_format = "%Y-%m-%dT%H:%M:%S%z"
            next_event_start = datetime.strptime(events[0]["start"], time_format)
            next_event_end = datetime.strptime(events[0]["end"], time_format)
            return CalendarEvent(next_event_start, next_event_end, events[0]["note"])

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Copy the state from the coordinator to this entity
        events = self.coordinator.data.get("area_information", {}).get("events", {})
        if events:
            time_format = "%Y-%m-%dT%H:%M:%S%z"
            next_event_start = datetime.strptime(events[0]["start"], time_format)
            next_event_end = datetime.strptime(events[0]["end"], time_format)
            self._event = CalendarEvent(
                next_event_start, next_event_end, events[0]["note"]
            )

        super()._handle_coordinator_update()

    async def async_get_events(
        self,
        hass,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        # Create calendar events from the loadshedding schedule
        schedule = self.coordinator.data.get("area_information", {}).get("schedule", {})
        if schedule:
            # Iterate over each day in the schedule and create calender events for each slot
            time_format = "%Y-%m-%dT%H:%M%z"
            calendar_events = []
            for day in schedule["days"]:
                for n, stage in enumerate(day["stages"]):
                    for time_range in stage:
                        # Extract the start and end time from the provided time range
                        times = re.findall(r"\d\d:\d\d", time_range)

                        # Create datetimes from the extracted times
                        start_time = datetime.strptime(
                            f"{day['date']}T{times[0]}+02:00", time_format
                        )
                        end_time = datetime.strptime(
                            f"{day['date']}T{times[1]}+02:00", time_format
                        )

                        # If the end time was earlier than the start time it means that the slot ran into the next day
                        # i.e. 22:30-00:30
                        if end_time < start_time:
                            end_time += timedelta(days=1)

                        calendar_events.append(
                            CalendarEvent(
                                start=start_time, end=end_time, summary=f"Stage {n + 1}"
                            )
                        )

            return calendar_events
        return []

    async def async_update(self) -> None:
        """
        Disable update behavior.
        Event updates are performed through the coordinator callback.
        This is simply used to evaluate the entity state
        """
