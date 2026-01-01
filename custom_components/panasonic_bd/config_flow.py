"""Config flow for Panasonic Blu-ray integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import CannotConnect, InvalidAuth, PanasonicBlurayApi
from .const import CONF_PLAYER_KEY, DEFAULT_NAME, DOMAIN, PlayerType

_LOGGER = logging.getLogger(__name__)

# Schema for user input
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_PLAYER_KEY): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input and test connection.

    Args:
        hass: Home Assistant instance
        data: User input data

    Returns:
        Dict with validated data and device info

    Raises:
        CannotConnect: If unable to connect to the device
        InvalidAuth: If authentication fails
    """
    host = data[CONF_HOST]
    player_key = data.get(CONF_PLAYER_KEY)

    _LOGGER.debug("Validating connection to %s", host)

    api = PanasonicBlurayApi(host=host, player_key=player_key)

    try:
        # Test connection
        if not await api.async_test_connection():
            raise CannotConnect("Cannot connect to device")

        # Detect player type
        player_type = await api.async_detect_player_type()
        _LOGGER.debug("Detected player type: %s", player_type.value)

        # If UHD and no player key, commands might fail
        # We'll still allow setup but warn the user
        if player_type == PlayerType.UHD and not player_key:
            _LOGGER.warning(
                "UHD player detected without player key. "
                "Remote commands may not work without authentication."
            )

        return {
            "title": data.get(CONF_NAME, DEFAULT_NAME),
            "player_type": player_type.value,
        }

    finally:
        await api.close()


class PanasonicBlurayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Panasonic Blu-ray."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step.

        Args:
            user_input: User input from the form

        Returns:
            FlowResult for the next step or entry creation
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store user input
            self._user_input = user_input

            # Set unique ID based on host
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create the config entry
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        # Show the form
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication for UHD players.

        Args:
            entry_data: Existing entry data

        Returns:
            FlowResult for re-auth form
        """
        self._user_input = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication confirmation.

        Args:
            user_input: User input from the form

        Returns:
            FlowResult for next step or entry update
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Update with new player key
            self._user_input[CONF_PLAYER_KEY] = user_input.get(CONF_PLAYER_KEY)

            try:
                await validate_input(self.hass, self._user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Update existing entry
                existing_entry = await self.async_set_unique_id(
                    self._user_input[CONF_HOST]
                )
                if existing_entry:
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data=self._user_input,
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

                return self.async_abort(reason="unknown")

        # Show re-auth form
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PLAYER_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "host": self._user_input.get(CONF_HOST, ""),
            },
        )


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuthError(HomeAssistantError):
    """Error to indicate invalid authentication."""
