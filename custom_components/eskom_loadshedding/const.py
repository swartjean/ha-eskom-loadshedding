"""Constants for eskom loadshedding interface"""

# Base component constants
NAME = "Eskom Loadshedding Interface"
DEVICE_NAME = "Loadshedding"
DOMAIN = "eskom_loadshedding"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "1.1.3"

ISSUE_URL = "https://github.com/swartjean/ha-eskom-loadshedding/issues"

# Icons
STATUS_SENSOR_ICON = "mdi:lightning-bolt"
LOCAL_STATUS_SENSOR_ICON = "mdi:home-lightning-bolt"
QUOTA_SENSOR_ICON = "mdi:cloud-percent"

# Platforms
SENSOR = "sensor"
CALENDAR = "calendar"
PLATFORMS = [SENSOR, CALENDAR]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_SCAN_PERIOD = "scan_period"
CONF_API_KEY = "api_key"

# Defaults
DEFAULT_SCAN_PERIOD = 7200
MIN_SCAN_PERIOD = 1800
DEFAULT_CALENDAR_SCAN_PERIOD = 30

# Entity Identifiers
LOCAL_EVENTS_ID = "calendar_local_events"
LOCAL_SCHEDULE_ID = "calendar_local_schedule"
NATIONAL_STATUS_ID = "national"
CAPE_TOWN_STATUS_ID = "capetown"
NATIONAL_STATUS_AREA_ID = "eskom"
CAPE_TOWN_STATUS_AREA_ID = "capetown"
LOCAL_STATUS_ID = "local"
QUOTA_ID = "api_quota"

# Entity Names
LOCAL_EVENTS_NAME = "Local Events"
LOCAL_SCHEDULE_NAME = "Local Schedule"
NATIONAL_SATUS_NAME = "National Status"
CAPE_TOWN_STATUS_NAME = "Cape Town Status"
LOCAL_STATUS_NAME = "Local Status"
QUOTA_NAME = "API Quota"

# API
BASE_API_URL = "https://developer.sepush.co.za/business/2.0"
REQUEST_TIMEOUT_S = 10

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
Welcome to the Eskom Loadshedding Interface!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
