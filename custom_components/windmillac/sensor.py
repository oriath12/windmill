"""Sensor platform for mapped Windmill purifier measurements."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_PURIFIER_MAX, DOMAIN, PURIFIER_MAX_PINS
from .purifier_entity import WindmillPurifierEntity

SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="pm25",
        name="PM2.5",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="filter_life",
        name="Filter life remaining",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="air_quality",
        name="Air quality",
        icon="mdi:air-filter",
    ),
    SensorEntityDescription(
        key="wifi_rssi",
        name="Wi-Fi signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        suggested_display_precision=0,
    ),
)


class WindmillPurifierSensor(WindmillPurifierEntity, SensorEntity):
    """Report one read-only purifier measurement."""

    def __init__(self, coordinator, description: SensorEntityDescription) -> None:
        """Initialize a sensor from its entity description."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | float | int | None:
        """Return the mapped text or numeric value without inventing readings."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None or isinstance(value, bool):
            return None
        if self.entity_description.key == "air_quality":
            text = str(value).strip()
            return text or None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return int(number) if number.is_integer() else number


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors only for explicitly mapped purifier pins."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    if coordinator.device_type != DEVICE_PURIFIER_MAX:
        return
    async_add_entities(
        WindmillPurifierSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
        if PURIFIER_MAX_PINS.get(description.key) is not None
    )
