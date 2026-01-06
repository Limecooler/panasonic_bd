"""Tests for Panasonic Blu-ray remote entity."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.panasonic_bd.const import DOMAIN, COMMANDS, COMMAND_ALIASES, PlayerType
from custom_components.panasonic_bd.coordinator import PanasonicBlurayData
from custom_components.panasonic_bd.remote import PanasonicBlurayRemote
from custom_components.panasonic_bd.api import CommandResult


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = PanasonicBlurayData(
        state="playing",
        player_status="Playback",
        media_position=120,
        media_duration=7200,
        chapter_current=3,
        chapter_total=20,
        player_type=PlayerType.BD,
        media_position_updated_at=datetime.now(),
    )
    coordinator.api = MagicMock()
    coordinator.api.async_send_command = AsyncMock(
        return_value=CommandResult(success=True, error=None)
    )
    coordinator.async_send_command = AsyncMock(return_value=True)
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "name": "Living Room Blu-ray"},
        unique_id="192.168.1.100",
    )


class TestRemoteProperties:
    """Test remote entity properties."""

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote.unique_id == "192.168.1.100_remote"

    def test_name(self, mock_coordinator, mock_entry):
        """Test entity name."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote.name == "Remote"

    def test_device_info(self, mock_coordinator, mock_entry):
        """Test device info."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        device_info = remote.device_info
        assert device_info["identifiers"] == {(DOMAIN, "192.168.1.100")}

    def test_is_on_when_playing(self, mock_coordinator, mock_entry):
        """Test is_on returns True when playing."""
        mock_coordinator.data.state = "playing"
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote.is_on is True

    def test_is_on_when_paused(self, mock_coordinator, mock_entry):
        """Test is_on returns True when paused."""
        mock_coordinator.data.state = "paused"
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote.is_on is True

    def test_is_on_when_off(self, mock_coordinator, mock_entry):
        """Test is_on returns False when off."""
        mock_coordinator.data.state = "off"
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote.is_on is False

    def test_is_on_when_standby(self, mock_coordinator, mock_entry):
        """Test is_on returns False when standby."""
        mock_coordinator.data.state = "standby"
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote.is_on is False

    def test_is_on_when_unknown(self, mock_coordinator, mock_entry):
        """Test is_on returns False when unknown."""
        mock_coordinator.data.state = "unknown"
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote.is_on is False

    def test_is_on_no_data(self, mock_coordinator, mock_entry):
        """Test is_on returns None when no data."""
        mock_coordinator.data = None
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote.is_on is None

    def test_extra_state_attributes(self, mock_coordinator, mock_entry):
        """Test extra state attributes."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        attrs = remote.extra_state_attributes
        assert "available_commands" in attrs
        assert "available_aliases" in attrs
        assert attrs["player_type"] == "bd"
        assert "POWER" in attrs["available_commands"]
        assert "PLAYBACK" in attrs["available_commands"]
        assert "play" in attrs["available_aliases"]
        assert "eject" in attrs["available_aliases"]


class TestRemoteActions:
    """Test remote entity actions."""

    async def test_turn_on(self, mock_coordinator, mock_entry):
        """Test turn on sends POWER command."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_turn_on()
        mock_coordinator.async_send_command.assert_called_once_with("POWER")

    async def test_turn_off(self, mock_coordinator, mock_entry):
        """Test turn off sends POWER command."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_turn_off()
        mock_coordinator.async_send_command.assert_called_once_with("POWER")

    async def test_send_single_command(self, mock_coordinator, mock_entry):
        """Test sending a single command."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["PLAYBACK"])
        mock_coordinator.api.async_send_command.assert_called_once_with("PLAYBACK")
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_send_multiple_commands(self, mock_coordinator, mock_entry):
        """Test sending multiple commands."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await remote.async_send_command(["UP", "DOWN", "SELECT"], delay_secs=0.1)
        assert mock_coordinator.api.async_send_command.call_count == 3

    async def test_send_command_case_insensitive(self, mock_coordinator, mock_entry):
        """Test commands are case insensitive."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["playback"])
        mock_coordinator.api.async_send_command.assert_called_once_with("PLAYBACK")

    async def test_send_command_with_repeats(self, mock_coordinator, mock_entry):
        """Test sending command with repeats."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await remote.async_send_command(["SKIPFWD"], num_repeats=3, delay_secs=0.1)
        assert mock_coordinator.api.async_send_command.call_count == 3

    async def test_send_unknown_command_skipped(self, mock_coordinator, mock_entry):
        """Test unknown commands are skipped with warning."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["UNKNOWN_CMD"])
        mock_coordinator.api.async_send_command.assert_not_called()

    async def test_send_command_via_alias(self, mock_coordinator, mock_entry):
        """Test sending command via alias."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["play"])
        mock_coordinator.api.async_send_command.assert_called_once_with("PLAYBACK")

    async def test_send_command_via_alias_case_insensitive(self, mock_coordinator, mock_entry):
        """Test aliases are case insensitive."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["PLAY"])
        # Alias lookup is lowercase, so PLAY doesn't match "play" alias
        # but it's not a valid native command either, so it's resolved by alias
        mock_coordinator.api.async_send_command.assert_called_once_with("PLAYBACK")

    async def test_send_eject_alias(self, mock_coordinator, mock_entry):
        """Test eject alias sends OP_CL."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["eject"])
        mock_coordinator.api.async_send_command.assert_called_once_with("OP_CL")

    async def test_send_fast_forward_alias(self, mock_coordinator, mock_entry):
        """Test fast forward alias sends CUE."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["ff"])
        mock_coordinator.api.async_send_command.assert_called_once_with("CUE")

    async def test_send_number_alias(self, mock_coordinator, mock_entry):
        """Test number alias sends D# command."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["5"])
        mock_coordinator.api.async_send_command.assert_called_once_with("D5")

    async def test_send_command_failure_logged(self, mock_coordinator, mock_entry):
        """Test command failures are logged."""
        mock_coordinator.api.async_send_command = AsyncMock(
            return_value=CommandResult(success=False, error="Device busy")
        )
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        await remote.async_send_command(["POWER"])
        # Should still call refresh even on failure
        mock_coordinator.async_request_refresh.assert_called_once()


