#!/usr/bin/env python3
"""Test script for Panasonic Blu-ray player integration.

This script tests connectivity and functionality with a real Panasonic Blu-ray
player before integrating with Home Assistant.

Usage:
    python scripts/test_player.py              # Run all tests
    python scripts/test_player.py --status     # Get player status only
    python scripts/test_player.py --power      # Test power on/off cycling
    python scripts/test_player.py --tray       # Test tray open/close
    python scripts/test_player.py --monitor    # Continuous status monitoring
    python scripts/test_player.py --commands   # Test sending commands (interactive)
    python scripts/test_player.py --debug      # Show raw HTTP protocol data
    python scripts/test_player.py --host IP    # Override IP from command line

Configuration:
    Copy .env.example to .env and set your player's IP address.
    Or set the PANASONIC_BD_HOST environment variable.
"""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import os
import socket
import subprocess
import sys
from pathlib import Path

# Add the custom_components directory to the path so we can import the integration
sys.path.insert(0, str(Path(__file__).parent.parent))

from custom_components.panasonic_bd.api import (
    PanasonicBlurayApi,
    CannotConnect,
)
from custom_components.panasonic_bd.const import COMMANDS, PlayerType


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}[PASS]{Colors.ENDC} {text}")


def print_failure(text: str) -> None:
    """Print a failure message."""
    print(f"{Colors.RED}[FAIL]{Colors.ENDC} {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}[WARN]{Colors.ENDC} {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.CYAN}[INFO]{Colors.ENDC} {text}")


def print_detail(label: str, value: str) -> None:
    """Print a labeled detail."""
    print(f"       {Colors.BLUE}{label}:{Colors.ENDC} {value}")


