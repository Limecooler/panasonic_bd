"""Media player platform for Panasonic Blu-ray integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PanasonicBlurayCoordinator, PanasonicBlurayData

_LOGGER = logging.getLogger(__name__)

# Map internal states to MediaPlayerState
STATE_MAP = {
    "off": MediaPlayerState.OFF,
    "standby": MediaPlayerState.OFF,
    "stopped": MediaPlayerState.IDLE,
    "playing": MediaPlayerState.PLAYING,
    "paused": MediaPlayerState.PAUSED,
    "unknown": None,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Panasonic Blu-ray media player from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry
        async_add_entities: Callback to add entities
    """
    coordinator: PanasonicBlurayCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    async_add_entities([PanasonicBlurayMediaPlayer(coordinator, entry)])


class PanasonicBlurayMediaPlayer(
    CoordinatorEntity[PanasonicBlurayCoordinator], MediaPlayerEntity
):
    """Representation of a Panasonic Blu-ray media player."""

    _attr_has_entity_name = True
    _attr_name = None  # Use device name as entity name
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
    )

    def __init__(
        self,
        coordinator: PanasonicBlurayCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the media player.

        Args:
            coordinator: Data update coordinator
            entry: Config entry
        """
        super().__init__(coordinator)
        self._host = entry.data[CONF_HOST]
        self._entry = entry

        # Unique ID for this entity
        self._attr_unique_id = f"{self._host}_media_player"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name=self.coordinator.device_name,
            manufacturer="Panasonic",
            model=f"Blu-ray Player ({self.coordinator.data.player_type.value if self.coordinator.data else 'unknown'})",
        )

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the current state of the player."""
        if self.coordinator.data is None:
            return None
        return STATE_MAP.get(self.coordinator.data.state, None)

    @property
    def media_position(self) -> int | None:
        """Return the current playback position in seconds."""
        if self.coordinator.data is None:
            return None
        position = self.coordinator.data.media_position
        return position if position > 0 else None

    @property
    def media_position_updated_at(self):
        """Return when position was last updated."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.media_position_updated_at

    @property
    def media_duration(self) -> int | None:
        """Return the total duration in seconds (BD players only)."""
        if self.coordinator.data is None:
            return None
        duration = self.coordinator.data.media_duration
        return duration if duration > 0 else None

    @property
    def media_track(self) -> int | None:
        """Return the current chapter number (BD players only)."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.chapter_current

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes (OpenHAB feature parity)."""
        if self.coordinator.data is None:
            return {}

        attrs: dict[str, Any] = {
            "player_status": self.coordinator.data.player_status,
            "player_type": self.coordinator.data.player_type.value,
        }

        # BD players have chapter info
        if self.coordinator.data.chapter_current is not None:
            attrs["chapter_current"] = self.coordinator.data.chapter_current
        if self.coordinator.data.chapter_total is not None:
            attrs["chapter_total"] = self.coordinator.data.chapter_total

        return attrs

    async def async_turn_on(self) -> None:
        """Turn on the player (wake from standby)."""
        # If already on, do nothing
        if self.state not in (MediaPlayerState.OFF, None):
            return
        await self.coordinator.async_send_command("POWER")

    async def async_turn_off(self) -> None:
        """Turn off the player (go to standby)."""
        # If already off, do nothing
        if self.state == MediaPlayerState.OFF:
            return
        await self.coordinator.async_send_command("POWER")

    async def async_media_play(self) -> None:
        """Start playback."""
        await self.coordinator.async_send_command("PLAYBACK")

    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self.coordinator.async_send_command("PAUSE")

    async def async_media_stop(self) -> None:
        """Stop playback."""
        await self.coordinator.async_send_command("STOP")

    async def async_media_next_track(self) -> None:
        """Skip to next chapter."""
        await self.coordinator.async_send_command("SKIPFWD")

    async def async_media_previous_track(self) -> None:
        """Skip to previous chapter."""
        await self.coordinator.async_send_command("SKIPREV")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
