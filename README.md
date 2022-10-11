# Eskom Loadshedding Interface

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![maintainer][maintenance-shield]][maintainer]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

This component integrates with the [EskomSePush](https://sepush.co.za/) API to provide [loadshedding](https://en.wikipedia.org/wiki/South_African_energy_crisis)-related status information.

An EskomSePush API key is required in order to use this integration. Please visit the [EskomSePush website](https://sepush.co.za/) to sign up and view API documentation.

**This component will set up the following platforms:**

Platform | Description
-- | --
`sensor` | Shows loadshedding status information for various areas.
`calendar` | Shows upcoming loadshedding event and schedule information for your area.

**This component will create the following entities:**

Entity | Description
-- | --
`sensor.loadshedding_api_quota` | The EskomSePush API quota associated with your API key.
`sensor.loadshedding_national_status` | The current national loadshedding stage for Eskom-supplied customers.
`sensor.loadshedding_cape_town_status` | The current loadshedding stage for City of Cape Town customers.
`sensor.loadshedding_local_status` | The current loadshedding stage for your specific area.
`calendar.loadshedding_local_events` | Calendar of upcoming loadshedding events for your specific area.
`calendar.loadshedding_local_schedule` | Calendar containing the full 7-day loadshedding schedule for your specific area.

The component update period defaults to 2 hours in order to avoid excess API quota consumption. This can be edited through the integration configuration, but you are responsible for monitoring your own API usage.

The recommended way to automate actions around loadshedding events is to use calendar triggers. Below is an example of a simple automation to turn off a switch one hour before any loadshedding event in your area:

```yaml
alias: Loadshedding Notification
trigger:
  - platform: calendar
    event: start
    entity_id: calendar.loadshedding_local_events
    offset: "-1:0:0"
action:
  - service: homeassistant.turn_off
    data: {}
    target:
      entity_id: switch.example_device
mode: queued
```

Note that by installing this integration you are using it at your own risk. Neither the creators of this integration, nor the EskomSePush team, will be held responsible for any inaccuracies or errors in the loadshedding information presented.

## Installation

**Note that an EskomSePush API key is required in order to use this integration**

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `eskom_loadshedding`.
4. Download _all_ the files from the `custom_components/eskom_loadshedding/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Settings" -> "Devices & Services", then click "+ Add Integration" and search for "Eskom Loadshedding Interface"
8. Complete the initial configuration by entering your EskomSePush API key and selecting your loadshedding zone

## Configuration is done in the UI

<!---->

[buymecoffee]: https://www.buymeacoffee.com/swartjean
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/swartjean/ha-eskom-loadshedding.svg?style=for-the-badge
[commits]: https://github.com/swartjean/ha-eskom-loadshedding/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/swartjean/ha-eskom-loadshedding.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jean%20Swart%20%40swartjean-blue.svg?style=for-the-badge
[maintainer]: https://github.com/swartjean
[releases-shield]: https://img.shields.io/github/v/release/swartjean/ha-eskom-loadshedding?style=for-the-badge
[releases]: https://github.com/swartjean/ha-eskom-loadshedding/releases
