"""Tests for Panasonic Blu-ray API client."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp
from aiohttp import ClientError

from custom_components.panasonic_bd.api import (
    PanasonicBlurayApi,
    CannotConnect,
    CommandResult,
    PlayStatus,
)
from custom_components.panasonic_bd.const import PlayerType, PlayerStatus


@pytest.fixture
def api():
    """Create an API instance for testing."""
    return PanasonicBlurayApi(host="192.168.1.100")


@pytest.fixture
def api_with_key():
    """Create an API instance with player key."""
    return PanasonicBlurayApi(host="192.168.1.100", player_key="testkey123")


class TestApiInit:
    """Test API initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        api = PanasonicBlurayApi(host="192.168.1.100")
        assert api._host == "192.168.1.100"
        assert api._player_key is None
        assert api._player_type == PlayerType.AUTO

    def test_init_with_key(self):
        """Test initialization with player key."""
        api = PanasonicBlurayApi(host="192.168.1.100", player_key="mykey")
        assert api._player_key == "mykey"

    def test_host_property(self):
        """Test host property."""
        api = PanasonicBlurayApi(host="192.168.1.100")
        assert api.host == "192.168.1.100"

    def test_player_type_property(self):
        """Test player_type property."""
        api = PanasonicBlurayApi(host="192.168.1.100")
        assert api.player_type == PlayerType.AUTO


class TestGetSession:
    """Test session management."""

    async def test_get_session_creates_new(self, api):
        """Test creating a new session."""
        session = await api._get_session()
        assert session is not None
        assert api._session is session
        await api.close()

    async def test_get_session_reuses_existing(self, api):
        """Test reusing existing session."""
        session1 = await api._get_session()
        session2 = await api._get_session()
        assert session1 is session2
        await api.close()

    async def test_get_session_with_player_key(self, api_with_key):
        """Test session creation with player key adds header."""
        session = await api_with_key._get_session()
        assert session is not None
        # The X-Player-Key header should be in the session's default headers
        await api_with_key.close()

    async def test_get_session_recreates_if_closed(self, api):
        """Test recreating session if closed."""
        session1 = await api._get_session()
        await session1.close()
        session2 = await api._get_session()
        assert session1 is not session2
        await api.close()


class TestBuildUrl:
    """Test URL building."""

    def test_build_url(self, api):
        """Test URL building."""
        url = api._build_url()
        assert url == "http://192.168.1.100:80/WAN/dvdr/dvdr_ctrl.cgi"

    def test_build_url_custom_port(self):
        """Test URL building with custom port."""
        api = PanasonicBlurayApi(host="192.168.1.100", port=8080)
        url = api._build_url()
        assert url == "http://192.168.1.100:8080/WAN/dvdr/dvdr_ctrl.cgi"


