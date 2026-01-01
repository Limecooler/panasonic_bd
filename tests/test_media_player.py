"""Tests for Panasonic Blu-ray media player entity."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.panasonic_bd.const import DOMAIN, PlayerType
from custom_components.panasonic_bd.coordinator import PanasonicBlurayData
from custom_components.panasonic_bd.media_player import (
    PanasonicBlurayMediaPlayer,
    STATE_MAP,
)


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
    coordinator.device_name = "Living Room Blu-ray"
    coordinator.async_send_command = AsyncMock()
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


class TestStateMap:
    """Test state mapping."""

    def test_state_map_off(self):
        """Test off state mapping."""
        assert STATE_MAP["off"] == MediaPlayerState.OFF

    def test_state_map_standby(self):
        """Test standby state mapping."""
        assert STATE_MAP["standby"] == MediaPlayerState.OFF

    def test_state_map_stopped(self):
        """Test stopped state mapping."""
        assert STATE_MAP["stopped"] == MediaPlayerState.IDLE

    def test_state_map_playing(self):
        """Test playing state mapping."""
        assert STATE_MAP["playing"] == MediaPlayerState.PLAYING

    def test_state_map_paused(self):
        """Test paused state mapping."""
        assert STATE_MAP["paused"] == MediaPlayerState.PAUSED


class TestMediaPlayerProperties:
    """Test media player properties."""

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.unique_id == "192.168.1.100_media_player"

    def test_device_info(self, mock_coordinator, mock_entry):
        """Test device info."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        device_info = player.device_info
        assert device_info["identifiers"] == {(DOMAIN, "192.168.1.100")}
        assert device_info["name"] == "Living Room Blu-ray"
        assert device_info["manufacturer"] == "Panasonic"

    def test_state_playing(self, mock_coordinator, mock_entry):
        """Test playing state."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.state == MediaPlayerState.PLAYING

    def test_state_none_when_no_data(self, mock_coordinator, mock_entry):
        """Test state is None when no data."""
        mock_coordinator.data = None
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.state is None

    def test_media_position(self, mock_coordinator, mock_entry):
        """Test media position."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.media_position == 120

    def test_media_position_none_when_zero(self, mock_coordinator, mock_entry):
        """Test media position is None when zero."""
        mock_coordinator.data.media_position = 0
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.media_position is None

    def test_media_duration(self, mock_coordinator, mock_entry):
        """Test media duration."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.media_duration == 7200

    def test_media_track(self, mock_coordinator, mock_entry):
        """Test media track (chapter)."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.media_track == 3

    def test_media_position_updated_at(self, mock_coordinator, mock_entry):
        """Test media position updated at timestamp."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.media_position_updated_at is not None

    def test_media_position_updated_at_none(self, mock_coordinator, mock_entry):
        """Test media position updated at when no data."""
        mock_coordinator.data = None
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        assert player.media_position_updated_at is None

    def test_extra_state_attributes(self, mock_coordinator, mock_entry):
        """Test extra state attributes."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        attrs = player.extra_state_attributes
        assert attrs["player_status"] == "Playback"
        assert attrs["player_type"] == "bd"
        assert attrs["chapter_current"] == 3
        assert attrs["chapter_total"] == 20

    def test_extra_state_attributes_no_chapters(self, mock_coordinator, mock_entry):
        """Test extra state attributes without chapters (UHD player)."""
        mock_coordinator.data.chapter_current = None
        mock_coordinator.data.chapter_total = None
        mock_coordinator.data.player_type = PlayerType.UHD
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        attrs = player.extra_state_attributes
        assert "chapter_current" not in attrs
        assert "chapter_total" not in attrs


class TestMediaPlayerActions:
    """Test media player actions."""

    async def test_turn_on(self, mock_coordinator, mock_entry):
        """Test turn on."""
        mock_coordinator.data.state = "off"
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_turn_on()
        mock_coordinator.async_send_command.assert_called_once_with("POWER")

    async def test_turn_on_already_on(self, mock_coordinator, mock_entry):
        """Test turn on when already on does nothing."""
        mock_coordinator.data.state = "playing"
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_turn_on()
        mock_coordinator.async_send_command.assert_not_called()

    async def test_turn_off(self, mock_coordinator, mock_entry):
        """Test turn off."""
        mock_coordinator.data.state = "playing"
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_turn_off()
        mock_coordinator.async_send_command.assert_called_once_with("POWER")

    async def test_turn_off_already_off(self, mock_coordinator, mock_entry):
        """Test turn off when already off does nothing."""
        mock_coordinator.data.state = "off"
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_turn_off()
        mock_coordinator.async_send_command.assert_not_called()

    async def test_media_play(self, mock_coordinator, mock_entry):
        """Test play."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_media_play()
        mock_coordinator.async_send_command.assert_called_once_with("PLAYBACK")

    async def test_media_pause(self, mock_coordinator, mock_entry):
        """Test pause."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_media_pause()
        mock_coordinator.async_send_command.assert_called_once_with("PAUSE")

    async def test_media_stop(self, mock_coordinator, mock_entry):
        """Test stop."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_media_stop()
        mock_coordinator.async_send_command.assert_called_once_with("STOP")

    async def test_media_next_track(self, mock_coordinator, mock_entry):
        """Test next track."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_media_next_track()
        mock_coordinator.async_send_command.assert_called_once_with("SKIPFWD")

    async def test_media_previous_track(self, mock_coordinator, mock_entry):
        """Test previous track."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        await player.async_media_previous_track()
        mock_coordinator.async_send_command.assert_called_once_with("SKIPREV")


class TestMediaPlayerCallback:
    """Test coordinator update callback."""

    def test_handle_coordinator_update(self, mock_coordinator, mock_entry):
        """Test that callback triggers state write."""
        player = PanasonicBlurayMediaPlayer(mock_coordinator, mock_entry)
        player.async_write_ha_state = MagicMock()

        player._handle_coordinator_update()

        player.async_write_ha_state.assert_called_once()
