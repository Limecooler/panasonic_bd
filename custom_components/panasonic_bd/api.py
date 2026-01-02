"""Async API client for Panasonic Blu-ray players."""
from __future__ import annotations

import asyncio
import gzip
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

from .const import (
    API_ENDPOINT,
    API_USER_AGENT,
    COMMANDS,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    PlayerStatus,
    PlayerType,
)

_LOGGER = logging.getLogger(__name__)


class PanasonicBlurayError(Exception):
    """Base exception for Panasonic Blu-ray errors."""


class CannotConnect(PanasonicBlurayError):
    """Exception raised when unable to connect to the device."""


class InvalidAuth(PanasonicBlurayError):
    """Exception raised when authentication fails (UHD players)."""


class CommandError(PanasonicBlurayError):
    """Exception raised when a command fails."""


@dataclass
class PlayStatus:
    """Playback status data."""

    state: str  # "off", "standby", "stopped", "playing", "paused", "unknown"
    status_string: str  # Human-readable status (OpenHAB: player-status)
    position: int  # Playback position in seconds
    duration: int  # Total duration in seconds (BD only, 0 for UHD)
    chapter_current: int | None  # Current chapter (BD only)
    chapter_total: int | None  # Total chapters (BD only)


@dataclass
class CommandResult:
    """Result of a command execution."""

    success: bool
    error: str | None = None


