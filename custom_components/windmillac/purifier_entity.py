"""Shared entity behavior for Windmill purifier platforms."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PURIFIER_MAX_MODEL
from .purifier_state import device_identifier


class WindmillPurifierEntity(CoordinatorEntity):
    """Associate a purifier entity with its non-secret device identity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key: str) -> None:
        """Initialize the shared device and entity identifiers."""
        super().__init__(coordinator)
        self._device_id = device_identifier(coordinator.blynk_service.token)
        self._attr_unique_id = f"{self._device_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=f"Windmill {PURIFIER_MAX_MODEL}",
            manufacturer="Windmill",
            model=PURIFIER_MAX_MODEL,
        )

    @property
    def available(self) -> bool:
        """Return whether the latest coordinator update succeeded."""
        return self.coordinator.last_update_success
