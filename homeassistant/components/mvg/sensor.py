"""Platform for sensor integration."""
from homeassistant.components import mvg

from datetime import timedelta
import mvg_api
from homeassistant.const import TEMP_CELSIUS, TIME_MINUTES
from homeassistant.helpers.entity import Entity

from .const import CONF_STATION, CONF_INCLUDE_PRODUCTS, ALL_PRODUCTS

SCAN_INTERVAL = timedelta(seconds=30)
ICONS = {
    "UBAHN": "mdi:subway",
    "TRAM": "mdi:tram",
    "BUS": "mdi:bus",
    "SBAHN": "mdi:train",
}


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up entry."""

    include_products = config_entry.options.get(CONF_INCLUDE_PRODUCTS, ALL_PRODUCTS)

    async_add_devices(
        [
            MvgSensor(
                name=config_entry.data[CONF_STATION], include_products=include_products
            )
        ]
    )


class MvgSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, include_products):
        """Initialize the sensor."""
        self._name = name
        self._state = None
        self._icon = None
        self.include_products = include_products

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

        attributes = self.departures[0]
        attributes["upcoming_departures"] = self.departures[1:5]

        return attributes

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """

        station_id = mvg_api.get_id_for_station(self._name)

        if station_id:
            desired_departures = []
            results = mvg_api.get_departures(station_id)

            # The API sometimes returns departures that are extremely
            # in the past (sometimes up to 25 minutes in the past)
            # so we find and remove those. Departures that are "just
            # missed" (5 minutes ago) we keep as it may be helpful
            # to have in some use cases.
            for departure in results:
                if (
                    departure["departureTimeMinutes"] > -5
                    and departure["product"] in self.include_products
                ):
                    desired_departures.append(departure)

            # The API will return an unsorted list of departures so we need to
            # sort on departureTimeMinutes so that we get the soonest departure
            # first.
            self.departures = sorted(
                desired_departures, key=lambda x: (x["departureTimeMinutes"])
            )

            if self.departures:
                self._state = self.departures[0]["departureTimeMinutes"]
                self._icon = ICONS[self.departures[0].get("product")]
            else:
                self._state = "-"
                self._icon = "mdi:clock"
