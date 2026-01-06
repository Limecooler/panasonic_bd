"""Remote platform for Panasonic Blu-ray integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable

from homeassistant.components.media_player import MediaPlayerState
from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COMMANDS, COMMAND_ALIASES, COMMAND_DESCRIPTIONS, DOMAIN
from .coordinator import PanasonicBlurayCoordinator

_LOGGER = logging.getLogger(__name__)

# Default delay between commands
DEFAULT_COMMAND_DELAY = 0.4


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Blu-ray remote from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: PanasonicBlurayCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    async_add_entities([PanasonicBlurayRemote(coordinator, entry)])


class PanasonicBlurayRemote(
    CoordinatorEntity[PanasonicBlurayCoordinator], RemoteEntity
):
    """Representation of a Panasonic Blu-ray remote."""

    _attr_has_entity_name = True
    _attr_name = "Remote"  # Will show as "Device Name Remote"

    def __init__(
        self,
        coordinator: PanasonicBlurayCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the remote.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
        """
        super().__init__(coordinator)
        self._host = entry.data[CONF_HOST]
        self._entry = entry

        # Unique ID for this entity
        self._attr_unique_id = f"{self._host}_remote"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information to link this entity to the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            # Other device info is set by media_player entity
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if device is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.state not in ("off", "standby", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes including available commands."""
        attrs: dict[str, Any] = {
            "available_commands": sorted(COMMANDS),
            "available_aliases": sorted(COMMAND_ALIASES.keys()),
        }

        if self.coordinator.data is not None:
            attrs["player_type"] = self.coordinator.data.player_type.value

        return attrs

    def _resolve_command(self, cmd: str) -> str | None:
        """Resolve command or alias to actual command.

        Args:
            cmd: Command name or alias

        Returns:
            Resolved command name, or None if not found
        """
        # Check direct command (case-insensitive)
        cmd_upper = cmd.upper()
        if cmd_upper in COMMANDS:
            return cmd_upper

        # Check alias (case-insensitive)
        cmd_lower = cmd.lower()
        if cmd_lower in COMMAND_ALIASES:
            return COMMAND_ALIASES[cmd_lower]

        return None

    async def async_turn_on(self, activity: str | None = None, **kwargs: Any) -> None:
        """Turn on the device.

        Args:
            activity: Optional activity (not used)
            **kwargs: Additional arguments (not used)
        """
        await self.coordinator.async_send_command("POWER")

    async def async_turn_off(self, activity: str | None = None, **kwargs: Any) -> None:
        """Turn off the device.

        Args:
            activity: Optional activity (not used)
            **kwargs: Additional arguments (not used)
        """
        await self.coordinator.async_send_command("POWER")

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send commands to the device.

        Supports both native Panasonic commands (e.g., "PLAYBACK") and
        intuitive aliases (e.g., "play"). Commands are case-insensitive.

        Args:
            command: List of commands or aliases to send
            **kwargs: Additional arguments (num_repeats, delay_secs)
        """
        num_repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay_secs = kwargs.get(ATTR_DELAY_SECS, DEFAULT_COMMAND_DELAY)

        for _ in range(num_repeats):
            for cmd in command:
                resolved_cmd = self._resolve_command(cmd)

                if resolved_cmd is None:
                    _LOGGER.warning(
                        "Unknown command or alias: %s. Use 'available_commands' or "
                        "'available_aliases' attributes to see valid options.",
                        cmd,
                    )
                    continue

                _LOGGER.debug("Sending command: %s (from: %s)", resolved_cmd, cmd)
                result = await self.coordinator.api.async_send_command(resolved_cmd)

                if not result.success:
                    _LOGGER.warning(
                        "Command %s failed: %s",
                        resolved_cmd,
                        result.error or "Unknown error",
                    )

                # Delay between commands
                if delay_secs > 0:
                    await asyncio.sleep(delay_secs)

        # Refresh state after commands
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
