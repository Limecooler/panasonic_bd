"""DataUpdateCoordinator for Panasonic Blu-ray integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PanasonicBlurayApi, PlayStatus
from .const import DOMAIN, PlayerType, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class PanasonicBlurayData:
    """Data class for Panasonic Blu-ray player state."""

    state: str  # "off", "standby", "stopped", "playing", "paused", "unknown"
    player_status: str  # Human-readable status (OpenHAB: player-status)
    media_position: int  # Playback position in seconds
    media_position_updated_at: datetime | None  # When position was last updated
    media_duration: int  # Total duration in seconds (BD only)
    chapter_current: int | None  # Current chapter (BD only)
    chapter_total: int | None  # Total chapters (BD only)
    player_type: PlayerType  # BD or UHD


class PanasonicBlurayCoordinator(DataUpdateCoordinator[PanasonicBlurayData]):
    """Coordinator for polling Panasonic Blu-ray player status."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: PanasonicBlurayApi,
        device_name: str,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            api: Panasonic Blu-ray API client
            device_name: Friendly name for the device
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self.device_name = device_name
        self._consecutive_errors = 0
        self._max_consecutive_errors = 3

    async def _async_update_data(self) -> PanasonicBlurayData:
        """Fetch data from the player.

        Returns:
            PanasonicBlurayData with current state

        Raises:
            UpdateFailed: If unable to fetch data after retries
        """
        try:
            play_status = await self.api.async_get_play_status()

            # Reset error counter on success
            self._consecutive_errors = 0

            return PanasonicBlurayData(
                state=play_status.state,
                player_status=play_status.status_string,
                media_position=play_status.position,
                media_position_updated_at=datetime.now(),
                media_duration=play_status.duration,
                chapter_current=play_status.chapter_current,
                chapter_total=play_status.chapter_total,
                player_type=self.api.player_type,
            )

        except Exception as err:
            self._consecutive_errors += 1

            # Silver tier: Don't spam logs with repeated errors
            if self._consecutive_errors <= self._max_consecutive_errors:
                _LOGGER.warning(
                    "Error communicating with %s (%d/%d): %s",
                    self.device_name,
                    self._consecutive_errors,
                    self._max_consecutive_errors,
                    err,
                )
            elif self._consecutive_errors == self._max_consecutive_errors + 1:
                _LOGGER.error(
                    "Repeated errors communicating with %s, "
                    "suppressing further warnings until resolved",
                    self.device_name,
                )

            # Return last known data if available, otherwise raise
            if self.data is not None:
                # Mark as unavailable but keep last known state
                return PanasonicBlurayData(
                    state="off",
                    player_status="Unavailable",
                    media_position=0,
                    media_position_updated_at=None,
                    media_duration=0,
                    chapter_current=None,
                    chapter_total=None,
                    player_type=self.api.player_type,
                )

            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def async_send_command(self, command: str) -> bool:
        """Send a command to the player.

        Args:
            command: Command to send

        Returns:
            True if command succeeded
        """
        result = await self.api.async_send_command(command)
        if result.success:
            # Trigger a refresh after command
            await self.async_request_refresh()
        return result.success
