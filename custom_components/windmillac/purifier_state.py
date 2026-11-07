"""Pure helpers for Windmill purifier state and entity identity."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from .const import PURIFIER_MAX_PRESETS, PURIFIER_MAX_SPEEDS

# V2 returns display labels while V3 mirrors the corresponding integer mode
# code. Blynk enumerable controls require integer keys for writes.
_MODE_BY_VALUE = {
    "1": "Low",
    "low": "Low",
    "2": "Medium",
    "medium": "Medium",
    "3": "High",
    "high": "High",
    "4": "Boost",
    "boost": "Boost",
    "5": "Eco",
    "eco": "Eco",
    "6": "Sleep",
    "sleep": "Sleep",
}
_VALUE_BY_MODE = {
    "Low": "1",
    "Medium": "2",
    "High": "3",
    "Boost": "4",
    "Eco": "5",
    "Sleep": "6",
}
_SLEEP_STYLE_BY_VALUE = {
    "0": "Whisper",
    "whisper": "Whisper",
    "1": "White Noise",
    "white_noise": "White Noise",
    "white noise": "White Noise",
    "whitenoise": "White Noise",
}
# V4=1 returned HTTP 200 but did not activate White Noise on the tested Max.
# Keep parsing its read state, but only permit the verified Whisper write.
_VALUE_BY_SLEEP_STYLE = {"Whisper": "0"}


def device_identifier(token: str) -> str:
    """Return a stable, non-secret identifier for a device token."""
    return sha256(token.encode("utf-8")).hexdigest()[:16]


def _normalized(value: Any) -> str | None:
    """Normalize a scalar Blynk value for mapping lookup."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip().lower().replace("-", "_")


def parse_purifier_mode(value: Any) -> str | None:
    """Convert a V2 value to a Max speed or preset name."""
    key = _normalized(value)
    return _MODE_BY_VALUE.get(key) if key is not None else None


def purifier_mode_to_pin(mode: str) -> str:
    """Convert a speed or main preset to its integer V2 key."""
    try:
        return _VALUE_BY_MODE[mode]
    except KeyError:
        raise ValueError(f"Unsupported purifier mode: {mode}") from None


def parse_sleep_style(value: Any) -> str | None:
    """Convert a V4 value to Whisper or White Noise."""
    key = _normalized(value)
    return _SLEEP_STYLE_BY_VALUE.get(key) if key is not None else None


def sleep_style_to_pin(style: str) -> str:
    """Convert a sleep style to its integer V4 key."""
    try:
        return _VALUE_BY_SLEEP_STYLE[style]
    except KeyError:
        raise ValueError(f"Unsupported sleep style: {style}") from None


def parse_purifier_switch(value: Any) -> bool | None:
    """Parse common Blynk boolean representations without truthy-string bugs."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = _normalized(value)
    if normalized in {"1", "true", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "off", "disabled"}:
        return False
    return None


def is_manual_speed(mode: str | None) -> bool:
    """Return whether a mode is a manual fan speed."""
    return mode in PURIFIER_MAX_SPEEDS


def is_preset(mode: str | None) -> bool:
    """Return whether a mode is an automatic or sleep preset."""
    return mode in PURIFIER_MAX_PRESETS
