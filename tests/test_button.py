"""Tests for Panasonic Blu-ray button entity."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.panasonic_bd.const import DOMAIN, PlayerType
from custom_components.panasonic_bd.coordinator import PanasonicBlurayData
from custom_components.panasonic_bd.button import (
    PanasonicBlurayEjectButton,
    async_setup_entry,
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
    coordinator.async_send_command = AsyncMock(return_value=True)
    return coordinator


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "name": "Living Room Blu-ray"},
        unique_id="192.168.1.100",
    )


class TestEjectButtonProperties:
    """Test eject button properties."""

    def test_unique_id(self, mock_coordinator, mock_entry):
        """Test unique ID."""
        button = PanasonicBlurayEjectButton(mock_coordinator, mock_entry)
        assert button.unique_id == "192.168.1.100_eject"

    def test_name(self, mock_coordinator, mock_entry):
        """Test entity name."""
        button = PanasonicBlurayEjectButton(mock_coordinator, mock_entry)
        assert button.name == "Eject"

    def test_icon(self, mock_coordinator, mock_entry):
        """Test button icon."""
        button = PanasonicBlurayEjectButton(mock_coordinator, mock_entry)
        assert button.icon == "mdi:eject"

    def test_device_info(self, mock_coordinator, mock_entry):
        """Test device info."""
        button = PanasonicBlurayEjectButton(mock_coordinator, mock_entry)
        device_info = button.device_info
        assert device_info["identifiers"] == {(DOMAIN, "192.168.1.100")}


class TestEjectButtonActions:
    """Test eject button actions."""

    async def test_press(self, mock_coordinator, mock_entry):
        """Test button press sends OP_CL command."""
        button = PanasonicBlurayEjectButton(mock_coordinator, mock_entry)
        await button.async_press()
        mock_coordinator.async_send_command.assert_called_once_with("OP_CL")


class TestButtonPlatformSetup:
    """Test button platform setup."""

    async def test_async_setup_entry(self, mock_coordinator, mock_entry):
        """Test async_setup_entry creates eject button."""
        mock_hass = MagicMock()
        mock_hass.data = {DOMAIN: {mock_entry.entry_id: {"coordinator": mock_coordinator}}}

        added_entities = []

        def capture_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(mock_hass, mock_entry, capture_entities)

        assert len(added_entities) == 1
        assert isinstance(added_entities[0], PanasonicBlurayEjectButton)
