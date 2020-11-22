"""Config flow for MVG integration."""
import logging
import mvg_api

import voluptuous as vol

from homeassistant import config_entries, core, exceptions

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required("station"): str})


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
    station_id = await hass.async_add_executor_job(api.check_if_station_exists)

    if not station_id:
        raise InvalidStation

    # Return info that you want to store in the config entry.
    return {"title": data["station"], "station_id": station_id}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MVG."""

    VERSION = 1
    # TODO pick one of the available connection classes in homeassistant/config_entries.py
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

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


class InvalidStation(exceptions.HomeAssistantError):
    """Error to indicate that station is invalid."""
