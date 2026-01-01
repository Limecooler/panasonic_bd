"""Tests for Panasonic Blu-ray integration setup."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.panasonic_bd.const import DOMAIN, PlayerType
from custom_components.panasonic_bd.coordinator import PanasonicBlurayData


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_api():
    """Create a mock API instance."""
    api = MagicMock()
    api.async_test_connection = AsyncMock(return_value=True)
    api.async_detect_player_type = AsyncMock(return_value=PlayerType.BD)
    api.async_get_play_status = AsyncMock(
        return_value=MagicMock(
            state="stopped",
            position=0,
            status_string="Stopped",
        )
    )
    api.close = AsyncMock()
    return api


async def test_setup_entry(hass: HomeAssistant, mock_api) -> None:
    """Test successful setup of config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "name": "Test Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.panasonic_bd.PanasonicBlurayApi",
        return_value=mock_api,
    ), patch(
        "custom_components.panasonic_bd.coordinator.PanasonicBlurayCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]


async def test_unload_entry(hass: HomeAssistant, mock_api) -> None:
    """Test unloading config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "name": "Test Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.panasonic_bd.PanasonicBlurayApi",
        return_value=mock_api,
    ), patch(
        "custom_components.panasonic_bd.coordinator.PanasonicBlurayCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED
    mock_api.close.assert_called_once()


async def test_setup_entry_connection_failure(hass: HomeAssistant) -> None:
    """Test setup with connection failure."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "name": "Test Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    mock_api = MagicMock()
    mock_api.close = AsyncMock()

    with patch(
        "custom_components.panasonic_bd.PanasonicBlurayApi",
        return_value=mock_api,
    ), patch(
        "custom_components.panasonic_bd.coordinator.PanasonicBlurayCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
        side_effect=Exception("Connection failed"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_reload_entry(hass: HomeAssistant, mock_api) -> None:
    """Test reloading config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "name": "Test Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.panasonic_bd.PanasonicBlurayApi",
        return_value=mock_api,
    ), patch(
        "custom_components.panasonic_bd.coordinator.PanasonicBlurayCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.LOADED

        # Trigger reload via update listener
        from custom_components.panasonic_bd import async_reload_entry

        await async_reload_entry(hass, entry)
        await hass.async_block_till_done()

    # Entry should still be loaded after reload
    assert entry.state == ConfigEntryState.LOADED
