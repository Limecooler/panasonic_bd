"""Fixtures for Panasonic Blu-ray integration tests."""
from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the custom_components directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.panasonic_bd.const import DOMAIN, PlayerType


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock setting up a config entry."""
    with patch(
        "custom_components.panasonic_bd.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_api() -> Generator[MagicMock, None, None]:
    """Mock the PanasonicBlurayApi."""
    with patch(
        "custom_components.panasonic_bd.config_flow.PanasonicBlurayApi"
    ) as mock_api_class:
        mock_instance = MagicMock()
        mock_instance.async_test_connection = AsyncMock(return_value=True)
        mock_instance.async_detect_player_type = AsyncMock(return_value=PlayerType.BD)
        mock_instance.close = AsyncMock()
        mock_api_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_api_cannot_connect() -> Generator[MagicMock, None, None]:
    """Mock the PanasonicBlurayApi with connection failure."""
    with patch(
        "custom_components.panasonic_bd.config_flow.PanasonicBlurayApi"
    ) as mock_api_class:
        mock_instance = MagicMock()
        mock_instance.async_test_connection = AsyncMock(return_value=False)
        mock_instance.close = AsyncMock()
        mock_api_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_api_invalid_auth() -> Generator[MagicMock, None, None]:
    """Mock the PanasonicBlurayApi with auth failure."""
    from custom_components.panasonic_bd.api import InvalidAuth

    with patch(
        "custom_components.panasonic_bd.config_flow.PanasonicBlurayApi"
    ) as mock_api_class:
        mock_instance = MagicMock()
        mock_instance.async_test_connection = AsyncMock(return_value=True)
        mock_instance.async_detect_player_type = AsyncMock(side_effect=InvalidAuth())
        mock_instance.close = AsyncMock()
        mock_api_class.return_value = mock_instance
        yield mock_instance
