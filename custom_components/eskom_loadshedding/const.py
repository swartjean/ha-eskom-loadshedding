"""Constants for eskom loadshedding interface"""
# Base component constants
NAME = "Eskom Loadshedding Interface"
DOMAIN = "eskom_loadshedding"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "1.0.5"

ISSUE_URL = "https://github.com/swartjean/ha-eskom-loadshedding/issues"

# Icons
ICON = "mdi:lightning-bolt"

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_SCAN_PERIOD = "scan_period"

# Defaults
DEFAULT_SCAN_PERIOD = 900
MIN_SCAN_PERIOD = 300

# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
Welcome to the Eskom Loadshedding Interface!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
