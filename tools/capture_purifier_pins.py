#!/usr/bin/env python3
"""Read-only Windmill purifier pin capture; never calls Blynk's update API."""

from __future__ import annotations

import argparse
import getpass
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://dashboard.windmillair.com/external/api/get"
PINS = [f"V{number}" for number in range(41)]
ACTIONS = [
    ("baseline", "On, Eco mode, child lock off, lights on, sounds on"),
    ("low", "Select Low speed"),
    ("medium", "Select Medium speed"),
    ("high", "Select High speed"),
    ("boost", "Select Boost speed"),
    ("sleep", "Select Sleep mode"),
    ("whisper", "Optional: select Whisper if it is a separate app mode; otherwise skip"),
    ("white_noise", "Optional: select White Noise if it is a separate app mode; otherwise skip"),
    ("eco", "Select Eco mode"),
    ("child_lock_on", "Enable child lock"),
    ("child_lock_off", "Disable child lock"),
    ("lights_off", "Turn Autofade off; if your app has a separate Display lights control, turn that off instead"),
    ("lights_on", "Turn Autofade on; if your app has a separate Display lights control, turn that on instead"),
    ("sound_off", "Turn button sounds off"),
    ("sound_on", "Turn button sounds on"),
    ("power_off", "Turn the purifier off"),
    ("power_on", "Turn the purifier on"),
]


def read_pin(token: str, pin: str, timeout: float) -> dict:
    """Read one pin and return only token-free response information."""
    query = urllib.parse.urlencode({"token": token})
    url = f"{BASE_URL}?{query}&{pin}"
    request = urllib.request.Request(url, headers={"User-Agent": "WindmillAC-pin-research/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"value": response.read().decode("utf-8", "replace").strip()}
    except urllib.error.HTTPError as err:
        return {"value": None, "http_status": err.code}
    except (urllib.error.URLError, TimeoutError) as err:
        reason = getattr(err, "reason", "timeout")
        return {"value": None, "error": str(reason)[:160]}


def snapshot(token: str, timeout: float) -> dict:
    """Read all candidate pins sequentially."""
    return {pin: read_pin(token, pin, timeout) for pin in PINS}


def changed_pins(before: dict | None, after: dict) -> dict:
    """Summarize raw value changes between two captures."""
    if before is None:
        return {}
    return {
        pin: {"before": before[pin]["value"], "after": after[pin]["value"]}
        for pin in PINS
        if before[pin]["value"] != after[pin]["value"]
    }


def main() -> None:
    """Capture user-driven states without writing to the purifier."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="purifier-pin-capture.json")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    print("This script is READ-ONLY. Your token is not written to the output file.")
    token = getpass.getpass("Windmill device token (hidden input): ").strip()
    if not token:
        raise SystemExit("A token is required.")

    captures = []
    previous = None
    for index, (key, instruction) in enumerate(ACTIONS):
        print(f"\n[{index + 1}/{len(ACTIONS)}] {instruction}")
        answer = input("Press Enter when ready, or type s to skip: ").strip().lower()
        if answer == "s":
            continue
        time.sleep(args.delay)
        current = snapshot(token, args.timeout)
        changes = changed_pins(previous, current)
        captures.append({"action": key, "instruction": instruction, "pins": current, "changes": changes})
        readable = sum(item["value"] is not None for item in current.values())
        print(f"Readable pins: {readable}/{len(PINS)}; changed since previous capture: {len(changes)}")
        if changes:
            print(json.dumps(changes, indent=2))
        previous = current

    result = {
        "schema": 1,
        "device": "Windmill Air Purifier Max",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": "GET external/api/get only; no update calls",
        "captures": captures,
    }
    output = Path(args.output)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nSaved token-free capture to {output.resolve()}")
    print("Upload that JSON file for mapping analysis; do not post your device token.")


if __name__ == "__main__":
    main()
