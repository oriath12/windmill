import json
import logging
from urllib.parse import urlencode

import requests
from homeassistant.components.climate.const import HVACMode

from .const import PURIFIER_MAX_PINS, REQUEST_TIMEOUT
from .purifier_state import purifier_mode_to_pin, sleep_style_to_pin

_LOGGER = logging.getLogger(__name__)


class BlynkService:
    def __init__(self, hass, server, token):
        self.hass = hass
        self.server = server
        self.token = token
        # Mapping of string values to pin values
        self.fan_speed_mapping = {
            "Auto": "0",
            "Low": "1",
            "Medium": "2",
            "High": "3"
        }
        self.mode_mapping = {
            HVACMode.AUTO: "2",
            HVACMode.COOL: "1",
            HVACMode.FAN_ONLY: "0"
        }
        self.power_mapping = {
            False: 0,
            True: 1
        }

    def _get_request_url(self, endpoint, params):
        query = urlencode(params)
        return f"{self.server}/{endpoint}?{query}"

    async def async_get_pin_value(self, pin):
        _LOGGER.debug(f"Getting pin value for pin {pin}")
        params = {'token': self.token}
        url = self._get_request_url(f'external/api/get', params) + f"&{pin}"

        def fetch():
            try:
                response = requests.get(url, timeout=REQUEST_TIMEOUT)
            except requests.exceptions.RequestException:
                raise Exception(f"Failed to get pin value for {pin}") from None
            _LOGGER.debug("Response Status Code: %s", response.status_code)

            if response.status_code != 200:
                raise Exception(f"Failed to get pin value for {pin}")

            text = response.text.strip()
            try:
                value = json.loads(text)
            except (ValueError, TypeError):
                # Blynk may return an unquoted enumerable label such as "eco".
                return text
            if isinstance(value, list):
                if not value:
                    raise Exception(f"Failed to parse response for {pin}: empty array")
                return value[0]
            return value

        return await self.hass.async_add_executor_job(fetch)

    async def async_set_pin_value(self, pin, value):
        _LOGGER.debug(f"Setting pin value for pin {pin} to {value}")
        params = {'token': self.token, pin: value}
        url = self._get_request_url(f'external/api/update', params)

        def fetch():
            try:
                response = requests.get(url, timeout=REQUEST_TIMEOUT)
            except requests.exceptions.RequestException:
                raise Exception(f"Failed to set pin value for {pin}") from None
            _LOGGER.debug("Response Status Code: %s", response.status_code)

            if response.status_code == 200:
                return response.text.strip()
            else:
                raise Exception(f"Failed to set pin value for {pin}")

        return await self.hass.async_add_executor_job(fetch)

    async def async_set_power(self, value):
        _LOGGER.debug(f"Setting Raw Power: {value}")
        pin_value = self.power_mapping.get(value, "0")
        _LOGGER.debug(f"Setting Power: {pin_value}")
        await self.async_set_pin_value('V0', pin_value)

    async def async_set_current_temp(self, value):
        await self.async_set_pin_value('V1', str(value))

    async def async_set_target_temp(self, value):
        await self.async_set_pin_value('V2', str(value))

    async def async_set_mode(self, value):
        value = value.lower()  # Ensure consistent casing
        pin_value = self.mode_mapping.get(value, "0")
        _LOGGER.debug(f"Setting mode {value} to pin {pin_value}")
        await self.async_set_pin_value('V3', pin_value)

    async def async_set_fan(self, value):
        # value = value.lower()  # Ensure consistent casing
        pin_value = self.fan_speed_mapping.get(value, "0")
        _LOGGER.debug(f"Setting fan {value} to pin {pin_value}")
        await self.async_set_pin_value('V4', pin_value)

    async def async_get_power(self) -> bool:
        pin_value = await self.async_get_pin_value('V0')
        _LOGGER.debug(f"Pin value received for power: {pin_value} (type: {type(pin_value)})")
        if pin_value == 1:
            return True
        else:
            return False

    async def async_get_mode(self):
        pin_value = await self.async_get_pin_value('V3')
        pin_value = str(pin_value).lower()
        current_power_state = await self.async_get_power()
        if current_power_state != False:
            match pin_value:
                case "cool":
                    return HVACMode.COOL
                case "fan":
                    return HVACMode.FAN_ONLY
                case "eco":
                    return HVACMode.AUTO
                case _:
                    return HVACMode.OFF
        else:
            return HVACMode.OFF


    async def async_get_fan(self):
        pin_value = await self.async_get_pin_value('V4')
        pin_value = str(pin_value).lower()
        fan_mode = "Auto"

        match pin_value:
            case "low":
                fan_mode = "Low"
            case "medium":
                fan_mode = "Medium"
            case "high":
                fan_mode = "High"
        _LOGGER.debug(f"Pin value: {pin_value} is mapped mode mapped to: {fan_mode}")
        return fan_mode

    async def async_set_purifier_mode(self, mode):
        """Set a purifier manual speed or preset on its mapped mode pin."""
        pin = PURIFIER_MAX_PINS["mode"]
        if not pin:
            raise ValueError("The purifier mode pin is not configured")
        value = purifier_mode_to_pin(mode)
        _LOGGER.debug("Setting purifier mode %s to pin %s value %s", mode, pin, value)
        await self.async_set_pin_value(pin, value)

    async def async_set_sleep_style(self, style):
        """Select Whisper or White Noise on the purifier's V4 enum."""
        pin = PURIFIER_MAX_PINS["sleep_style"]
        value = sleep_style_to_pin(style)
        _LOGGER.debug("Setting sleep style %s to pin %s value %s", style, pin, value)
        await self.async_set_pin_value(pin, value)
