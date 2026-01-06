"""Button platform for Panasonic Blu-ray integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicBlurayCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Blu-ray buttons from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: PanasonicBlurayCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    async_add_entities([PanasonicBlurayEjectButton(coordinator, entry)])


class PanasonicBlurayEjectButton(
    CoordinatorEntity[PanasonicBlurayCoordinator], ButtonEntity
):
    """Representation of a Panasonic Blu-ray eject button."""

    _attr_has_entity_name = True
    _attr_name = "Eject"
    _attr_icon = "mdi:eject"

    def __init__(
        self,
        coordinator: PanasonicBlurayCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
        """
        super().__init__(coordinator)
        self._host = entry.data[CONF_HOST]
        self._entry = entry

        # Unique ID for this entity
        self._attr_unique_id = f"{self._host}_eject"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information to link this entity to the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            # Other device info is set by media_player entity
        )

    async def async_press(self) -> None:
        """Handle the button press - open/close the disc tray."""
        _LOGGER.debug("Eject button pressed for %s", self.coordinator.device_name)
        await self.coordinator.async_send_command("OP_CL")