def load_dotenv() -> None:
    """Load environment variables from .env file if it exists."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ.setdefault(key, value)


def get_local_ip_addresses() -> list[tuple[str, str]]:
    """Get all local IP addresses and their network interfaces.

    Returns:
        List of tuples (interface_name, ip_address)
    """
    local_ips = []

    # Method 1: Try to get IP by connecting to an external address
    # This gives us the "primary" outbound interface
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # We don't actually connect, just use this to determine the outbound interface
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        local_ips.append(("primary", primary_ip))
    except (socket.error, OSError):
        pass

    # Method 2: Get all addresses from hostname
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ["127.0.0.1"] and ip not in [x[1] for x in local_ips]:
                local_ips.append(("hostname", ip))
    except socket.gaierror:
        pass

    # Method 3: Try common interface patterns (macOS/Linux)
    try:
        import subprocess

        result = subprocess.run(
            ["ifconfig"] if sys.platform == "darwin" else ["ip", "addr"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            import re

            # Look for inet addresses
            if sys.platform == "darwin":
                pattern = r"inet (\d+\.\d+\.\d+\.\d+)"
            else:
                pattern = r"inet (\d+\.\d+\.\d+\.\d+)"

            for match in re.finditer(pattern, result.stdout):
                ip = match.group(1)
                if ip not in ["127.0.0.1"] and ip not in [x[1] for x in local_ips]:
                    local_ips.append(("interface", ip))
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return local_ips


def check_same_subnet(player_ip: str, local_ips: list[tuple[str, str]]) -> tuple[bool, str]:
    """Check if the player IP is on the same subnet as any local interface.

    Args:
        player_ip: The IP address of the player
        local_ips: List of local IP addresses

    Returns:
        Tuple of (is_same_subnet, message)
    """
    if not local_ips:
        return False, "Could not determine local IP addresses"

    try:
        player_addr = ipaddress.ip_address(player_ip)
    except ValueError:
        return False, f"Invalid player IP address: {player_ip}"

    # Extract player's /24 subnet for comparison
    player_network = ipaddress.ip_network(f"{player_ip}/24", strict=False)

    # Check each local IP for subnet match
    # We use /24 subnet (most common home network setup)
    # Panasonic players require same-subnet communication
    for interface, local_ip in local_ips:
        try:
            # Create /24 network from local IP
            local_network = ipaddress.ip_network(f"{local_ip}/24", strict=False)

            # Check if player is in the same /24 subnet
            if player_addr in local_network:
                return True, f"Player {player_ip} is on same subnet as local {local_ip} ({local_network})"

        except ValueError:
            continue

    # Build helpful message about subnet mismatch
    local_subnets = []
    for _, ip in local_ips:
        try:
            network = ipaddress.ip_network(f"{ip}/24", strict=False)
            local_subnets.append(str(network))
        except ValueError:
            pass

    return False, (
        f"Player IP {player_ip} does not appear to be on the same subnet as this machine.\n"
        f"       Local subnets: {', '.join(set(local_subnets))}\n"
        f"       Player subnet: {player_network}\n"
        f"       The Panasonic player will not respond correctly to cross-subnet requests.\n"
        f"       \n"
        f"       To fix this, ensure you're running this test from a machine on the same\n"
        f"       network as your Blu-ray player (e.g., your Home Assistant server)."
    )


def ping_host(host: str, timeout: int = 3) -> tuple[bool, float | None, str]:
    """Ping a host to check if it's reachable.

    Args:
        host: IP address or hostname to ping
        timeout: Timeout in seconds

    Returns:
        Tuple of (success, response_time_ms, message)
    """
    # Determine ping command based on platform
    if sys.platform == "win32":
        # Windows: -n count, -w timeout in milliseconds
        cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
    else:
        # macOS/Linux: -c count, -W timeout in seconds
        cmd = ["ping", "-c", "1", "-W", str(timeout), host]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2,  # Add buffer for subprocess timeout
        )

        if result.returncode == 0:
            # Try to extract response time from output
            import re

            # Look for time= patterns (works on most systems)
            # Examples: "time=1.23 ms", "time=1.23ms", "time<1ms"
            time_match = re.search(r"time[=<](\d+\.?\d*)\s*ms", result.stdout, re.IGNORECASE)
            if time_match:
                response_time = float(time_match.group(1))
                return True, response_time, f"Ping successful ({response_time:.1f} ms)"
            else:
                return True, None, "Ping successful"
        else:
            # Ping failed - host unreachable
            return False, None, "Host did not respond to ping"

    except subprocess.TimeoutExpired:
        return False, None, f"Ping timed out after {timeout} seconds"
    except FileNotFoundError:
        return False, None, "Ping command not found"
    except Exception as e:
        return False, None, f"Ping error: {e}"


def test_ping(host: str) -> bool:
    """Test if the player responds to ping.

    Args:
        host: Player IP address

    Returns:
        True if ping successful
    """
    print_info(f"Pinging {host}...")

    success, response_time, message = ping_host(host)

    if success:
        print_success(message)
        print()
        print_info("The player is powered on or Quick Start is enabled.")
        return True
    else:
        print_failure(message)
        print()
        print_warning("The player may be:")
        print("       - Powered off completely")
        print("       - In standby without Quick Start enabled")
        print("       - On a different network/VLAN")
        print("       - Blocking ICMP ping requests")
        print()
        print_info("Tip: Enable 'Quick Start' in Player Settings -> System to allow")
        print("     the player to respond while in standby mode.")
        return False


async def test_connection(api: PanasonicBlurayApi) -> bool:
    """Test basic connectivity to the player.

    Args:
        api: The API client instance

    Returns:
        True if connection successful
    """
    print_info("Testing connection to player...")

    try:
        result = await api.async_test_connection()
        if result:
            print_success("Connection successful")
            return True
        else:
            print_failure("Connection failed - player did not respond correctly")
            return False
    except CannotConnect as e:
        print_failure(f"Connection failed: {e}")
        return False
    except Exception as e:
        print_failure(f"Unexpected error: {e}")
        return False


async def test_player_detection(api: PanasonicBlurayApi) -> PlayerType | None:
    """Detect the player type (BD or UHD).

    Args:
        api: The API client instance

    Returns:
        Detected PlayerType or None on failure
    """
    print_info("Detecting player type...")

    try:
        player_type = await api.async_detect_player_type()
        if player_type == PlayerType.BD:
            print_success("Detected: BD Player (full status support)")
            print_detail("Features", "Extended status, chapters, duration")
        elif player_type == PlayerType.UHD:
            print_success("Detected: UHD Player (limited status)")
            print_detail("Features", "Basic status, elapsed time only")
            if not api._player_key:
                print_warning("UHD player may need player key for remote commands")
        else:
            print_warning("Could not determine player type (AUTO)")
        return player_type
    except Exception as e:
        print_failure(f"Detection failed: {e}")
        return None


async def test_get_status(api: PanasonicBlurayApi) -> bool:
    """Get and display current player status.

    Args:
        api: The API client instance

    Returns:
        True if status retrieved successfully
    """
    print_info("Getting player status...")

    try:
        status = await api.async_get_play_status()

        print_success("Status retrieved successfully")
        print_detail("State", status.state)
        print_detail("Status", status.status_string)
        print_detail("Position", f"{status.position} seconds")

        if status.duration > 0:
            print_detail("Duration", f"{status.duration} seconds")
            progress = (status.position / status.duration * 100) if status.duration else 0
            print_detail("Progress", f"{progress:.1f}%")

        if status.chapter_current is not None:
            chapter_info = f"{status.chapter_current}"
            if status.chapter_total is not None:
                chapter_info += f" / {status.chapter_total}"
            print_detail("Chapter", chapter_info)

        return True

    except Exception as e:
        print_failure(f"Status retrieval failed: {e}")
        return False


async def test_power_cycle(api: PanasonicBlurayApi) -> bool:
    """Test power on/off functionality using POWER toggle command.

    Note: The player's status API does not distinguish between "standby" and
    "powered on but idle" - both return state=0. Therefore, this test can only
    verify that the POWER command is accepted by the player, not that the
    power state actually changed. Visual confirmation is required.

    Args:
        api: The API client instance

    Returns:
        True if power commands were sent successfully
    """
    print_info("Testing power toggle functionality...")
    print()
    print_warning("IMPORTANT: The player's status API cannot distinguish between")
    print("           'standby' and 'powered on idle' states. Both return state=0.")
    print("           Visual confirmation of power state changes is required.")
    print()

    # Get initial state for reference
    try:
        initial_status = await api.async_get_play_status()
        print_detail("Current reported state", initial_status.state)
        print_detail("Current status string", initial_status.status_string)
    except Exception as e:
        print_failure(f"Could not get initial state: {e}")
        return False

    # Test 1: Send first POWER toggle
    print()
    print_info("Test 1: Sending POWER command (toggle)...")
    result = await api.async_send_command("POWER")
    if not result.success:
        print_failure(f"Failed to send power command: {result.error}")
        return False
    print_success("POWER command accepted by player")
    print_info("Please visually confirm the player toggled power state.")

    # Wait a moment
    print_info("Waiting 5 seconds...")
    await asyncio.sleep(5)

    # Check status (for informational purposes)
    status = await api.async_get_play_status()
    print_detail("Reported state after toggle", status.state)

    # Test 2: Send second POWER toggle to return to original state
    print()
    print_info("Test 2: Sending POWER command again (toggle back)...")
    result = await api.async_send_command("POWER")
    if not result.success:
        print_failure(f"Failed to send power command: {result.error}")
        return False
    print_success("POWER command accepted by player")
    print_info("Please visually confirm the player toggled back.")

    # Wait and check final status
    print_info("Waiting 3 seconds...")
    await asyncio.sleep(3)

    final_status = await api.async_get_play_status()
    print_detail("Final reported state", final_status.state)

    print()
    print_success("Power toggle test completed!")
    print()
    print_info("Summary:")
    print("       - Both POWER commands were accepted by the player")
    print("       - Status API limitation: cannot detect on/off state when idle")
    print("       - The integration will show 'standby' even when player is on HOME menu")
    print("       - State correctly changes to 'playing'/'paused' during playback")

    return True


async def test_tray(api: PanasonicBlurayApi) -> bool:
    """Test tray open/close functionality.

    This tests the OP_CL (open/close) command which physically opens and closes
    the disc tray. This is a safe test that provides visual confirmation the
    player is responding to commands.

    Args:
        api: The API client instance

    Returns:
        True if tray commands were sent successfully
    """
    print_info("Testing tray open/close functionality...")
    print()
    print_warning("This will physically open and close the disc tray.")
    print_info("Please ensure there's clearance in front of the player.")
    print()

    # Test 1: Open tray
    print_info("Opening tray...")
    result = await api.async_send_command("OP_CL")
    if not result.success:
        print_failure(f"Failed to send tray command: {result.error}")
        return False
    print_success("OP_CL command accepted")
    print_info("Please confirm the tray is opening...")

    # Wait for tray to open
    print_info("Waiting 5 seconds...")
    await asyncio.sleep(5)

    # Test 2: Close tray
    print()
    print_info("Closing tray...")
    result = await api.async_send_command("OP_CL")
    if not result.success:
        print_failure(f"Failed to send tray command: {result.error}")
        return False
    print_success("OP_CL command accepted")
    print_info("Please confirm the tray is closing...")

    # Wait for tray to close
    print_info("Waiting 3 seconds...")
    await asyncio.sleep(3)

    print()
    print_success("Tray test completed!")
    print()
    print_info("If the tray opened and closed, the player is responding correctly")
    print_info("to remote commands. The integration should work properly.")

    return True


async def test_debug_request(host: str, port: int = 80) -> bool:
    """Send a raw HTTP request and display the full exchange.

    This shows the actual HTTP protocol exchange for debugging purposes.
    Useful when the player isn't responding as expected.

    Args:
        host: Player IP address
        port: HTTP port (default 80)

    Returns:
        True if request completed (regardless of response)
    """
    import aiohttp

    print_info("Raw HTTP protocol debug mode")
    print()

    url = f"http://{host}:{port}/WAN/dvdr/dvdr_ctrl.cgi"
    data = "cCMD_PST.x=100&cCMD_PST.y=100"
    headers = {
        "User-Agent": "MEI-LAN-REMOTE-CALL",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    print(f"{Colors.CYAN}━━━ REQUEST ━━━{Colors.ENDC}")
    print(f"POST {url}")
    for key, value in headers.items():
        print(f"{key}: {value}")
    print()
    print(data)
    print()

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=data, headers=headers) as response:
                print(f"{Colors.CYAN}━━━ RESPONSE ━━━{Colors.ENDC}")
                print(f"HTTP {response.status} {response.reason}")
                for key, value in response.headers.items():
                    print(f"{key}: {value}")
                print()

                raw_bytes = await response.read()
                print(f"{Colors.CYAN}━━━ BODY ({len(raw_bytes)} bytes) ━━━{Colors.ENDC}")

                # Check for gzip
                if len(raw_bytes) >= 2 and raw_bytes[0:2] == b'\x1f\x8b':
                    print(f"{Colors.YELLOW}[gzip compressed]{Colors.ENDC}")
                    import gzip
                    try:
                        raw_bytes = gzip.decompress(raw_bytes)
                        print(f"{Colors.GREEN}[decompressed to {len(raw_bytes)} bytes]{Colors.ENDC}")
                    except Exception as e:
                        print(f"{Colors.RED}[decompression failed: {e}]{Colors.ENDC}")

                # Show hex dump for first 64 bytes
                print()
                print(f"{Colors.BLUE}Hex:{Colors.ENDC}", end="")
                for i, b in enumerate(raw_bytes[:64]):
                    if i % 16 == 0:
                        print()
                        print(f"  {i:04x}: ", end="")
                    print(f"{b:02x} ", end="")
                if len(raw_bytes) > 64:
                    print(f"\n  ... ({len(raw_bytes) - 64} more bytes)")
                print()

                # Show as text
                print()
                try:
                    text = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw_bytes.decode("latin-1")

                print(f"{Colors.BLUE}Text:{Colors.ENDC}")
                for line in text.strip().split("\n")[:20]:
                    print(f"  {line}")

                print()
                print_success("Debug request completed")
                return True

    except aiohttp.ClientError as e:
        print(f"{Colors.RED}━━━ CONNECTION ERROR ━━━{Colors.ENDC}")
        print(f"Error: {e}")
        print()
        print_failure("Could not connect to player")
        return False
    except asyncio.TimeoutError:
        print(f"{Colors.RED}━━━ TIMEOUT ━━━{Colors.ENDC}")
        print("Request timed out after 10 seconds")
        print()
        print_failure("Connection timed out")
        return False


async def test_monitor(api: PanasonicBlurayApi, interval: float = 2.0) -> bool:
    """Continuously monitor player status.

    This polls the player status at regular intervals and displays changes.
    Useful for testing playback state transitions during actual disc playback.

    Args:
        api: The API client instance
        interval: Polling interval in seconds

    Returns:
        True (always, unless interrupted)
    """
    print_info("Continuous status monitoring mode")
    print()
    print_info(f"Polling every {interval} seconds. Press Ctrl+C to stop.")
    print()

    last_state = None
    last_position = None
    poll_count = 0

    try:
        while True:
            poll_count += 1
            try:
                status = await api.async_get_play_status()

                # Format the status line
                state_changed = last_state != status.state
                position_str = f"{status.position}s"
                if status.duration > 0:
                    progress = (status.position / status.duration * 100)
                    position_str = f"{status.position}/{status.duration}s ({progress:.1f}%)"

                chapter_str = ""
                if status.chapter_current is not None:
                    chapter_str = f" Ch.{status.chapter_current}"
                    if status.chapter_total:
                        chapter_str = f" Ch.{status.chapter_current}/{status.chapter_total}"

                # Use different colors based on state
                if status.state == "playing":
                    state_color = Colors.GREEN
                elif status.state == "paused":
                    state_color = Colors.YELLOW
                elif status.state == "standby":
                    state_color = Colors.CYAN
                else:
                    state_color = Colors.ENDC

                # Print status (with state change indicator)
                change_indicator = " *" if state_changed else ""
                print(
                    f"[{poll_count:4d}] "
                    f"{state_color}{status.state:10}{Colors.ENDC} "
                    f"| {position_str:20}{chapter_str}{change_indicator}"
                )

                last_state = status.state
                last_position = status.position

            except CannotConnect:
                print(f"[{poll_count:4d}] {Colors.RED}UNAVAILABLE{Colors.ENDC} | Connection failed")
            except Exception as e:
                print(f"[{poll_count:4d}] {Colors.RED}ERROR{Colors.ENDC} | {e}")

            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        print()
        print_info("Monitoring stopped.")
        return True


async def test_commands(api: PanasonicBlurayApi) -> bool:
    """Test sending commands to the player (interactive).

    Args:
        api: The API client instance

    Returns:
        True if command test completed
    """
    print_info("Command testing mode")
    print()

    # Show available safe commands
    safe_commands = ["DSPSEL", "PLAYBACKINFO"]
    print(f"  Safe test commands: {', '.join(safe_commands)}")
    print()

    # List all available commands
    print("  All available commands:")
    command_list = sorted(COMMANDS.keys())
    for i in range(0, len(command_list), 8):
        row = command_list[i : i + 8]
        print(f"    {', '.join(row)}")
    print()

    # Interactive command testing
    print(f"{Colors.YELLOW}Enter commands to test (or 'quit' to exit):{Colors.ENDC}")
    print(f"{Colors.YELLOW}Note: Some commands may affect playback or player state.{Colors.ENDC}")
    print()

    while True:
        try:
            command = input(f"{Colors.CYAN}Command> {Colors.ENDC}").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting command test mode.")
            break

        if not command or command in ("QUIT", "EXIT", "Q"):
            break

        if command not in COMMANDS:
            print_warning(f"Unknown command: {command}")
            continue

        print_info(f"Sending command: {command}")
        try:
            result = await api.async_send_command(command)
            if result.success:
                print_success(f"Command '{command}' executed successfully")
            else:
                print_failure(f"Command '{command}' failed: {result.error}")
        except Exception as e:
            print_failure(f"Command error: {e}")

    return True


async def run_tests(
    host: str,
    player_key: str | None = None,
    status_only: bool = False,
    test_power: bool = False,
    test_tray_mode: bool = False,
    test_monitor_mode: bool = False,
    test_debug_mode: bool = False,
    test_cmds: bool = False,
) -> int:
    """Run the test suite.

    Args:
        host: Player IP address
        player_key: Optional player key for UHD authentication
        status_only: Only get status, skip other tests
        test_power: Test power on/off cycling
        test_tray_mode: Test tray open/close
        test_monitor_mode: Continuous status monitoring
        test_debug_mode: Show raw HTTP protocol data
        test_cmds: Enable interactive command testing

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("Panasonic Blu-ray Player Test")

    # Display configuration
    print_info(f"Player IP: {host}")
    if player_key:
        print_info(f"Player Key: {'*' * 8}...{player_key[-4:]}")
    print()

    # Special mode: Debug raw HTTP protocol
    if test_debug_mode:
        print_header("Raw HTTP Debug")
        await test_debug_request(host)
        return 0

    # Special mode: Continuous monitoring (skips normal tests)
    if test_monitor_mode:
        api = PanasonicBlurayApi(host=host, player_key=player_key)
        try:
            print_header("Status Monitor")
            await test_monitor(api)
            return 0
        finally:
            await api.close()

    # Test 0: Ping test (first check)
    print_header("Ping Test")
    ping_success = test_ping(host)

    if not ping_success:
        print()
        print_warning("Ping failed, but continuing with other tests...")
        print_info("Some players may block ping but still respond to HTTP requests.")
        print()

    # Check network subnet
    print_header("Network Validation")
    local_ips = get_local_ip_addresses()

    if local_ips:
        print_info("Local IP addresses detected:")
        for interface, ip in local_ips:
            print_detail(interface, ip)
        print()

    is_same_subnet, subnet_message = check_same_subnet(host, local_ips)

    if is_same_subnet:
        print_success(subnet_message)
    else:
        print_failure(subnet_message)
        print()
        print_warning("The player may not respond correctly. Continuing anyway...")
        print()

    # Create API client
    api = PanasonicBlurayApi(host=host, player_key=player_key)

    try:
        results = {"ping": ping_success, "connection": False, "status": False}

        # Test 1: Connection
        print_header("Connection Test")
        results["connection"] = await test_connection(api)

        if not results["connection"]:
            print()
            print_failure("Connection failed. Cannot continue with other tests.")
            print()
            print("Troubleshooting tips:")
            print("  1. Ensure the player is powered on (not in standby without Quick Start)")
            print("  2. Verify Remote Device Operation is enabled on the player")
            print("  3. Check that the IP address is correct")
            print("  4. Ensure no firewall is blocking port 80")
            return 1

        # Test 2: Player Detection (skipped in status-only mode)
        if not status_only:
            print_header("Player Detection")
            player_type = await test_player_detection(api)
            results["detection"] = player_type is not None

        # Test 3: Status
        print_header("Player Status")
        results["status"] = await test_get_status(api)

        # Test 4: Power cycle (optional)
        if test_power:
            print_header("Power Cycle Test")
            results["power"] = await test_power_cycle(api)

        # Test 5: Tray test (optional)
        if test_tray_mode:
            print_header("Tray Open/Close Test")
            results["tray"] = await test_tray(api)

        # Test 6: Commands (optional, interactive)
        if test_cmds:
            print_header("Command Testing")
            await test_commands(api)

        # Summary
        print_header("Test Summary")
        all_passed = all(results.values())

        for test_name, passed in results.items():
            if passed:
                print_success(f"{test_name.title()} test passed")
            else:
                print_failure(f"{test_name.title()} test failed")

        print()
        if all_passed:
            print(f"{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.ENDC}")
            print()
            print("Your player is ready to use with the Home Assistant integration.")
            return 0
        else:
            print(f"{Colors.YELLOW}{Colors.BOLD}Some tests had issues.{Colors.ENDC}")
            print()
            print("Review the output above for details.")
            return 1

    finally:
        await api.close()


