"""Config flow for MVG integration."""
import logging
import mvg_api

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from .const import (
    ATTR_STATION_PRODUCTS,
    CONF_INCLUDE_PRODUCTS,
    CONF_STATION,
    CONF_STATION_ID,
    CONF_LEAD_TIME,
    DEFAULT_LEAD_TIME,
    CONF_INCLUDE_LINES,
)


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

    def get_station_info(self) -> str:
        """Get station information."""
        return mvg_api.get_locations(self.station)[0]


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    api = MvgApi(data["station"])

    station_info = await hass.async_add_executor_job(api.get_station_info)

    if not station_info:
        raise InvalidStation

    # Return info that you want to store in the config entry.
    return {
        "title": station_info["name"],
        ATTR_STATION_PRODUCTS: station_info["products"],
        CONF_STATION_ID: station_info["id"],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MVG."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, data=None):
        """Handle the initial step."""
        if data is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, data)
            # Add some metadata grabbed when validating input
            # to save ourselves some calls to the API
            data[ATTR_STATION_PRODUCTS] = info[ATTR_STATION_PRODUCTS]
            data[CONF_STATION_ID] = info[CONF_STATION_ID]
        except InvalidStation:
            errors["base"] = "invalid_station"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=data)

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
                            CONF_INCLUDE_PRODUCTS,
                            self.config_entry.data[ATTR_STATION_PRODUCTS],
                        ),
                    ): cv.multi_select(self.config_entry.data[ATTR_STATION_PRODUCTS]),
                    vol.Optional(
                        CONF_LEAD_TIME,
                        default=self.config_entry.options.get(
                            CONF_LEAD_TIME, DEFAULT_LEAD_TIME
                        ),
                    ): int,
                }
            ),
        )


class InvalidStation(exceptions.HomeAssistantError):
    """Error to indicate that station is invalid."""
