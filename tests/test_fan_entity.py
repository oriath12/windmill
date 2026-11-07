"""Dependency-free behavioral tests for purifier fan, sensors, and switches."""

import asyncio
import importlib.util
import math
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.windmillac"


def module(name, **attributes):
    """Create a module stub with the requested attributes."""
    result = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(result, key, value)
    sys.modules[name] = result
    return result


def load(name, relative_path):
    """Load an integration module by path."""
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


root = types.ModuleType("custom_components")
root.__path__ = [str(ROOT / "custom_components")]
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components/windmillac")]
sys.modules["custom_components"] = root
sys.modules[PACKAGE] = package


class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


class DeviceInfo:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FanEntity:
    pass


class SensorEntity:
    pass


class SwitchEntity:
    pass


class EntityDescription:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


module("homeassistant")
module("homeassistant.components")
module(
    "homeassistant.components.fan",
    FanEntity=FanEntity,
    FanEntityFeature=types.SimpleNamespace(
        SET_SPEED=1, PRESET_MODE=2, TURN_ON=4, TURN_OFF=8
    ),
)
module(
    "homeassistant.components.sensor",
    SensorEntity=SensorEntity,
    SensorEntityDescription=EntityDescription,
    SensorDeviceClass=types.SimpleNamespace(PM25="pm25", SIGNAL_STRENGTH="signal_strength"),
    SensorStateClass=types.SimpleNamespace(MEASUREMENT="measurement"),
)
module(
    "homeassistant.components.switch",
    SwitchEntity=SwitchEntity,
    SwitchEntityDescription=EntityDescription,
)
module("homeassistant.config_entries", ConfigEntry=object)
module(
    "homeassistant.const",
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER="µg/m³",
    PERCENTAGE="%",
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT="dBm",
    EntityCategory=types.SimpleNamespace(CONFIG="config", DIAGNOSTIC="diagnostic"),
)
module("homeassistant.core", HomeAssistant=object)
module("homeassistant.helpers")
module("homeassistant.helpers.entity", DeviceInfo=DeviceInfo)
module("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
module("homeassistant.helpers.update_coordinator", CoordinatorEntity=CoordinatorEntity)
module("homeassistant.util")


def ordered_list_item_to_percentage(items, item):
    return (items.index(item) + 1) * 100 // len(items)


def percentage_to_ordered_list_item(items, percentage):
    return items[math.ceil(percentage / 100 * len(items)) - 1]


module(
    "homeassistant.util.percentage",
    ordered_list_item_to_percentage=ordered_list_item_to_percentage,
    percentage_to_ordered_list_item=percentage_to_ordered_list_item,
)

const = load(f"{PACKAGE}.const", "custom_components/windmillac/const.py")
load(f"{PACKAGE}.purifier_state", "custom_components/windmillac/purifier_state.py")
load(f"{PACKAGE}.purifier_entity", "custom_components/windmillac/purifier_entity.py")
fan_module = load(f"{PACKAGE}.fan", "custom_components/windmillac/fan.py")
sensor_module = load(f"{PACKAGE}.sensor", "custom_components/windmillac/sensor.py")
switch_module = load(f"{PACKAGE}.switch", "custom_components/windmillac/switch.py")


class FakeService:
    def __init__(self):
        self.calls = []

    async def async_set_power(self, value):
        self.calls.append(("power", value))

    async def async_set_purifier_mode(self, mode):
        self.calls.append(("mode", mode))

    async def async_set_sleep_style(self, style):
        self.calls.append(("sleep_style", style))

    async def async_set_pin_value(self, pin, value):
        self.calls.append(("pin", pin, value))


class FakeCoordinator:
    def __init__(self, data):
        self.data = data
        self.device_type = const.DEVICE_PURIFIER_MAX
        self.last_update_success = True
        self.blynk_service = FakeService()
        self.blynk_service.token = "secret-device-token"
        self.refreshes = 0

    async def async_request_refresh(self):
        self.refreshes += 1


def setup_platform(platform, coordinator):
    """Run one platform setup and return its added entities."""
    entry = types.SimpleNamespace(entry_id="entry")
    hass = types.SimpleNamespace(
        data={const.DOMAIN: {"entry": {"coordinator": coordinator}}}
    )
    added = []
    asyncio.run(platform.async_setup_entry(hass, entry, added.extend))
    return added


class FanEntityTests(unittest.TestCase):
    def test_manual_speed_percentages(self):
        expected = {"Low": 25, "Medium": 50, "High": 75, "Boost": 100}
        for mode, percentage in expected.items():
            with self.subTest(mode=mode):
                fan = fan_module.WindmillPurifierFan(
                    FakeCoordinator({"power": True, "mode": mode})
                )
                self.assertEqual(fan.percentage, percentage)
                self.assertIsNone(fan.preset_mode)

    def test_eco_and_sleep_are_presets(self):
        cases = (
            ("Eco", "Whisper", "Eco"),
            ("Sleep", "Whisper", "Sleep"),
            ("Sleep", "White Noise", "Sleep"),
        )
        for mode, sleep_style, preset in cases:
            with self.subTest(preset=preset):
                fan = fan_module.WindmillPurifierFan(
                    FakeCoordinator(
                        {"power": True, "mode": mode, "sleep_style": sleep_style}
                    )
                )
                self.assertIsNone(fan.percentage)
                self.assertEqual(fan.preset_mode, preset)

    def test_off_state_has_zero_speed_and_no_preset(self):
        fan = fan_module.WindmillPurifierFan(
            FakeCoordinator({"power": False, "mode": "High"})
        )
        self.assertEqual(fan.percentage, 0)
        self.assertIsNone(fan.preset_mode)

    def test_setting_percentage_maps_to_medium(self):
        coordinator = FakeCoordinator({"power": True, "mode": "Low"})
        fan = fan_module.WindmillPurifierFan(coordinator)
        asyncio.run(fan.async_set_percentage(50))
        self.assertEqual(coordinator.blynk_service.calls, [("mode", "Medium")])
        self.assertEqual(coordinator.refreshes, 1)

    def test_white_noise_is_not_offered_as_a_preset(self):
        fan = fan_module.WindmillPurifierFan(
            FakeCoordinator({"power": True, "mode": "Sleep"})
        )
        self.assertEqual(fan._attr_preset_modes, ["Eco", "Sleep"])
        self.assertNotIn("White Noise", fan._attr_preset_modes)

    def test_sleep_preset_selects_whisper(self):
        coordinator = FakeCoordinator(
            {"power": True, "mode": "Sleep", "sleep_style": "White Noise"}
        )
        fan = fan_module.WindmillPurifierFan(coordinator)
        asyncio.run(fan.async_set_preset_mode("Sleep"))
        self.assertEqual(
            coordinator.blynk_service.calls,
            [("mode", "Sleep"), ("sleep_style", "Whisper")],
        )
        self.assertEqual(coordinator.refreshes, 1)

    def test_zero_percentage_turns_off(self):
        coordinator = FakeCoordinator({"power": True, "mode": "Low"})
        fan = fan_module.WindmillPurifierFan(coordinator)
        asyncio.run(fan.async_set_percentage(0))
        self.assertEqual(coordinator.blynk_service.calls, [("power", False)])
        self.assertEqual(coordinator.refreshes, 1)

    def test_turn_on_with_boost(self):
        coordinator = FakeCoordinator({"power": False, "mode": "Low"})
        fan = fan_module.WindmillPurifierFan(coordinator)
        asyncio.run(fan.async_turn_on(percentage=100))
        self.assertEqual(
            coordinator.blynk_service.calls, [("power", True), ("mode", "Boost")]
        )

    def test_turn_on_with_sleep_preset_selects_whisper(self):
        coordinator = FakeCoordinator({"power": False, "mode": "Low"})
        fan = fan_module.WindmillPurifierFan(coordinator)
        asyncio.run(fan.async_turn_on(preset_mode="Sleep"))
        self.assertEqual(
            coordinator.blynk_service.calls,
            [
                ("power", True),
                ("mode", "Sleep"),
                ("sleep_style", "Whisper"),
            ],
        )

    def test_unique_id_does_not_contain_token(self):
        coordinator = FakeCoordinator({"power": True, "mode": "Low"})
        fan = fan_module.WindmillPurifierFan(coordinator)
        self.assertNotIn(coordinator.blynk_service.token, fan._attr_unique_id)
        self.assertTrue(fan._attr_unique_id.endswith("_fan"))

    def test_platform_never_adds_fan_for_ac(self):
        coordinator = FakeCoordinator({"power": True, "mode": "Low"})
        coordinator.device_type = const.DEVICE_AC
        self.assertEqual(setup_platform(fan_module, coordinator), [])


class PurifierSensorTests(unittest.TestCase):
    def setUp(self):
        self.coordinator = FakeCoordinator(
            {
                "power": True,
                "mode": "Low",
                "pm25": "2.5",
                "filter_life": 99,
                "air_quality": "Good",
                "wifi_rssi": -52,
            }
        )
        self.descriptions = {
            description.key: description
            for description in sensor_module.SENSOR_DESCRIPTIONS
        }

    def sensor(self, key):
        return sensor_module.WindmillPurifierSensor(
            self.coordinator, self.descriptions[key]
        )

    def test_numeric_and_qualitative_values(self):
        self.assertEqual(self.sensor("pm25").native_value, 2.5)
        self.assertEqual(self.sensor("filter_life").native_value, 99)
        self.assertEqual(self.sensor("air_quality").native_value, "Good")
        self.assertEqual(self.sensor("wifi_rssi").native_value, -52)

    def test_invalid_or_missing_values_remain_unavailable(self):
        self.coordinator.data["pm25"] = "not-a-number"
        self.coordinator.data["air_quality"] = "  "
        self.assertIsNone(self.sensor("pm25").native_value)
        self.assertIsNone(self.sensor("air_quality").native_value)

    def test_setup_adds_only_mapped_sensors_for_purifiers(self):
        entities = setup_platform(sensor_module, self.coordinator)
        self.assertEqual(
            {entity.entity_description.key for entity in entities},
            {"pm25", "filter_life", "air_quality", "wifi_rssi"},
        )
        self.assertFalse(any(entity.entity_description.key == "aqi" for entity in entities))
        self.coordinator.device_type = const.DEVICE_AC
        self.assertEqual(setup_platform(sensor_module, self.coordinator), [])


class PurifierSwitchTests(unittest.TestCase):
    def test_switch_states_and_writes_use_only_mapped_pins(self):
        expected_pins = {"child_lock": "V11", "autofade": "V5", "sound": "V6"}
        descriptions = {
            description.key: description
            for description in switch_module.SWITCH_DESCRIPTIONS
        }
        for key, pin in expected_pins.items():
            with self.subTest(key=key):
                coordinator = FakeCoordinator({key: "1"})
                entity = switch_module.WindmillPurifierSwitch(
                    coordinator, descriptions[key]
                )
                self.assertTrue(entity.is_on)
                asyncio.run(entity.async_turn_off())
                self.assertEqual(coordinator.blynk_service.calls, [("pin", pin, 0)])
                self.assertEqual(coordinator.refreshes, 1)

                coordinator.data[key] = "0"
                self.assertFalse(entity.is_on)
                asyncio.run(entity.async_turn_on())
                self.assertEqual(
                    coordinator.blynk_service.calls,
                    [("pin", pin, 0), ("pin", pin, 1)],
                )

    def test_platform_never_adds_switches_for_ac(self):
        coordinator = FakeCoordinator({"child_lock": 0})
        coordinator.device_type = const.DEVICE_AC
        self.assertEqual(setup_platform(switch_module, coordinator), [])


if __name__ == "__main__":
    unittest.main()
