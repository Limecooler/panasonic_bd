"""The Panasonic Blu-ray integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .api import PanasonicBlurayApi
from .const import CONF_PLAYER_KEY, DEFAULT_NAME, DOMAIN
from .coordinator import PanasonicBlurayCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.REMOTE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Panasonic Blu-ray from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to set up

    Returns:
        True if setup was successful
    """
    host = entry.data[CONF_HOST]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    player_key = entry.data.get(CONF_PLAYER_KEY)

    _LOGGER.debug("Setting up Panasonic Blu-ray: %s (%s)", name, host)

    # Create API client
    api = PanasonicBlurayApi(
        host=host,
        player_key=player_key,
    )

    # Detect player type
    await api.async_detect_player_type()
    _LOGGER.debug("Detected player type: %s", api.player_type.value)

    # Create coordinator
    coordinator = PanasonicBlurayCoordinator(hass, api, name)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and API in hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload was successful
    """
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Close API session and remove from hass.data
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api"].close()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change.

    Args:
        hass: Home Assistant instance
        entry: Config entry that was updated
    """
    await hass.config_entries.async_reload(entry.entry_id)
