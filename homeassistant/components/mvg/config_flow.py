"""Config flow for MVG integration."""
import logging

import mvg_api
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_DEPARTURES_TO_SHOW,
    CONF_DESTINATION_STATION,
    CONF_DESTINATION_STATION_ID,
    CONF_INCLUDE_LINES,
    CONF_INCLUDE_PRODUCTS,
    CONF_LEAD_TIME,
    CONF_ROUTE,
    CONF_STATION,
    CONF_STATION_ID,
    DEFAULT_DEPARTURES_TO_SHOW,
    DEFAULT_LEAD_TIME,
    STATION_PRODUCTS,
)
from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STATION): cv.string,
        vol.Optional(CONF_NAME, ""): cv.string,
        vol.Optional(CONF_ROUTE, True): bool,
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

    api = MvgApi(data[CONF_STATION])

    station_info = await hass.async_add_executor_job(api.get_station_info)

    if not station_info:
        raise InvalidStation

    # If no custom name is provided, use the name of the
    # station as the name.
    if not CONF_NAME in data and CONF_DESTINATION_STATION not in data:
        data[CONF_NAME] = station_info["name"]

    # Return info that you want to store in the config entry.
    return {
        CONF_STATION: station_info["name"],
        STATION_PRODUCTS: station_info["products"],
        CONF_STATION_ID: station_info["id"],
        CONF_NAME: data[CONF_NAME],
    }


async def validate_route_input(hass: core.HomeAssistant, data):

    api = MvgApi(data[CONF_DESTINATION_STATION])

    station_info = await hass.async_add_executor_job(api.get_station_info)

    if not station_info:
        raise InvalidStation

    # Return info that you want to store in the config entry.
    return {
        CONF_DESTINATION_STATION: station_info["name"],
        CONF_DESTINATION_STATION_ID: station_info["id"],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MVG."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        self.mvg_config = {}

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
            # Add some metadata grabbed when validating input
            # to save ourselves some future calls to the API
            self.mvg_config.update(info)
        except InvalidStation:
            errors["base"] = "invalid_station"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            if CONF_ROUTE in user_input and user_input[CONF_ROUTE]:
                return await self.async_step_route()

            return self.async_create_entry(
                title=self.mvg_config[CONF_NAME], data=self.mvg_config
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_route(self, user_input=None):
        """ Get destination info to complete route"""

        data_schema = {
            vol.Required(CONF_DESTINATION_STATION): str,
        }

        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="route", data_schema=vol.Schema(data_schema)
            )

        if user_input is not None:
            try:
                info = await validate_route_input(self.hass, user_input)
                self.mvg_config.update(info)
            except InvalidStation:
                errors["base"] = "invalid_station"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=self.mvg_config[CONF_NAME], data=self.mvg_config
                )

        return self.async_show_form(
            step_id="route", data_schema=vol.Schema(data_schema), errors=errors
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
                            self.config_entry.data[STATION_PRODUCTS],
                        ),
                    ): cv.multi_select(self.config_entry.data[STATION_PRODUCTS]),
                    vol.Optional(
                        CONF_LEAD_TIME,
                        default=self.config_entry.options.get(
                            CONF_LEAD_TIME, DEFAULT_LEAD_TIME
                        ),
                    ): int,
                    vol.Optional(
                        CONF_DEPARTURES_TO_SHOW,
                        default=self.config_entry.options.get(
                            CONF_DEPARTURES_TO_SHOW, DEFAULT_DEPARTURES_TO_SHOW
                        ),
                    ): cv.positive_int,
                }
            ),
        )


class InvalidStation(exceptions.HomeAssistantError):
    """Error to indicate that station is invalid."""
