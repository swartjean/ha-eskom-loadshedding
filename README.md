# Eskom Loadshedding Interface

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![maintainer][maintenance-shield]][maintainer]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

This is a simple component to integrate with the [Eskom Loadshedding API](https://loadshedding.eskom.co.za/LoadShedding) and provide [loadshedding](https://en.wikipedia.org/wiki/South_African_energy_crisis)-related status information.

This integration exposes a sensor for the current stage of loadshedding.

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
