import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    BASE_URL,
    CONF_DEVICE_TYPE,
    CONF_TOKEN,
    DEFAULT_DEVICE_TYPE,
    DOMAIN,
    PLATFORMS,
)
from .blynk_service import BlynkService
from .coordinator import WindmillDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Windmill AC from a config entry."""
    _LOGGER.debug("Setting up Windmill AC config entry")

    server = BASE_URL
    token = entry.data[CONF_TOKEN]
    # Entries created before device-type support are A/C entries.
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)

    blynk_service = BlynkService(hass, server, token)
    coordinator = WindmillDataUpdateCoordinator(hass, blynk_service, device_type)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    await coordinator.async_config_entry_first_refresh()

    # Forward the platforms for this config entry.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok
