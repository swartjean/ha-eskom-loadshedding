# Eskom Loadshedding Interface

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![maintainer][maintenance-shield]][maintainer]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

This is a simple component to integrate with the [Eskom Loadshedding API](https://loadshedding.eskom.co.za/LoadShedding) and provide [loadshedding](https://en.wikipedia.org/wiki/South_African_energy_crisis)-related status information.

This integration exposes a sensor for the current stage of loadshedding. Due to current issues with the Eskom API, additional features (schedule lookups, etc) are unavailable. These will be implemented once the issues are resolved.

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show loadshedding status information.

{% if not installed %}
## Installation

1. Click install.
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Eskom Loadshedding Interface".

{% endif %}

## Configuration is done in the UI

<!---->

[buymecoffee]: https://www.buymeacoffee.com/swartjean
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/swartjean/ha-eskom-loadshedding.svg?style=for-the-badge
[commits]: https://github.com/swartjean/ha-eskom-loadshedding/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/swartjean/ha-eskom-loadshedding.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jean%20Swart%20%40swartjean-blue.svg?style=for-the-badge
[maintainer]: https://github.com/swartjean
[releases-shield]: https://img.shields.io/github/v/release/swartjean/ha-eskom-loadshedding?style=for-the-badge
[releases]: https://github.com/swartjean/ha-eskom-loadshedding/releases