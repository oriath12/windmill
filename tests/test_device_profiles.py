"""Dependency-free tests for A/C and purifier coordinator profiles."""

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.windmillac"


def load_module(name: str, path: Path):
    """Load one module without executing the integration's HA-dependent init."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Package stubs allow relative imports while keeping Home Assistant optional.
root = types.ModuleType("custom_components")
root.__path__ = [str(ROOT / "custom_components")]
package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components" / "windmillac")]
sys.modules["custom_components"] = root
sys.modules[PACKAGE] = package

update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")


class DataUpdateCoordinator:
    """Small coordinator stub matching the constructor used by the integration."""

    def __init__(self, hass, logger, name, update_interval):
        self.hass = hass
        self.last_update_success = True


class UpdateFailed(Exception):
    """Stub UpdateFailed exception."""


update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed
sys.modules["homeassistant"] = types.ModuleType("homeassistant")
sys.modules["homeassistant.helpers"] = types.ModuleType("homeassistant.helpers")
sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator

const = load_module(f"{PACKAGE}.const", ROOT / "custom_components/windmillac/const.py")
state = load_module(
    f"{PACKAGE}.purifier_state", ROOT / "custom_components/windmillac/purifier_state.py"
)
coordinator_module = load_module(
    f"{PACKAGE}.coordinator", ROOT / "custom_components/windmillac/coordinator.py"
)


class FakeService:
    """Simulate pin reads and legacy A/C helper methods."""

    token = "secret-device-token"

    def __init__(self, values):
        self.values = values
        self.calls = []

    async def async_get_pin_value(self, pin):
        self.calls.append(pin)
        value = self.values[pin]
        if isinstance(value, Exception):
            raise value
        return value

    async def async_get_mode(self):
        self.calls.append("legacy_mode")
        return "cool"

    async def async_get_fan(self):
        self.calls.append("legacy_fan")
        return "Auto"

    async def async_get_power(self):
        self.calls.append("legacy_power")
        return True


class PurifierStateTests(unittest.TestCase):
    def test_all_max_main_modes_round_trip(self):
        expected = {
            1: "Low",
            2: "Medium",
            3: "High",
            4: "Boost",
            5: "Eco",
            6: "Sleep",
        }
        for raw, mode in expected.items():
            with self.subTest(raw=raw, mode=mode):
                self.assertEqual(state.parse_purifier_mode(raw), mode)
                self.assertEqual(state.parse_purifier_mode(mode), mode)
                self.assertEqual(state.purifier_mode_to_pin(mode), str(raw))

    def test_sleep_styles_round_trip(self):
        expected = {0: "Whisper", 1: "White Noise"}
        for raw, style in expected.items():
            with self.subTest(raw=raw, style=style):
                self.assertEqual(state.parse_sleep_style(raw), style)
                self.assertEqual(state.parse_sleep_style(style), style)
                self.assertEqual(state.sleep_style_to_pin(style), str(raw))
        self.assertEqual(state.parse_sleep_style("white_noise"), "White Noise")

    def test_unknown_values_are_not_misclassified(self):
        self.assertIsNone(state.parse_purifier_mode("White Noise"))
        self.assertIsNone(state.parse_purifier_mode("unexpected"))
        self.assertIsNone(state.parse_sleep_style("unexpected"))

    def test_switch_parser_does_not_treat_zero_string_as_true(self):
        self.assertFalse(state.parse_purifier_switch("0"))
        self.assertTrue(state.parse_purifier_switch("1"))
        self.assertFalse(state.parse_purifier_switch("off"))
        self.assertTrue(state.parse_purifier_switch("enabled"))
        self.assertTrue(state.parse_purifier_switch(1.0))
        self.assertFalse(state.parse_purifier_switch(0.0))
        self.assertIsNone(state.parse_purifier_switch("unknown"))

    def test_device_identifier_is_stable_and_non_secret(self):
        token = "secret-device-token"
        identifier = state.device_identifier(token)
        self.assertEqual(identifier, state.device_identifier(token))
        self.assertNotIn(token, identifier)
        self.assertNotEqual(identifier, state.device_identifier("another-token"))
        self.assertEqual(len(identifier), 16)

    def test_invalid_writes_are_rejected(self):
        with self.assertRaises(ValueError):
            state.purifier_mode_to_pin("White Noise")
        with self.assertRaises(ValueError):
            state.sleep_style_to_pin("Sleep")


class CoordinatorProfileTests(unittest.TestCase):
    def test_legacy_ac_profile_is_unchanged(self):
        service = FakeService({"V1": 72, "V2": 70})
        coordinator = coordinator_module.WindmillDataUpdateCoordinator(None, service)
        data = asyncio.run(coordinator._async_update_data())
        self.assertEqual(
            data,
            {
                "current_temp": 72,
                "target_temp": 70,
                "mode": "cool",
                "fan": "Auto",
                "power": True,
            },
        )
        self.assertEqual(
            service.calls, ["V1", "V2", "legacy_mode", "legacy_fan", "legacy_power"]
        )

    def test_purifier_reads_the_complete_capture_driven_profile(self):
        service = FakeService(
            {
                "V0": 1,
                "V1": 0,
                "V2": "Sleep",
                "V4": "White Noise",
                "V5": 0,
                "V6": 1,
                "V7": 99,
                "V11": 0,
                "V14": -52,
                "V16": "Good",
            }
        )
        coordinator = coordinator_module.WindmillDataUpdateCoordinator(
            None, service, const.DEVICE_PURIFIER_MAX
        )
        data = asyncio.run(coordinator._async_update_data())
        self.assertEqual(
            data,
            {
                "power": True,
                "mode": "Sleep",
                "pm25": 0,
                "sleep_style": "White Noise",
                "autofade": 0,
                "sound": 1,
                "filter_life": 99,
                "child_lock": 0,
                "wifi_rssi": -52,
                "air_quality": "Good",
            },
        )
        self.assertEqual(
            service.calls,
            ["V0", "V2", "V1", "V4", "V5", "V6", "V7", "V11", "V14", "V16"],
        )
        for unknown_pin in ("V8", "V9", "V10", "V12", "V15"):
            self.assertNotIn(unknown_pin, service.calls)

    def test_optional_pin_failure_does_not_break_primary_controls(self):
        service = FakeService(
            {
                "V0": 0,
                "V1": Exception("unsupported"),
                "V2": "Eco",
                "V4": "Whisper",
            }
        )
        coordinator = coordinator_module.WindmillDataUpdateCoordinator(
            None, service, const.DEVICE_PURIFIER_MAX
        )
        data = asyncio.run(coordinator._async_update_data())
        self.assertFalse(data["power"])
        self.assertEqual(data["mode"], "Eco")
        self.assertIsNone(data["pm25"])
        self.assertEqual(data["sleep_style"], "Whisper")
        self.assertIsNone(data["air_quality"])
        self.assertEqual(
            service.calls,
            ["V0", "V2", "V1", "V4", "V5", "V6", "V7", "V11", "V14", "V16"],
        )

    def test_missing_required_purifier_pin_raises_update_failed(self):
        service = FakeService({"V0": 1})
        coordinator = coordinator_module.WindmillDataUpdateCoordinator(
            None, service, const.DEVICE_PURIFIER_MAX
        )
        with self.assertRaises(UpdateFailed):
            asyncio.run(coordinator._async_update_data())


if __name__ == "__main__":
    unittest.main()
