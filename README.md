# Windmill Air for Home Assistant

A community integration for **Windmill air conditioners** and the **Windmill Air Purifier Max**. It extends [`bzellman/WindmillAC`](https://github.com/bzellman/WindmillAC) with a separate purifier profile, so a purifier is represented as a **fan**, not as an air-conditioner `climate` entity.

> **Unofficial software:** This project is not associated with, supported by, or endorsed by Windmill. Cloud behavior can change without notice. Use it at your own risk.

## Supported entities

Add each physical device separately with its own auth token and device type.

| Configured device | Home Assistant entities |
| --- | --- |
| Air conditioner | One `climate` entity with temperature, HVAC mode, fan mode, and power controls, preserving the upstream integration’s behavior |
| Air Purifier Max | One `fan` entity; PM2.5, filter-life, qualitative air-quality, and optional Wi-Fi signal sensors; Child lock, Autofade, and Button sounds switches |

The purifier fan exposes four manual speeds as percentages: **Low 25%**, **Medium 50%**, **High 75%**, and **Boost 100%**. Its presets are **Eco** and **Sleep** (Sleep with Whisper). White Noise remains available in the official Windmill app but is not exposed by this integration because its inferred write command did not work on the tested purifier. If White Noise is selected in the app, Home Assistant reports the broader **Sleep** preset after its next poll. The qualitative air-quality sensor reports labels such as `Good`; it is not presented as a numeric AQI measurement. The Wi-Fi signal sensor is disabled by default because its pin assignment is less certain than the primary controls.

> **Hardware-validation status:** The purifier’s read mappings were verified with token-free captures from an Air Purifier Max, and user testing confirmed the primary controls and switches. An isolated `V4=1` write returned HTTP 200 but never changed the settled state from Whisper to White Noise. Version 1.1.1 therefore removes White Noise as a writable option rather than sending a command known not to work. Sleep continues to select Whisper.

## Requirements

- Home Assistant **2024.4.0 or newer**
- A Windmill device available in the [Windmill Air Dashboard](https://dashboard.windmillair.com)
- The device’s auth token
- A public GitHub repository for Marketplace/HACS installation, or manual access to the Home Assistant `config` directory

Home Assistant **2026.11 and newer** includes the Marketplace under **Settings → Marketplace**. Earlier versions use HACS as a separate custom integration.

## Install on Home Assistant 2026.11 or newer

1. Open **Settings → Marketplace**.
2. Select **Add from link** in the upper-right corner.
3. Enter `https://github.com/oriath12/windmill`.
4. Select **Add**. If Home Assistant asks for a type, choose **Integration**. A GitHub connection may be requested for a custom repository.
5. Open the repository in the Marketplace and select **Install**.
6. If you replaced an existing copy of `windmillac`, restart Home Assistant before configuring devices so the updated code is loaded.

See the [Marketplace custom-repository documentation](https://www.home-assistant.io/integrations/marketplace/#custom-repositories) for the current interface and GitHub-connection behavior.

## Install with HACS on Home Assistant 2026.10 or older

1. Install and configure HACS if it is not already available.
2. Open **HACS → Integrations → three-dot menu → Custom repositories**.
3. Enter your repository URL and select **Integration** as the category.
4. Add the repository, find **Windmill Air**, and select **Download**.
5. Restart Home Assistant.

## Manual installation alternative

Copy the `custom_components/windmillac` directory into your Home Assistant `config/custom_components` directory. The resulting path must be:

```text
/config/custom_components/windmillac/manifest.json
```

Restart Home Assistant after copying or replacing the files. On a Home Assistant Green, use a file-editing method you already trust, such as the Samba or SSH add-on; do not run the diagnostic Python utility on the Green itself.

## Configure both devices

1. Open **Settings → Devices & services → Add integration**.
2. Search for **Windmill Air**.
3. Enter the A/C token and select **Air conditioner**.
4. Repeat the flow with the purifier token and select **Air Purifier Max**.
5. Confirm that the A/C creates a `climate` entity and the purifier creates a `fan` plus sensors and switches.

The token field is masked in the configuration UI. Separate config entries allow the two devices to use different pin profiles without sharing entity types or state.

## Physical purifier write-test checklist

Test these actions manually while watching both Home Assistant and the Windmill app/device. Allow several seconds for cloud state to synchronize.

- [ ] Power off and on.
- [ ] Low, Medium, High, and Boost; confirm 25/50/75/100% maps to the correct physical speed.
- [ ] Eco.
- [ ] Sleep; confirm Sleep with Whisper is selected.
- [ ] Child lock on and off.
- [ ] Autofade on and off.
- [ ] Button sounds on and off.
- [ ] Change a setting in the Windmill app and confirm Home Assistant reflects it after the next poll.
- [ ] Check PM2.5, filter life, and qualitative air quality against the Windmill dashboard.

If a write does not match, **stop using that control and do not try unknown pins**. Capture the expected and actual entity state, the non-secret Home Assistant log message, and the Windmill app state for troubleshooting.

## Polling, availability, and privacy

The integration polls `https://dashboard.windmillair.com` every 60 seconds using the existing Blynk-compatible HTTPS API. Requests have a 15-second timeout. A failure of an optional purifier sensor does not disable primary power and mode control, although the affected sensor becomes unknown until a later successful poll.

Purifier entity and config-entry identifiers use a shortened SHA-256 token hash instead of embedding the raw token. Debug logging does not include request URLs or raw response bodies. The legacy A/C entity IDs are deliberately unchanged for compatibility, so existing A/C installations retain the upstream integration’s raw-token identifier behavior; avoid publishing legacy entity IDs or diagnostics without reviewing them.

The read-only utility at `tools/capture_purifier_pins.py` calls only `external/api/get`, accepts the token through hidden input, and writes token-free JSON. It is a development diagnostic, not an integration dependency.

## Troubleshooting

- **The purifier still appears as an A/C:** Remove the incorrectly configured purifier entry, restart after installing the updated files, and add the purifier again with **Air Purifier Max** selected. Do not delete a correctly working A/C entry.
- **Windmill Air does not appear in Add integration:** Confirm `manifest.json` is at the path shown above, then restart and check the Home Assistant log.
- **Required-pin errors:** Verify that the token belongs to the selected device type and that the device is online in the Windmill dashboard.
- **A sensor is unknown but power works:** An optional pin may be temporarily unavailable or may differ on another firmware revision. Primary controls intentionally remain available.
- **State changes lag:** This is a cloud-polling integration with a 60-second interval; wait for a refresh rather than sending repeated writes.
- **Marketplace rejects the repository:** Ensure the GitHub repository is public and contains root-level `hacs.json` and `README.md`, plus `custom_components/windmillac/manifest.json`.

## Development validation

The tests use Home Assistant stubs and do not contact real devices:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components/windmillac tests
```

They cover legacy A/C reads, capture-derived purifier reads, all main modes, read parsing for both sleep styles, rejection of the unverified White Noise write, sensor values, switch writes, fan percentages, Eco/Sleep presets, platform isolation, integer-enum writes, request timeouts, and token-safe logging. Passing these tests is not a substitute for physical validation.

## Research and attribution

The [research and implementation report](docs/research-report.md) documents the root cause, public evidence, capture-derived pin map, entity design, security boundaries, test results, and remaining physical-validation limits.

This work is based on [Bradley Zellman’s WindmillAC integration](https://github.com/bzellman/WindmillAC). The related [`markuswinkler/WindmillFan`](https://github.com/markuswinkler/WindmillFan) fork provided useful architectural context, but its older five-speed mapping was not reused for the Air Purifier Max. The Max profile in this repository comes from the separate read-only captures described above.

Distributed under the MIT License. See `LICENSE`.