class TestSendRequest:
    """Test the _send_request method."""

    async def test_send_request_success_with_data(self, api):
        """Test successful request with data line."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='00,"OK",1\r\n0,100,200')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        with patch.object(api, "_get_session", return_value=mock_session):
            status, data = await api._send_request("test_data")
            assert status == "ok"
            assert data == ["0", "100", "200"]

    async def test_send_request_success_no_data(self, api):
        """Test successful request without data line."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='00,"OK",1')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        with patch.object(api, "_get_session", return_value=mock_session):
            status, data = await api._send_request("test_data")
            assert status == "ok"
            assert data is None

    async def test_send_request_error_fe_response(self, api):
        """Test request with FE error response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='FE,"Error",0')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        with patch.object(api, "_get_session", return_value=mock_session):
            status, data = await api._send_request("test_data")
            assert status == "error"
            assert data is None

    async def test_send_request_error_non_00_response(self, api):
        """Test request with non-00 status response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='01,"Error",0')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        with patch.object(api, "_get_session", return_value=mock_session):
            status, data = await api._send_request("test_data")
            assert status == "error"

    async def test_send_request_empty_response(self, api):
        """Test request with empty response."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        with patch.object(api, "_get_session", return_value=mock_session):
            status, data = await api._send_request("test_data")
            assert status == "error"

    async def test_send_request_whitespace_only_response(self, api):
        """Test request with whitespace-only response that results in empty lines."""
        mock_response = AsyncMock()
        mock_response.status = 200
        # After strip() this becomes empty, split gives [''] which is truthy
        # To get an empty list, we need to mock the behavior differently
        mock_response.text = AsyncMock(return_value='   \r\n   ')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        with patch.object(api, "_get_session", return_value=mock_session):
            status, data = await api._send_request("test_data")
            # After strip and split, we get [''] which is truthy
            # So this will hit the first_line parsing which may fail
            assert status == "error"

    async def test_send_request_404_error(self, api):
        """Test request with 404 response."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(CannotConnect):
                await api._send_request("test_data")

    async def test_send_request_500_error(self, api):
        """Test request with 500 response."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        with patch.object(api, "_get_session", return_value=mock_session):
            with pytest.raises(CannotConnect):
                await api._send_request("test_data")

    async def test_send_request_client_error(self, api):
        """Test request with client error."""
        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=aiohttp.ClientError())

        with patch.object(api, "_get_session", return_value=mock_session):
            status, data = await api._send_request("test_data")
            assert status == "off"
            assert data is None

    async def test_send_request_timeout(self, api):
        """Test request with timeout."""
        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=asyncio.TimeoutError())

        with patch.object(api, "_get_session", return_value=mock_session):
            status, data = await api._send_request("test_data")
            assert status == "off"
            assert data is None


class TestTestConnection:
    """Test connection testing."""

    async def test_connection_success(self, api):
        """Test successful connection."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("ok", ["0", "100", "-1"])
            result = await api.async_test_connection()
            assert result is True

    async def test_connection_failure_error(self, api):
        """Test connection failure with error response."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("error", None)
            result = await api.async_test_connection()
            assert result is False

    async def test_connection_failure_off(self, api):
        """Test connection failure when device off."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("off", None)
            result = await api.async_test_connection()
            assert result is True  # "off" is still a valid response

    async def test_connection_failure_exception(self, api):
        """Test connection failure with exception."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = CannotConnect("Connection failed")
            result = await api.async_test_connection()
            assert result is False


class TestDetectPlayerType:
    """Test player type detection."""

    async def test_detect_bd_player(self, api):
        """Test detecting BD player."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # BD players respond to GET_STATUS with data
            mock_request.return_value = ("ok", ["0", "100", "200", "0", "1", "5"])
            player_type = await api.async_detect_player_type()
            assert player_type == PlayerType.BD
            assert api._player_type == PlayerType.BD

    async def test_detect_uhd_player_error(self, api):
        """Test detecting UHD player (PST returns error)."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # First call (GET_STATUS) returns no data, second (PST) returns error
            mock_request.side_effect = [("ok", None), ("error", None)]
            player_type = await api.async_detect_player_type()
            assert player_type == PlayerType.UHD

    async def test_detect_bd_player_pst_ok(self, api):
        """Test detecting BD player when PST returns ok."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # First call (GET_STATUS) returns no data, second (PST) returns ok
            mock_request.side_effect = [("ok", None), ("ok", ["0", "0"])]
            player_type = await api.async_detect_player_type()
            assert player_type == PlayerType.BD


