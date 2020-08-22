# Eskom Loadshedding Interface

This is a simple component to integrate with the [Eskom Loadshedding API](https://loadshedding.eskom.co.za/LoadShedding) and provide [loadshedding](https://en.wikipedia.org/wiki/South_African_energy_crisis)-related status information.

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show loadshedding status information.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `eskom_loadshedding`.
4. Download _all_ the files from the `custom_components/eskom_loadshedding/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Eskom Loadshedding Interface"

## Configuration is done in the UI

<!---->
