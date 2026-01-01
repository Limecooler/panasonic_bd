"""Constants for the Panasonic Blu-ray integration."""
from __future__ import annotations

from datetime import timedelta
from enum import Enum
from typing import Final

# Integration info
DOMAIN: Final = "panasonic_bd"
NAME: Final = "Panasonic Blu-ray Player"
VERSION: Final = "1.0.1"

# Configuration
CONF_PLAYER_KEY: Final = "player_key"
DEFAULT_NAME: Final = "Panasonic Blu-ray"
DEFAULT_PORT: Final = 80
DEFAULT_TIMEOUT: Final = 5

# Polling intervals
SCAN_INTERVAL: Final = timedelta(seconds=10)
MIN_TIME_BETWEEN_SCANS: Final = SCAN_INTERVAL
MIN_TIME_BETWEEN_FORCED_SCANS: Final = timedelta(seconds=1)

# API constants
API_ENDPOINT: Final = "/WAN/dvdr/dvdr_ctrl.cgi"
API_USER_AGENT: Final = "MEI-LAN-REMOTE-CALL"


class PlayerType(Enum):
    """Player type enumeration."""

    AUTO = "auto"
    BD = "bd"
    UHD = "uhd"


class PlayerStatus(Enum):
    """Player status values (OpenHAB compatible)."""

    POWER_OFF = "Power Off"
    TRAY_OPEN = "Tray Open"
    STOPPED = "Stopped"
    PLAYBACK = "Playback"
    PAUSE_PLAYBACK = "Pause Playback"
    UNKNOWN = "Unknown"


# Complete command list - all commands from OpenHAB and albaintor integrations
# BD Player Commands (2011-2012 models)
BD_COMMANDS: Final[set[str]] = {
    # Power
    "POWER",
    "POWERON",
    "POWEROFF",
    # Tray
    "OP_CL",
    # Playback
    "PLAYBACK",
    "PAUSE",
    "STOP",
    "CUE",
    "REV",
    "SKIPFWD",
    "SKIPREV",
    # Shuttle (variable speed)
    "SHFWD1",
    "SHFWD2",
    "SHFWD3",
    "SHFWD4",
    "SHFWD5",
    "SHREV1",
    "SHREV2",
    "SHREV3",
    "SHREV4",
    "SHREV5",
    # Jog (frame-by-frame)
    "JLEFT",
    "JRIGHT",
    # Navigation
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "SELECT",
    "RETURN",
    "EXIT",
    # Menu
    "MLTNAVI",
    "DSPSEL",
    "TITLE",
    "MENU",
    "PUPMENU",
    "SETUP",
    # Numbers
    "D0",
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7",
    "D8",
    "D9",
    "D12",
    "SHARP",
    "CLEAR",
    # Color Buttons
    "RED",
    "GREEN",
    "BLUE",
    "YELLOW",
    # Apps/Network
    "NETFLIX",
    "SKYPE",
    "V_CAST",
    "NETWORK",
    # Audio/Video
    "AUDIOSEL",
    "3D",
    "OSDONOFF",
    "P_IN_P",
    "PIP",
    # Advanced
    "PICTMD",
    "2NDARY",
    "CHROMA",
    "KEYS",
    "DETAIL",
    "RESOLUTN",
}

# UHD Player Additional Commands (2018+ models)
UHD_COMMANDS: Final[set[str]] = {
    # Skip
    "MNSKIP",
    "MNBACK",
    # Subtitles
    "TITLEONOFF",
    "CLOSED_CAPTION",
    # Picture
    "HDR_PICTUREMODE",
    "PICTURESETTINGS",
    # Audio
    "SOUNDEFFECT",
    "HIGHCLARITY",
    # Other
    "PLAYBACKINFO",
    "MIRACAST",
    "SKIP_THE_TRAILER",
}

# All supported commands
COMMANDS: Final[set[str]] = BD_COMMANDS | UHD_COMMANDS

# Command descriptions for documentation
COMMAND_DESCRIPTIONS: Final[dict[str, str]] = {
    # Power
    "POWER": "Toggle power (on/standby)",
    "POWERON": "Power on only",
    "POWEROFF": "Power off (standby) only",
    # Tray
    "OP_CL": "Open/Close disc tray",
    # Playback
    "PLAYBACK": "Play",
    "PAUSE": "Pause",
    "STOP": "Stop",
    "CUE": "Fast forward",
    "REV": "Rewind",
    "SKIPFWD": "Skip forward (next chapter)",
    "SKIPREV": "Skip back (previous chapter)",
    "MNSKIP": "Manual skip +60 seconds",
    "MNBACK": "Manual skip -10 seconds",
    # Shuttle
    "SHFWD1": "Shuttle forward speed 1",
    "SHFWD2": "Shuttle forward speed 2",
    "SHFWD3": "Shuttle forward speed 3",
    "SHFWD4": "Shuttle forward speed 4",
    "SHFWD5": "Shuttle forward speed 5",
    "SHREV1": "Shuttle reverse speed 1",
    "SHREV2": "Shuttle reverse speed 2",
    "SHREV3": "Shuttle reverse speed 3",
    "SHREV4": "Shuttle reverse speed 4",
    "SHREV5": "Shuttle reverse speed 5",
    # Jog
    "JLEFT": "Jog left (frame back)",
    "JRIGHT": "Jog right (frame forward)",
    # Navigation
    "UP": "Navigate up",
    "DOWN": "Navigate down",
    "LEFT": "Navigate left",
    "RIGHT": "Navigate right",
    "SELECT": "OK / Select",
    "RETURN": "Return / Back",
    "EXIT": "Exit menu",
    # Menu
    "MLTNAVI": "Home menu",
    "DSPSEL": "Display / Status",
    "TITLE": "Top menu / Title menu",
    "MENU": "Disc menu",
    "PUPMENU": "Pop-up menu",
    "SETUP": "Setup menu",
    # Numbers
    "D0": "Number 0",
    "D1": "Number 1",
    "D2": "Number 2",
    "D3": "Number 3",
    "D4": "Number 4",
    "D5": "Number 5",
    "D6": "Number 6",
    "D7": "Number 7",
    "D8": "Number 8",
    "D9": "Number 9",
    "D12": "Number 12",
    "SHARP": "# key",
    "CLEAR": "* / Cancel",
    # Color Buttons
    "RED": "Red button",
    "GREEN": "Green button",
    "BLUE": "Blue button",
    "YELLOW": "Yellow button",
    # Apps/Network
    "NETFLIX": "Netflix",
    "SKYPE": "Skype",
    "V_CAST": "VIERA Cast",
    "NETWORK": "Network menu",
    "MIRACAST": "Screen mirroring",
    # Audio/Video
    "AUDIOSEL": "Audio selection",
    "3D": "3D mode toggle",
    "OSDONOFF": "On-screen display toggle",
    "P_IN_P": "Picture-in-picture",
    "PIP": "Picture-in-picture (alternate)",
    "TITLEONOFF": "Subtitle toggle",
    "CLOSED_CAPTION": "Closed captions",
    "HDR_PICTUREMODE": "HDR picture mode",
    "PICTURESETTINGS": "Picture settings",
    "SOUNDEFFECT": "Sound effects",
    "HIGHCLARITY": "High clarity sound",
    "PLAYBACKINFO": "Playback information",
    "SKIP_THE_TRAILER": "Skip trailer",
    # Advanced
    "PICTMD": "Picture mode",
    "2NDARY": "Secondary audio/video",
    "CHROMA": "Chroma settings",
    "KEYS": "Key lock",
    "DETAIL": "Detail settings",
    "RESOLUTN": "Resolution settings",
}