def main() -> int:
    """Main entry point."""
    # Load .env file
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Test Panasonic Blu-ray player connectivity and functionality.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_player.py                    Run all tests
  python scripts/test_player.py --status           Get player status only
  python scripts/test_player.py --power            Test power on/off cycling
  python scripts/test_player.py --tray             Test disc tray open/close
  python scripts/test_player.py --monitor          Continuous status monitoring
  python scripts/test_player.py --debug            Show raw HTTP protocol data
  python scripts/test_player.py --commands         Interactive command testing
  python scripts/test_player.py --host 192.168.1.50  Use specific IP

Configuration:
  Set PANASONIC_BD_HOST in .env file or environment variable.
  For UHD players, also set PANASONIC_BD_PLAYER_KEY if needed.
        """,
    )
    parser.add_argument(
        "--host",
        "-H",
        help="Player IP address (overrides .env file)",
    )
    parser.add_argument(
        "--key",
        "-k",
        help="Player key for UHD authentication (overrides .env file)",
    )
    parser.add_argument(
        "--status",
        "-s",
        action="store_true",
        help="Only get player status, skip other tests",
    )
    parser.add_argument(
        "--power",
        "-p",
        action="store_true",
        help="Test power on/off cycling",
    )
    parser.add_argument(
        "--tray",
        "-t",
        action="store_true",
        help="Test disc tray open/close (physically verifiable)",
    )
    parser.add_argument(
        "--monitor",
        "-m",
        action="store_true",
        help="Continuous status monitoring (Ctrl+C to stop)",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Show raw HTTP protocol exchange for debugging",
    )
    parser.add_argument(
        "--commands",
        "-c",
        action="store_true",
        help="Enable interactive command testing",
    )

    args = parser.parse_args()

    # Get configuration
    host = args.host or os.environ.get("PANASONIC_BD_HOST")
    player_key = args.key or os.environ.get("PANASONIC_BD_PLAYER_KEY")

    if not host:
        print(f"{Colors.RED}Error: No player IP address specified.{Colors.ENDC}")
        print()
        print("Set the IP address using one of these methods:")
        print("  1. Create a .env file with PANASONIC_BD_HOST=your_ip")
        print("  2. Set the PANASONIC_BD_HOST environment variable")
        print("  3. Use the --host command line argument")
        print()
        print("See .env.example for a template configuration file.")
        return 1

    # Validate IP address format
    try:
        ipaddress.ip_address(host)
    except ValueError:
        print(f"{Colors.RED}Error: Invalid IP address format: {host}{Colors.ENDC}")
        return 1

    # Run tests
    return asyncio.run(
        run_tests(
            host=host,
            player_key=player_key,
            status_only=args.status,
            test_power=args.power,
            test_tray_mode=args.tray,
            test_monitor_mode=args.monitor,
            test_debug_mode=args.debug,
            test_cmds=args.commands,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