class TestSendCommand:
    """Test sending commands."""

    async def test_send_command_success(self, api):
        """Test successful command."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("ok", None)
            result = await api.async_send_command("POWER")
            assert result.success is True

    async def test_send_command_invalid(self, api):
        """Test invalid command."""
        result = await api.async_send_command("INVALID_CMD")
        assert result.success is False
        assert "Unknown command" in result.error

    async def test_send_command_error_response(self, api):
        """Test command with error response."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("error", None)
            result = await api.async_send_command("POWER")
            assert result.success is False

    async def test_send_command_device_off(self, api):
        """Test command when device is off."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("off", None)
            result = await api.async_send_command("POWER")
            assert result.success is False
            assert "off or unreachable" in result.error

    async def test_send_command_auto_detect_uhd_on_error(self, api):
        """Test auto-detecting UHD when command fails."""
        api._player_type = PlayerType.AUTO
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("error", None)
            await api.async_send_command("POWER")
            assert api._player_type == PlayerType.UHD

    async def test_send_command_auto_detect_bd_on_success(self, api):
        """Test auto-detecting BD when command succeeds."""
        api._player_type = PlayerType.AUTO
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("ok", None)
            await api.async_send_command("POWER")
            assert api._player_type == PlayerType.BD


class TestGetPlayStatus:
    """Test getting play status."""

    async def test_get_status_playing(self, api):
        """Test getting playing status."""
        api._player_type = PlayerType.UHD  # Skip extended status
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # PST: state=1 (playing), position=120
            mock_request.return_value = ("ok", ["1", "120"])
            status = await api.async_get_play_status()
            assert status.state == "playing"
            assert status.position == 120

    async def test_get_status_stopped(self, api):
        """Test getting stopped status."""
        api._player_type = PlayerType.UHD  # Skip extended status
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # PST: state=0 (stopped), position=0
            mock_request.return_value = ("ok", ["0", "0"])
            status = await api.async_get_play_status()
            assert status.state == "stopped"
            assert status.position == 0

    async def test_get_status_paused(self, api):
        """Test getting paused status."""
        api._player_type = PlayerType.UHD  # Skip extended status
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # PST: state=2 (paused), position=60
            mock_request.return_value = ("ok", ["2", "60"])
            status = await api.async_get_play_status()
            assert status.state == "paused"
            assert status.position == 60

    async def test_get_status_unknown_state(self, api):
        """Test getting status with unknown state value."""
        api._player_type = PlayerType.UHD
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # PST: state=99 (unknown), position=0
            mock_request.return_value = ("ok", ["99", "0"])
            status = await api.async_get_play_status()
            assert status.state == "unknown"

    async def test_get_status_no_disc(self, api):
        """Test getting status with no disc (negative position)."""
        api._player_type = PlayerType.UHD
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # Position=-2 means no disc
            mock_request.return_value = ("ok", ["0", "-2"])
            status = await api.async_get_play_status()
            assert status.state == "stopped"
            assert status.position == 0  # Should be normalized to 0

    async def test_get_status_off(self, api):
        """Test getting status when device off."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("off", None)
            status = await api.async_get_play_status()
            assert status.state == "off"

    async def test_get_status_error(self, api):
        """Test getting status with error."""
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = ("error", None)
            status = await api.async_get_play_status()
            assert status.state == "unknown"

    async def test_get_status_parse_error(self, api):
        """Test getting status with parse error."""
        api._player_type = PlayerType.UHD
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # Invalid data that will cause parse error
            mock_request.return_value = ("ok", ["not_a_number", "also_not"])
            status = await api.async_get_play_status()
            assert status.state == "stopped"  # Falls back to 0
            assert status.position == 0

    async def test_get_status_bd_with_extended(self, api):
        """Test getting status for BD player with extended info."""
        api._player_type = PlayerType.BD
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # First call: PST, Second call: GET_STATUS
            mock_request.side_effect = [
                ("ok", ["1", "120"]),  # PST: playing, position=120
                ("ok", ["1", "0", "0", "120", "7200", "3", "20"]),  # Extended status
            ]
            status = await api.async_get_play_status()
            assert status.state == "playing"
            assert status.position == 120
            assert status.duration == 7200
            assert status.chapter_current == 3
            assert status.chapter_total == 20

    async def test_get_status_bd_standby(self, api):
        """Test getting standby status for BD player."""
        api._player_type = PlayerType.BD
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            # First call: PST (stopped), Second call: GET_STATUS (ext_state=0)
            mock_request.side_effect = [
                ("ok", ["0", "0"]),  # PST: stopped
                ("ok", ["0", "0", "0", "0", "0", "0", "0"]),  # Extended: standby
            ]
            status = await api.async_get_play_status()
            assert status.state == "standby"

    async def test_get_status_bd_extended_error(self, api):
        """Test BD player when extended status fails."""
        api._player_type = PlayerType.BD
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                ("ok", ["1", "120"]),  # PST: playing
                ("error", None),  # Extended status fails
            ]
            status = await api.async_get_play_status()
            assert status.state == "playing"
            assert status.duration == 0  # No extended data

    async def test_get_status_bd_extended_parse_error(self, api):
        """Test BD player when extended status has parse error."""
        api._player_type = PlayerType.BD
        with patch.object(api, "_send_request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                ("ok", ["1", "120"]),  # PST: playing
                ("ok", ["not_a_number"]),  # Extended status with bad data
            ]
            status = await api.async_get_play_status()
            assert status.state == "playing"


class TestClose:
    """Test closing the API client."""

    async def test_close_with_session(self, api):
        """Test closing when session exists."""
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        api._session = mock_session

        await api.close()

        mock_session.close.assert_called_once()
        assert api._session is None

    async def test_close_without_session(self, api):
        """Test closing when no session exists."""
        api._session = None
        await api.close()  # Should not raise

    async def test_close_already_closed(self, api):
        """Test closing an already closed session."""
        mock_session = MagicMock()
        mock_session.closed = True
        api._session = mock_session

        await api.close()  # Should not call close again
