"""Switch platform for mapped Windmill purifier settings."""

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_PURIFIER_MAX, DOMAIN, PURIFIER_MAX_PINS
from .purifier_entity import WindmillPurifierEntity
from .purifier_state import parse_purifier_switch

SWITCH_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="child_lock",
        name="Child lock",
        icon="mdi:lock-outline",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key="autofade",
        name="Autofade",
        icon="mdi:led-on",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key="sound",
        name="Button sounds",
        icon="mdi:volume-high",
        entity_category=EntityCategory.CONFIG,
    ),
)


class WindmillPurifierSwitch(WindmillPurifierEntity, SwitchEntity):
    """Control one boolean purifier setting."""

    def __init__(self, coordinator, description: SwitchEntityDescription) -> None:
        """Initialize a switch from its entity description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the current setting state."""
        return parse_purifier_switch(self.coordinator.data.get(self.entity_description.key))

    async def _async_set_state(self, state: bool) -> None:
        """Write only to a deliberately configured pin, then refresh."""
        pin = PURIFIER_MAX_PINS[self.entity_description.key]
        if pin is None:
            raise ValueError(f"No pin configured for {self.entity_description.key}")
        await self.coordinator.blynk_service.async_set_pin_value(pin, 1 if state else 0)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the setting."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the setting."""
        await self._async_set_state(False)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add switches only after their pins have been identified."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    if coordinator.device_type != DEVICE_PURIFIER_MAX:
        return
    async_add_entities(
        WindmillPurifierSwitch(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
        if PURIFIER_MAX_PINS[description.key] is not None
    )
