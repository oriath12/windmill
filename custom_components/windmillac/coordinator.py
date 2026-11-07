#coordinator.py
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import (
    DEFAULT_DEVICE_TYPE,
    DEVICE_PURIFIER_MAX,
    DOMAIN,
    PURIFIER_MAX_PINS,
    UPDATE_INTERVAL,
)
from .purifier_state import parse_purifier_mode, parse_purifier_switch, parse_sleep_style

_LOGGER = logging.getLogger(__name__)

class WindmillDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Windmill AC API."""

    def __init__(self, hass, blynk_service, device_type=DEFAULT_DEVICE_TYPE):
        """Initialize the coordinator for one configured device type."""
        _LOGGER.debug("Initializing Windmill coordinator for %s", device_type)
        self.blynk_service = blynk_service
        self.device_type = device_type
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self):
        """Fetch data using only the configured device's pin profile."""
        if self.device_type == DEVICE_PURIFIER_MAX:
            return await self._async_update_purifier_data()
        return await self._async_update_ac_data()

    async def _async_update_ac_data(self):
        """Fetch the legacy A/C data set without changing its behavior."""
        _LOGGER.debug("Fetching data from Windmill AC")
        try:
            data = {
                "current_temp": await self.blynk_service.async_get_pin_value("V1"),
                "target_temp": await self.blynk_service.async_get_pin_value("V2"),
                "mode": await self.blynk_service.async_get_mode(),
                "fan": await self.blynk_service.async_get_fan(),
                "power": await self.blynk_service.async_get_power(),
            }
            _LOGGER.debug("Data fetched from Windmill AC: %s", data)
            return data
        except Exception as err:
            _LOGGER.error("Error fetching A/C data: %s", err)
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def _async_update_purifier_data(self):
        """Fetch purifier power, mode, and only explicitly mapped extras."""
        try:
            data = {
                "power": parse_purifier_switch(
                    await self.blynk_service.async_get_pin_value(
                        PURIFIER_MAX_PINS["power"]
                    )
                ),
                "mode": parse_purifier_mode(
                    await self.blynk_service.async_get_pin_value(
                        PURIFIER_MAX_PINS["mode"]
                    )
                ),
            }
        except Exception as err:
            _LOGGER.error("Error fetching required purifier data: %s", err)
            raise UpdateFailed(f"Error fetching purifier data: {err}") from err

        for key, pin in PURIFIER_MAX_PINS.items():
            if key in {"power", "mode"} or pin is None:
                continue
            try:
                value = await self.blynk_service.async_get_pin_value(pin)
                data[key] = parse_sleep_style(value) if key == "sleep_style" else value
            except Exception as err:
                # An optional sensor must never make power/speed control unavailable.
                data[key] = None
                _LOGGER.debug("Optional purifier value %s unavailable on %s: %s", key, pin, err)

        _LOGGER.debug("Data fetched from Windmill purifier: %s", data)
        return data
