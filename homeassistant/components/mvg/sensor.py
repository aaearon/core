"""Platform for sensor integration."""
from datetime import timedelta

import mvg_api

from homeassistant.components import mvg
from homeassistant.const import ATTR_ATTRIBUTION, TIME_MINUTES, CONF_NAME
from homeassistant.helpers.entity import Entity

from .const import (
    CONF_DEPARTURES_TO_SHOW,
    CONF_INCLUDE_PRODUCTS,
    CONF_LEAD_TIME,
    CONF_STATION,
    CONF_STATION_ID,
    DATA_ATTRIBUTION,
    DEFAULT_DEPARTURES_TO_SHOW,
    DEFAULT_LEAD_TIME,
    STATION_PRODUCTS,
)

SCAN_INTERVAL = timedelta(seconds=30)
ICONS = {
    "UBAHN": "mdi:subway",
    "TRAM": "mdi:tram",
    "BUS": "mdi:bus",
    "SBAHN": "mdi:train",
}


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up entry."""

    include_products = config_entry.options.get(
        CONF_INCLUDE_PRODUCTS, config_entry.data[STATION_PRODUCTS]
    )
    lead_time = config_entry.options.get(CONF_LEAD_TIME, DEFAULT_LEAD_TIME)
    departures_to_show = config_entry.options.get(
        CONF_DEPARTURES_TO_SHOW, DEFAULT_DEPARTURES_TO_SHOW
    )

    async_add_devices(
        [
            MvgSensor(
                name=config_entry.data[CONF_NAME],
                station=config_entry.data[CONF_STATION],
                station_id=config_entry.data[CONF_STATION_ID],
                include_products=include_products,
                lead_time=lead_time,
                departures_to_show=departures_to_show,
            )
        ],
        True,
    )


class MvgSensor(Entity):
    """Representation of a Sensor."""

    def __init__(
        self, name, station, station_id, include_products, lead_time, departures_to_show
    ):
        """Initialize the sensor."""
        self._name = name
        self._station = station
        self._station_id = station_id
        self._state = None
        self._icon = None
        self.include_products = include_products
        self.lead_time = lead_time
        self.departures_to_show = departures_to_show

        self.data = MvgDepartureData(self._station_id)
        self.departures = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TIME_MINUTES

    @property
    def device_state_attributes(self):
        if not self.departures:
            return None

        attributes = {}
        attributes["station"] = self._station
        attributes[ATTR_ATTRIBUTION] = DATA_ATTRIBUTION
        attributes.update(self.departures[0])
        attributes["upcoming_departures"] = self.departures[: self.departures_to_show]

        return attributes

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self.data.update()

        desired_departures = []

        for departure in self.data.departures:
            if (
                departure["departureTimeMinutes"] > self.lead_time
                and departure["product"] in self.include_products
            ):
                desired_departures.append(departure)

        # The API will return an unsorted list of departures so we need to
        # sort on departureTimeMinutes so that we get the soonest departure
        # first. departureTime does not take into account any delay.
        self.departures = sorted(
            desired_departures, key=lambda x: (x["departureTimeMinutes"])
        )

        if self.departures:
            self._state = self.departures[0]["departureTimeMinutes"]
            self._icon = ICONS[self.departures[0].get("product")]
        else:
            self._state = "-"
            self._icon = "mdi:clock"


class MvgDepartureData:
    def __init__(self, station_id):
        self._station_id = station_id
        self.departures = []

    def update(self):
        self.departures = mvg_api.get_departures(self._station_id)