class PanasonicBlurayApi:
    """Async API client for Panasonic Blu-ray players."""

    def __init__(
        self,
        host: str,
        player_key: str | None = None,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the API client.

        Args:
            host: IP address or hostname of the player
            player_key: Optional authentication key for UHD players
            port: HTTP port (default 80)
            timeout: Request timeout in seconds
        """
        self._host = host
        self._player_key = player_key
        self._port = port
        self._timeout = ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._player_type: PlayerType = PlayerType.AUTO
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return the host address."""
        return self._host

    @property
    def player_type(self) -> PlayerType:
        """Return the detected player type."""
        return self._player_type

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            headers = {"User-Agent": API_USER_AGENT}
            if self._player_key:
                # UHD authentication header
                headers["X-Player-Key"] = self._player_key
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers=headers,
            )
        return self._session

    async def close(self) -> None:
        """Close the API session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _build_url(self) -> str:
        """Build the API URL."""
        return f"http://{self._host}:{self._port}{API_ENDPOINT}"

    async def _send_request(self, data: str) -> tuple[str, list[str] | None]:
        """Send a POST request to the player.

        Args:
            data: Form-encoded data to send

        Returns:
            Tuple of (status, response_lines)
            status is "ok", "off", or "error"
            response_lines is the parsed CSV data or None

        Raises:
            CannotConnect: If unable to connect to the device
        """
        async with self._lock:
            try:
                session = await self._get_session()
                url = self._build_url()

                _LOGGER.debug("Sending request to %s: %s", url, data)

                async with session.post(
                    url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as response:
                    if response.status == 404:
                        # Device may be on different subnet or not configured
                        raise CannotConnect(
                            f"Device returned 404. Ensure player is on same subnet "
                            f"and Remote Device Operation is enabled."
                        )

                    if response.status != 200:
                        raise CannotConnect(
                            f"Unexpected status code: {response.status}"
                        )

                    # Read response as bytes to handle potential gzip compression
                    raw_bytes = await response.read()

                    # Check if response is gzip compressed (magic bytes 0x1f 0x8b)
                    if len(raw_bytes) >= 2 and raw_bytes[0:2] == b'\x1f\x8b':
                        try:
                            raw_bytes = gzip.decompress(raw_bytes)
                        except (gzip.BadGzipFile, EOFError, OSError):
                            _LOGGER.debug("Failed to decompress gzip response")
                            return ("error", None)

                    # Decode as text
                    try:
                        text = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        # Try latin-1 as fallback
                        text = raw_bytes.decode("latin-1")

                    lines = text.strip().split("\r\n")

                    _LOGGER.debug("Response: %s", lines)

                    # First line is status: "00, "", 1" on success, "FE..." on error
                    first_line = lines[0].split(",")
                    if first_line[0].strip().startswith("FE"):
                        return ("error", None)

                    if first_line[0].strip() != "00":
                        return ("error", None)

                    # Parse data from second line if present
                    if len(lines) > 1:
                        data_line = lines[1].split(",")
                        return ("ok", data_line)

                    return ("ok", None)

            except aiohttp.ClientError as err:
                _LOGGER.debug("Connection error: %s", err)
                return ("off", None)
            except asyncio.TimeoutError:
                _LOGGER.debug("Connection timeout")
                return ("off", None)

    async def async_test_connection(self) -> bool:
        """Test connection to the player.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            status, _ = await self._send_request(
                "cCMD_GET_STATUS.x=100&cCMD_GET_STATUS.y=100"
            )
            return status != "error"
        except CannotConnect:
            return False

    async def async_detect_player_type(self) -> PlayerType:
        """Detect the player type (BD or UHD).

        BD players respond to status commands.
        UHD players may require authentication.

        Returns:
            PlayerType.BD, PlayerType.UHD, or PlayerType.AUTO if unknown
        """
        _LOGGER.debug("Detecting player type for %s", self._host)

        # Try to get status - BD players will respond
        status, data = await self._send_request(
            "cCMD_GET_STATUS.x=100&cCMD_GET_STATUS.y=100"
        )

        if status == "ok" and data:
            self._player_type = PlayerType.BD
            _LOGGER.debug("Detected BD player (extended status available)")
            return self._player_type

        # If status failed, try a simple command
        # UHD players return error for commands without auth
        status, _ = await self._send_request(
            "cCMD_PST.x=100&cCMD_PST.y=100"
        )

        if status == "error":
            # Likely UHD without auth
            self._player_type = PlayerType.UHD
            _LOGGER.debug("Detected UHD player (limited status, may need authentication)")
        elif status == "ok":
            # Could be UHD with auth or BD
            self._player_type = PlayerType.BD
            _LOGGER.debug("Detected BD-compatible player")

        return self._player_type

    async def async_send_command(self, command: str) -> CommandResult:
        """Send a command to the player.

        Args:
            command: Command name (e.g., "POWER", "PLAYBACK")

        Returns:
            CommandResult with success status

        Raises:
            CommandError: If the command is not recognized
        """
        command = command.upper()
        if command not in COMMANDS:
            _LOGGER.warning("Unknown command requested: %s", command)
            return CommandResult(
                success=False,
                error=f"Unknown command: {command}"
            )

        data = f"cCMD_RC_{command}.x=100&cCMD_RC_{command}.y=100"
        status, _ = await self._send_request(data)

        if status == "error":
            # If we're auto-detecting, this might indicate UHD
            if self._player_type == PlayerType.AUTO:
                self._player_type = PlayerType.UHD
            _LOGGER.debug("Command %s failed (player returned error)", command)
            return CommandResult(success=False, error="Command failed")

        if status == "off":
            _LOGGER.debug("Command %s failed (device off or unreachable)", command)
            return CommandResult(success=False, error="Device is off or unreachable")

        # If we're auto-detecting and command succeeded, likely BD
        if self._player_type == PlayerType.AUTO:
            self._player_type = PlayerType.BD

        _LOGGER.debug("Command %s executed successfully", command)
        return CommandResult(success=True)

    async def async_get_play_status(self) -> PlayStatus:
        """Get the current playback status.

        This uses the cCMD_PST command for basic status and
        cCMD_GET_STATUS for extended info (BD players only).

        Returns:
            PlayStatus with current state and position info
        """
        # Get basic play status
        status, data = await self._send_request(
            "cCMD_PST.x=100&cCMD_PST.y=100"
        )

        if status == "off":
            return PlayStatus(
                state="off",
                status_string=PlayerStatus.POWER_OFF.value,
                position=0,
                duration=0,
                chapter_current=None,
                chapter_total=None,
            )

        if status == "error" or not data:
            return PlayStatus(
                state="unknown",
                status_string=PlayerStatus.UNKNOWN.value,
                position=0,
                duration=0,
                chapter_current=None,
                chapter_total=None,
            )

        # Parse PST response: state, playing_time, unknown, unknown
        # state: 0=stopped, 1=playing, 2=paused
        try:
            pst_state = int(data[0]) if len(data) > 0 else 0
            position = int(data[1]) if len(data) > 1 else 0
        except (ValueError, IndexError):
            pst_state = 0
            position = 0

        # Negative position means no disc
        if position < 0:
            position = 0

        # Get extended status for BD players (duration, chapters)
        duration = 0
        chapter_current = None
        chapter_total = None

        if self._player_type != PlayerType.UHD:
            ext_status, ext_data = await self._send_request(
                "cCMD_GET_STATUS.x=100&cCMD_GET_STATUS.y=100"
            )

            if ext_status == "ok" and ext_data:
                try:
                    # Extended status format:
                    # 0: state (0=standby/playing/paused, 2=stopped/menu)
                    # 3: playing time
                    # 4: total time
                    # 5: current chapter (sometimes)
                    # 6: total chapters (sometimes)
                    ext_state = int(ext_data[0]) if len(ext_data) > 0 else 0
                    duration = int(ext_data[4]) if len(ext_data) > 4 else 0
                    if len(ext_data) > 5:
                        chapter_current = int(ext_data[5])
                    if len(ext_data) > 6:
                        chapter_total = int(ext_data[6])

                    # Use extended state to determine standby
                    if ext_state == 0 and pst_state == 0:
                        # Stopped + ext state 0 = standby
                        return PlayStatus(
                            state="standby",
                            status_string=PlayerStatus.POWER_OFF.value,
                            position=position,
                            duration=duration,
                            chapter_current=chapter_current,
                            chapter_total=chapter_total,
                        )
                except (ValueError, IndexError):
                    pass

        # Map PST state to our state
        if pst_state == 0:
            state = "stopped"
            status_string = PlayerStatus.STOPPED.value
        elif pst_state == 1:
            state = "playing"
            status_string = PlayerStatus.PLAYBACK.value
        elif pst_state == 2:
            state = "paused"
            status_string = PlayerStatus.PAUSE_PLAYBACK.value
        else:
            state = "unknown"
            status_string = PlayerStatus.UNKNOWN.value

        return PlayStatus(
            state=state,
            status_string=status_string,
            position=position,
            duration=duration,
            chapter_current=chapter_current,
            chapter_total=chapter_total,
        )