class TestCommands:
    """Test that all commands are valid."""

    def test_all_commands_defined(self):
        """Test that we have a comprehensive command list."""
        # Essential commands should be present
        essential = [
            "POWER",
            "PLAYBACK",
            "PAUSE",
            "STOP",
            "SKIPFWD",
            "SKIPREV",
            "UP",
            "DOWN",
            "LEFT",
            "RIGHT",
            "SELECT",
            "RETURN",
            "MENU",
            "OP_CL",
        ]
        for cmd in essential:
            assert cmd in COMMANDS, f"Missing essential command: {cmd}"

    def test_number_commands(self):
        """Test number commands exist."""
        for i in range(10):
            assert f"D{i}" in COMMANDS

    def test_color_commands(self):
        """Test color button commands exist."""
        colors = ["RED", "GREEN", "BLUE", "YELLOW"]
        for color in colors:
            assert color in COMMANDS

    def test_shuttle_commands(self):
        """Test shuttle commands exist."""
        for i in range(1, 6):
            assert f"SHFWD{i}" in COMMANDS
            assert f"SHREV{i}" in COMMANDS


class TestRemoteCallback:
    """Test coordinator update callback."""

    def test_handle_coordinator_update(self, mock_coordinator, mock_entry):
        """Test that callback triggers state write."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        remote.async_write_ha_state = MagicMock()

        remote._handle_coordinator_update()

        remote.async_write_ha_state.assert_called_once()


class TestCommandAliases:
    """Test command alias mappings."""

    def test_all_aliases_map_to_valid_commands(self):
        """Test all aliases map to commands in COMMANDS set."""
        for alias, command in COMMAND_ALIASES.items():
            assert command in COMMANDS, f"Alias '{alias}' maps to invalid command '{command}'"

    def test_playback_aliases(self):
        """Test playback-related aliases."""
        assert COMMAND_ALIASES["play"] == "PLAYBACK"
        assert COMMAND_ALIASES["ff"] == "CUE"
        assert COMMAND_ALIASES["fast_forward"] == "CUE"
        assert COMMAND_ALIASES["rewind"] == "REV"
        assert COMMAND_ALIASES["rw"] == "REV"
        assert COMMAND_ALIASES["next"] == "SKIPFWD"
        assert COMMAND_ALIASES["previous"] == "SKIPREV"

    def test_navigation_aliases(self):
        """Test navigation aliases."""
        assert COMMAND_ALIASES["ok"] == "SELECT"
        assert COMMAND_ALIASES["enter"] == "SELECT"
        assert COMMAND_ALIASES["back"] == "RETURN"
        assert COMMAND_ALIASES["home"] == "MLTNAVI"

    def test_tray_aliases(self):
        """Test tray aliases."""
        assert COMMAND_ALIASES["eject"] == "OP_CL"
        assert COMMAND_ALIASES["open"] == "OP_CL"
        assert COMMAND_ALIASES["close"] == "OP_CL"

    def test_number_aliases(self):
        """Test number aliases."""
        for i in range(10):
            assert COMMAND_ALIASES[str(i)] == f"D{i}"

    def test_resolve_command_direct(self, mock_coordinator, mock_entry):
        """Test _resolve_command with direct command."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote._resolve_command("POWER") == "POWER"
        assert remote._resolve_command("power") == "POWER"
        assert remote._resolve_command("PoWeR") == "POWER"

    def test_resolve_command_alias(self, mock_coordinator, mock_entry):
        """Test _resolve_command with alias."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote._resolve_command("play") == "PLAYBACK"
        assert remote._resolve_command("PLAY") == "PLAYBACK"
        assert remote._resolve_command("eject") == "OP_CL"

    def test_resolve_command_unknown(self, mock_coordinator, mock_entry):
        """Test _resolve_command with unknown command."""
        remote = PanasonicBlurayRemote(mock_coordinator, mock_entry)
        assert remote._resolve_command("invalid_cmd") is None
        assert remote._resolve_command("notacommand") is None
