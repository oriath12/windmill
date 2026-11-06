import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_TYPE,
    CONF_TOKEN,
    DEVICE_AC,
    DEVICE_PURIFIER_MAX,
    DOMAIN,
)
from .purifier_state import device_identifier

class WindmillConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Windmill integration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WindmillOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(device_identifier(user_input[CONF_TOKEN]))
            self._abort_if_unique_id_configured()
            title = (
                "Windmill Air Purifier Max"
                if user_input[CONF_DEVICE_TYPE] == DEVICE_PURIFIER_MAX
                else "Windmill AC"
            )
            return self.async_create_entry(title=title, data=user_input)

        token_selector = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
        schema = vol.Schema({
            vol.Required(CONF_TOKEN): token_selector,
            vol.Required(CONF_DEVICE_TYPE, default=DEVICE_AC): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": DEVICE_AC, "label": "Air conditioner"},
                        {"value": DEVICE_PURIFIER_MAX, "label": "Air Purifier Max"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

class WindmillOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Windmill options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="Windmill Air", data=user_input)

        schema = vol.Schema({
            vol.Required(
                CONF_TOKEN, default=self.config_entry.data.get(CONF_TOKEN)
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        })

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
