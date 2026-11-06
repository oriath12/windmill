"""Constants for the Windmill Air integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Windmill Air"
DOMAIN = "windmillac"
VERSION = "1.1.0"
PLATFORMS = ["climate", "fan", "sensor", "switch"]
UPDATE_INTERVAL = 60
REQUEST_TIMEOUT = 15
CONF_TOKEN = "token"
CONF_DEVICE_TYPE = "device_type"
BASE_URL = "https://dashboard.windmillair.com"

DEVICE_AC = "ac"
DEVICE_PURIFIER_MAX = "purifier_max"
DEVICE_TYPES = (DEVICE_AC, DEVICE_PURIFIER_MAX)
DEFAULT_DEVICE_TYPE = DEVICE_AC

# Verified by token-free, read-only captures of the user's Air Purifier Max.
# V8, V9, V10, V12, and V15 remain unmapped because their semantics were not
# established. Unknown pins are deliberately not polled or written.
PURIFIER_MAX_PINS = {
    "power": "V0",
    "pm25": "V1",
    "mode": "V2",
    "sleep_style": "V4",
    "autofade": "V5",
    "sound": "V6",
    "filter_life": "V7",
    "child_lock": "V11",
    "wifi_rssi": "V14",
    "air_quality": "V16",
}

PURIFIER_MAX_MODEL = "Air Purifier Max"
PURIFIER_MAX_SPEEDS = ("Low", "Medium", "High", "Boost")
# Sleep always selects Whisper; White Noise is the alternate sleep style.
PURIFIER_MAX_PRESETS = ("Eco", "Sleep", "White Noise")
PURIFIER_MAX_SLEEP_STYLES = ("Whisper", "White Noise")
