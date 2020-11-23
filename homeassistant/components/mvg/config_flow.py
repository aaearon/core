"""Config flow for MVG integration."""
import logging
import mvg_api

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from .const import ALL_PRODUCTS, CONF_INCLUDE_PRODUCTS, CONF_STATION


from homeassistant import config_entries, core, exceptions

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STATION): cv.string,
    }
)


class MvgApi:
    def __init__(self, station):
        self.station = station

    def check_if_station_exists(self) -> str:
        """Test if the station exists."""
        station_id = mvg_api.get_id_for_station(self.station)
        if station_id:
            return station_id


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    api = MvgApi(data["station"])

    if not await hass.async_add_executor_job(api.check_if_station_exists):
        raise InvalidStation

    # Return info that you want to store in the config entry.
    return {"title": data[CONF_STATION]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MVG."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except InvalidStation:
            errors["base"] = "invalid_station"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(title="", data=self.options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INCLUDE_PRODUCTS,
                        default=self.config_entry.options.get(
                            CONF_INCLUDE_PRODUCTS, ALL_PRODUCTS
                        ),
                    ): cv.multi_select(ALL_PRODUCTS),
                }
            ),
        )


class InvalidStation(exceptions.HomeAssistantError):
    """Error to indicate that station is invalid."""
