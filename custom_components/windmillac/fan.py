"""Fan platform for Windmill air purifiers."""

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import (
    DEVICE_PURIFIER_MAX,
    DOMAIN,
    PURIFIER_MAX_PRESETS,
    PURIFIER_MAX_SPEEDS,
)
from .purifier_entity import WindmillPurifierEntity
from .purifier_state import is_manual_speed


class WindmillPurifierFan(WindmillPurifierEntity, FanEntity):
    """Represent the purifier as a fan, not an air conditioner."""

    _attr_name = None
    _attr_icon = "mdi:air-purifier"
    _attr_speed_count = len(PURIFIER_MAX_SPEEDS)
    _attr_preset_modes = list(PURIFIER_MAX_PRESETS)
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator) -> None:
        """Initialize the purifier's main fan entity."""
        super().__init__(coordinator, "fan")
        self._speeds = list(PURIFIER_MAX_SPEEDS)

    @property
    def is_on(self) -> bool | None:
        """Return the purifier power state."""
        return self.coordinator.data.get("power")

    @property
    def percentage(self) -> int | None:
        """Return manual speed as a percentage, or None during a preset."""
        if not self.is_on:
            return 0
        mode = self.coordinator.data.get("mode")
        if not is_manual_speed(mode):
            return None
        return ordered_list_item_to_percentage(self._speeds, mode)

    @property
    def preset_mode(self) -> str | None:
        """Return the active Eco or sleep preset."""
        if not self.is_on:
            return None
        mode = self.coordinator.data.get("mode")
        if mode == "Sleep":
            if self.coordinator.data.get("sleep_style") == "White Noise":
                return "White Noise"
            return "Sleep"
        return "Eco" if mode == "Eco" else None

    async def _async_apply_mode(self, mode: str) -> None:
        """Apply a manual speed or a main-mode/sleep-style combination."""
        if mode == "White Noise":
            await self.coordinator.blynk_service.async_set_purifier_mode("Sleep")
            await self.coordinator.blynk_service.async_set_sleep_style("White Noise")
        elif mode == "Sleep":
            await self.coordinator.blynk_service.async_set_purifier_mode("Sleep")
            await self.coordinator.blynk_service.async_set_sleep_style("Whisper")
        else:
            await self.coordinator.blynk_service.async_set_purifier_mode(mode)

    async def _async_set_mode(self, mode: str) -> None:
        """Power on if necessary, set a mode, and refresh once."""
        if not self.is_on:
            await self.coordinator.blynk_service.async_set_power(True)
        await self._async_apply_mode(mode)
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set one of the four manual speeds; zero turns the purifier off."""
        if percentage == 0:
            await self.async_turn_off()
            return
        mode = percentage_to_ordered_list_item(self._speeds, percentage)
        await self._async_set_mode(mode)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set Eco, Sleep/Whisper, or Sleep/White Noise mode."""
        await self._async_set_mode(preset_mode)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn on, optionally selecting a speed or preset."""
        if percentage == 0:
            await self.async_turn_off()
            return
        await self.coordinator.blynk_service.async_set_power(True)
        if preset_mode is not None:
            await self._async_apply_mode(preset_mode)
        elif percentage is not None:
            mode = percentage_to_ordered_list_item(self._speeds, percentage)
            await self.coordinator.blynk_service.async_set_purifier_mode(mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the purifier off."""
        await self.coordinator.blynk_service.async_set_power(False)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a fan only for purifier config entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    if coordinator.device_type == DEVICE_PURIFIER_MAX:
        async_add_entities([WindmillPurifierFan(coordinator)])
