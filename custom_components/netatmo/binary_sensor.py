"""Support for the Netatmo sensors."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import cast

import pyatmo

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
    BinarySensorEntity,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONCENTRATION_PARTS_PER_MILLION,
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfPower,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSoundPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import async_entries_for_config_entry
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_OPEN,
    CONF_URL_ENERGY,
    CONF_URL_PUBLIC_WEATHER,
    CONF_URL_SECURITY,
    CONF_URL_WEATHER,
    CONF_WEATHER_AREAS,
    DATA_HANDLER,
    DOMAIN,
    NETATMO_CREATE_BATTERY,
    NETATMO_CREATE_DOORTAG_SENSOR,
    NETATMO_CREATE_ROOM_SENSOR,
    NETATMO_CREATE_SENSOR,
    NETATMO_CREATE_WEATHER_SENSOR,
    SIGNAL_NAME,
)
from .data_handler import HOME, PUBLIC, NetatmoDataHandler, NetatmoDevice, NetatmoRoom
from .helper import NetatmoArea
from .netatmo_entity_base import NetatmoBase

_LOGGER = logging.getLogger(__name__)

@dataclass
class NetatmoRequiredKeysMixin:
    """Mixin for required keys."""

    netatmo_name: str


@dataclass
class NetatmoBinarySensorEntityDescription(BinarySensorEntityDescription, NetatmoRequiredKeysMixin):
    """Describes Netatmo binary sensor entity."""

DOORTAG_SENSOR_DESCRIPTION = NetatmoBinarySensorEntityDescription(
    key="doortag",
    name="Door Tag",
    netatmo_name="doortag",
    device_class=BinarySensorDeviceClass.OPENING,
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Netatmo binary sensor devices."""

    @callback
    def _create_doortag_entity(netatmo_device: NetatmoDevice) -> None:
        entity = NetatmoCamDoorTagBinarySensor(netatmo_device)
        async_add_entities([entity])

    entry.async_on_unload(
        async_dispatcher_connect(hass, NETATMO_CREATE_DOORTAG_SENSOR, _create_doortag_entity)
    )

class NetatmoCamDoorTagBinarySensor(NetatmoBase, BinarySensorEntity):
    """Implementation of a Netatmo binary sensor."""

    entity_description: NetatmoBinarySensorEntityDescription

    def __init__(
        self,
        netatmo_device: NetatmoDevice,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(netatmo_device.data_handler)
        self.entity_description = DOORTAG_SENSOR_DESCRIPTION
        self._device_class = DOORTAG_SENSOR_DESCRIPTION.device_class

        self._module = cast(pyatmo.modules.NACamDoorTag, netatmo_device.device)
        self._id = self._module.entity_id
        self._device_name = self._module.name

        self._publishers.extend(
            [
                {
                    "name": HOME,
                    "home_id": netatmo_device.device.home.entity_id,
                    SIGNAL_NAME: netatmo_device.signal_name,
                },
            ]
        )

        self._attr_name = f"{self._module.name} {self.entity_description.name}"
        self._room_id = self._module.room_id
        self._model = getattr(self._module.device_type, "value")
        self._config_url = CONF_URL_SECURITY

        self._attr_unique_id = (
            f"{self._id}-{self._module.entity_id}-{self.entity_description.key}"
        )

    @callback
    def async_update_callback(self) -> None:
        """Update the entity's state."""
        if not self._module.reachable:
            if self.available:
                self._attr_available = False
                self._attr_native_value = None
            return

        self._attr_available = True
        self._attr_native_value = self._module.status == ATTR_OPEN

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self._module.status == ATTR_OPEN
