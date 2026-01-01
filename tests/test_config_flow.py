"""Tests for Panasonic Blu-ray config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.panasonic_bd.const import DOMAIN, PlayerType


async def test_form_user(hass: HomeAssistant, mock_api, mock_setup_entry) -> None:
    """Test we get the user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "192.168.1.100",
            "name": "Living Room Blu-ray",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Room Blu-ray"
    assert result["data"] == {
        "host": "192.168.1.100",
        "name": "Living Room Blu-ray",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_user_with_player_key(
    hass: HomeAssistant, mock_api, mock_setup_entry
) -> None:
    """Test user form with player key for UHD players."""
    mock_api.async_detect_player_type = AsyncMock(return_value=PlayerType.UHD)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "192.168.1.100",
            "name": "UHD Player",
            "player_key": "abcd1234abcd1234abcd1234abcd1234",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "UHD Player"
    assert result["data"]["player_key"] == "abcd1234abcd1234abcd1234abcd1234"


async def test_form_cannot_connect(
    hass: HomeAssistant, mock_api_cannot_connect, mock_setup_entry
) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "192.168.1.100",
            "name": "Test Player",
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_invalid_auth(
    hass: HomeAssistant, mock_api_invalid_auth, mock_setup_entry
) -> None:
    """Test we handle invalid auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "192.168.1.100",
            "name": "Test Player",
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_already_configured(
    hass: HomeAssistant, mock_api, mock_setup_entry
) -> None:
    """Test we handle already configured error."""
    # Create an existing entry using MockConfigEntry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Existing Player",
        data={"host": "192.168.1.100", "name": "Existing Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "192.168.1.100",
            "name": "Duplicate Player",
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_form_unknown_error(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test we handle unknown error."""
    with patch(
        "custom_components.panasonic_bd.config_flow.PanasonicBlurayApi"
    ) as mock_api_class:
        mock_instance = MagicMock()
        mock_instance.async_test_connection = AsyncMock(side_effect=Exception("Boom"))
        mock_instance.close = AsyncMock()
        mock_api_class.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "192.168.1.100",
                "name": "Test Player",
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_form_default_name(
    hass: HomeAssistant, mock_api, mock_setup_entry
) -> None:
    """Test form uses default name when not provided."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "192.168.1.100",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Default name should be used
    assert result["title"] == "Panasonic Blu-ray"


async def test_reauth_flow(hass: HomeAssistant, mock_api, mock_setup_entry) -> None:
    """Test reauth flow for UHD players."""
    # Create an existing entry using MockConfigEntry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="UHD Player",
        data={"host": "192.168.1.100", "name": "UHD Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
        },
        data={"host": "192.168.1.100", "name": "UHD Player"},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "player_key": "newkey12345678901234567890123456",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_form_uhd_without_player_key(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """Test UHD player detection without player key logs warning."""
    with patch(
        "custom_components.panasonic_bd.config_flow.PanasonicBlurayApi"
    ) as mock_api_class:
        mock_instance = MagicMock()
        mock_instance.async_test_connection = AsyncMock(return_value=True)
        mock_instance.async_detect_player_type = AsyncMock(return_value=PlayerType.UHD)
        mock_instance.close = AsyncMock()
        mock_api_class.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "192.168.1.100",
                "name": "UHD Player",
                # No player_key provided
            },
        )
        await hass.async_block_till_done()

        # Should still create entry, just log warning
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "UHD Player"


async def test_reauth_cannot_connect(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """Test reauth flow with connection error."""
    from custom_components.panasonic_bd.api import CannotConnect

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="UHD Player",
        data={"host": "192.168.1.100", "name": "UHD Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.panasonic_bd.config_flow.PanasonicBlurayApi"
    ) as mock_api_class:
        mock_instance = MagicMock()
        mock_instance.async_test_connection = AsyncMock(return_value=False)
        mock_instance.close = AsyncMock()
        mock_api_class.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
            data={"host": "192.168.1.100", "name": "UHD Player"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"player_key": "somekey123"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_invalid_auth(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """Test reauth flow with invalid auth error."""
    from custom_components.panasonic_bd.api import InvalidAuth

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="UHD Player",
        data={"host": "192.168.1.100", "name": "UHD Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.panasonic_bd.config_flow.PanasonicBlurayApi"
    ) as mock_api_class:
        mock_instance = MagicMock()
        mock_instance.async_test_connection = AsyncMock(return_value=True)
        mock_instance.async_detect_player_type = AsyncMock(side_effect=InvalidAuth())
        mock_instance.close = AsyncMock()
        mock_api_class.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
            data={"host": "192.168.1.100", "name": "UHD Player"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"player_key": "badkey123"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_unknown_error(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """Test reauth flow with unknown error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="UHD Player",
        data={"host": "192.168.1.100", "name": "UHD Player"},
        unique_id="192.168.1.100",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.panasonic_bd.config_flow.PanasonicBlurayApi"
    ) as mock_api_class:
        mock_instance = MagicMock()
        mock_instance.async_test_connection = AsyncMock(side_effect=Exception("Boom"))
        mock_instance.close = AsyncMock()
        mock_api_class.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
            data={"host": "192.168.1.100", "name": "UHD Player"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"player_key": "somekey123"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_reauth_no_existing_entry(
    hass: HomeAssistant, mock_api, mock_setup_entry
) -> None:
    """Test reauth flow when no existing entry found."""
    # Don't add entry to hass - simulate entry being deleted during reauth
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH},
        data={"host": "192.168.1.100", "name": "UHD Player"},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"player_key": "newkey123"},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "unknown"
