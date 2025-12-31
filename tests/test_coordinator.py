"""Tests for Panasonic Blu-ray coordinator."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.panasonic_bluray.coordinator import (
    PanasonicBlurayCoordinator,
    PanasonicBlurayData,
)
from custom_components.panasonic_bluray.api import PlayStatus, CommandResult
from custom_components.panasonic_bluray.const import PlayerType, PlayerStatus


@pytest.fixture
def mock_api():
    """Create a mock API."""
    api = MagicMock()
    api.player_type = PlayerType.BD
    api.async_get_play_status = AsyncMock(
        return_value=PlayStatus(
            state="playing",
            status_string=PlayerStatus.PLAYBACK.value,
            position=120,
            duration=7200,
            chapter_current=3,
            chapter_total=20,
        )
    )
    api.async_send_command = AsyncMock(
        return_value=CommandResult(success=True, error=None)
    )
    return api


@pytest.fixture
def coordinator(hass: HomeAssistant, mock_api):
    """Create a coordinator for testing."""
    return PanasonicBlurayCoordinator(hass, mock_api, "Test Player")


class TestCoordinatorInit:
    """Test coordinator initialization."""

    def test_init(self, hass: HomeAssistant, mock_api):
        """Test coordinator initialization."""
        coordinator = PanasonicBlurayCoordinator(hass, mock_api, "Test Player")
        assert coordinator.api is mock_api
        assert coordinator.device_name == "Test Player"
        assert coordinator._consecutive_errors == 0


class TestAsyncUpdateData:
    """Test the _async_update_data method."""

    async def test_update_success(self, coordinator, mock_api):
        """Test successful data update."""
        data = await coordinator._async_update_data()

        assert data.state == "playing"
        assert data.player_status == PlayerStatus.PLAYBACK.value
        assert data.media_position == 120
        assert data.media_duration == 7200
        assert data.chapter_current == 3
        assert data.chapter_total == 20
        assert data.player_type == PlayerType.BD
        assert coordinator._consecutive_errors == 0

    async def test_update_resets_error_counter(self, coordinator, mock_api):
        """Test that successful update resets error counter."""
        coordinator._consecutive_errors = 5
        await coordinator._async_update_data()
        assert coordinator._consecutive_errors == 0

    async def test_update_error_increments_counter(self, coordinator, mock_api):
        """Test that error increments counter."""
        mock_api.async_get_play_status.side_effect = Exception("Connection failed")

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._consecutive_errors == 1

    async def test_update_error_with_existing_data(self, coordinator, mock_api):
        """Test error when there is existing data returns offline state."""
        # Set existing data
        coordinator.data = PanasonicBlurayData(
            state="playing",
            player_status="Playback",
            media_position=100,
            media_position_updated_at=datetime.now(),
            media_duration=7200,
            chapter_current=3,
            chapter_total=20,
            player_type=PlayerType.BD,
        )
        mock_api.async_get_play_status.side_effect = Exception("Connection failed")

        data = await coordinator._async_update_data()

        assert data.state == "off"
        assert data.player_status == "Unavailable"
        assert coordinator._consecutive_errors == 1

    async def test_update_error_suppresses_after_max(self, coordinator, mock_api):
        """Test that errors are suppressed after max consecutive errors."""
        mock_api.async_get_play_status.side_effect = Exception("Connection failed")

        # First 3 errors should be logged
        for i in range(3):
            with pytest.raises(UpdateFailed):
                await coordinator._async_update_data()

        # 4th error triggers suppression message
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._consecutive_errors == 4

        # 5th+ errors are suppressed
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._consecutive_errors == 5


class TestAsyncSendCommand:
    """Test the async_send_command method."""

    async def test_send_command_success(self, coordinator, mock_api):
        """Test successful command sends and refreshes."""
        with patch.object(
            coordinator, "async_request_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            result = await coordinator.async_send_command("POWER")

            assert result is True
            mock_api.async_send_command.assert_called_once_with("POWER")
            mock_refresh.assert_called_once()

    async def test_send_command_failure(self, coordinator, mock_api):
        """Test failed command does not refresh."""
        mock_api.async_send_command.return_value = CommandResult(
            success=False, error="Command failed"
        )

        with patch.object(
            coordinator, "async_request_refresh", new_callable=AsyncMock
        ) as mock_refresh:
            result = await coordinator.async_send_command("POWER")

            assert result is False
            mock_refresh.assert_not_called()
