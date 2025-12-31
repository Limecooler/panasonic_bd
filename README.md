# Panasonic Blu-ray Player Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/Limecooler/panasonic_bluray.svg)](https://github.com/Limecooler/panasonic_bluray/releases)

Control your Panasonic Blu-ray player from Home Assistant with full remote control functionality.

## Features

- **Media Player Entity**: Play, pause, stop, skip tracks, power on/off
- **Remote Entity**: Send any remote control command (60+ commands)
- **Status Monitoring**: Track playback state, position, and duration
- **BD & UHD Support**: Works with both standard Blu-ray and 4K UHD players
- **Multiple Players**: Add as many Blu-ray players as you have - each gets its own device

## Supported Models

### Fully Supported (BD Players - 2011/2012)

| Model | Notes |
|-------|-------|
| DMP-BDT110 | Full functionality |
| DMP-BDT120 | Full functionality |
| DMP-BDT210 | Full functionality |
| DMP-BDT220 | Full functionality |
| DMP-BDT221 | Full functionality |
| DMP-BDT310 | Full functionality |
| DMP-BDT320 | Full functionality |
| DMP-BDT500 | Full functionality |
| DMP-BBT01 | Full functionality |

### UHD Players (2018+) - Requires Player Key or Patched Firmware

| Model | Notes |
|-------|-------|
| DP-UB420 / DP-UB424 | Limited status, requires authentication |
| DP-UB820 / DP-UB824 | Limited status, requires authentication |
| DP-UB9000 / DP-UB9004 | Limited status, requires authentication |

> **Note**: UHD players have limited status reporting (elapsed time only, no chapter info) and require either a player key or patched firmware for remote control commands.

## Prerequisites

### Network Requirements

⚠️ **Important**: Your Blu-ray player must be on the **same subnet** as your Home Assistant server. Cross-subnet connections are not supported by the player's protocol.

### Player Configuration

Before installing this integration, you must configure your Blu-ray player:

#### For BD Players (DMP-BDT series):

1. Turn on your Blu-ray player
2. Press **HOME** on the remote
3. Navigate to **Player Settings** → **Network** → **Network Settings** → **Remote Device Settings**
4. Set **Remote Device Operation** to **On**
5. Set **Registration Type** to **Automatic**

#### To Enable Network Standby (recommended):

This allows Home Assistant to turn on the player from standby:

1. Navigate to **Player Settings** → **System** → **Quick Start**
2. Set **Quick Start** to **On**

#### For UHD Players (DP-UB series):

In addition to the above steps:

1. Navigate to **Player Settings** → **Network** → **Voice Control**
2. Set **Voice Control** to **On** (if available - discontinued June 2023)

> **Note for UHD owners**: If Voice Control is no longer available on your firmware, you may need patched firmware or a player key. See [UHD Authentication](#uhd-authentication) below.

### Finding Your Player's IP Address

1. On your Blu-ray player, go to **Player Settings** → **Network** → **Network Status**
2. Note the **IP Address** shown (e.g., `192.168.1.100`)
3. Consider setting a static IP or DHCP reservation in your router to prevent the IP from changing

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on **Integrations**
3. Click the **three dots** menu in the top right corner
4. Select **Custom repositories**
5. Add the repository URL: `https://github.com/Limecooler/panasonic_bluray`
6. Select **Integration** as the category
7. Click **Add**
8. Search for "Panasonic Blu-ray" and click **Download**
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/Limecooler/panasonic_bluray/releases)
2. Extract the `panasonic_bluray` folder
3. Copy it to your `config/custom_components/` directory
4. Restart Home Assistant

## Configuration

### Adding the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Panasonic Blu-ray"
4. Enter the configuration:
   - **IP Address**: Your player's IP address (e.g., `192.168.1.100`)
   - **Device Name**: A friendly name (optional, defaults to "Panasonic Blu-ray")
   - **Player Key**: For UHD models only, if required (see below)
5. Click **Submit**

### Adding Multiple Players

You can add as many Blu-ray players as you have:

1. After adding the first player, click **+ Add Integration** again
2. Search for "Panasonic Blu-ray" again
3. Enter the IP address of your second player
4. Give it a unique name (e.g., "Bedroom Blu-ray")
5. Repeat for additional players

Each player will appear as a separate device with its own entities:
- `media_player.living_room_blu_ray` + `remote.living_room_blu_ray_remote`
- `media_player.bedroom_blu_ray` + `remote.bedroom_blu_ray_remote`

### UHD Authentication

UHD players (DP-UB series) require authentication for remote control commands. You have two options:

**Option 1: Patched Firmware**
- Players with modified firmware do not require a player key
- See [AVForums](https://www.avsforum.com/forums/blu-ray-dvd-player-multiregion-hacks.126/) for information

**Option 2: Player Key**
- If you have a player key, enter it during configuration
- The key is a 32-character hexadecimal string
- Contact the community for assistance obtaining a key

## Usage

### Media Player Entity

The integration creates a media player entity: `media_player.panasonic_blu_ray`

#### Supported Actions:

| Action | Description |
|--------|-------------|
| Turn On | Wake player from standby |
| Turn Off | Put player in standby |
| Play | Start/resume playback |
| Pause | Pause playback |
| Stop | Stop playback |
| Next Track | Skip to next chapter/track |
| Previous Track | Skip to previous chapter/track |

#### State Information:

- **State**: off, idle, playing, paused
- **Media Position**: Current playback position (seconds)
- **Media Duration**: Total duration (BD players only)
- **Media Track**: Current chapter number (BD players only)

#### Extra Attributes (visible in Developer Tools):

| Attribute | Description |
|-----------|-------------|
| `player_status` | Detailed status (Power Off, Tray Open, Stopped, Playback, Pause Playback) |
| `player_type` | Detected type (BD or UHD) |
| `chapter_current` | Current chapter number (BD players only) |
| `chapter_total` | Total chapters in title (BD players only) |

> **Note**: UHD players only report elapsed time. Duration and chapter information are not available on UHD models.

#### Example Automations:

**Dim lights when playing:**

```yaml
automation:
  - alias: "Dim lights for movie"
    trigger:
      - platform: state
        entity_id: media_player.panasonic_blu_ray
        to: "playing"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 20
```

**Restore lights when stopped:**

```yaml
automation:
  - alias: "Restore lights after movie"
    trigger:
      - platform: state
        entity_id: media_player.panasonic_blu_ray
        from: "playing"
        to: "idle"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_pct: 100
```

### Remote Entity

The integration also creates a remote entity: `remote.panasonic_blu_ray_remote`

Use `remote.send_command` to send any button press from the physical remote.

#### Example Service Calls:

**Open/Close disc tray:**

```yaml
service: remote.send_command
target:
  entity_id: remote.panasonic_blu_ray_remote
data:
  command: OP_CL
```

**Navigate to Home menu:**

```yaml
service: remote.send_command
target:
  entity_id: remote.panasonic_blu_ray_remote
data:
  command: MLTNAVI
```

**Send multiple commands:**

```yaml
service: remote.send_command
target:
  entity_id: remote.panasonic_blu_ray_remote
data:
  command:
    - MLTNAVI
    - DOWN
    - DOWN
    - SELECT
  delay_secs: 0.5
```

**Repeat a command:**

```yaml
service: remote.send_command
target:
  entity_id: remote.panasonic_blu_ray_remote
data:
  command: SKIPFWD
  num_repeats: 3
```

### Available Commands

#### Power

| Command | Description |
|---------|-------------|
| `POWER` | Toggle power (on/standby) |
| `POWERON` | Power on only |
| `POWEROFF` | Power off (standby) only |

#### Disc Tray

| Command | Description |
|---------|-------------|
| `OP_CL` | Open/Close disc tray |

#### Playback

| Command | Description |
|---------|-------------|
| `PLAYBACK` | Play |
| `PAUSE` | Pause |
| `STOP` | Stop |
| `CUE` | Fast forward |
| `REV` | Rewind |
| `SKIPFWD` | Skip forward (next chapter) |
| `SKIPREV` | Skip back (previous chapter) |
| `MNSKIP` | Manual skip +60 seconds |
| `MNBACK` | Manual skip -10 seconds |
| `SHFWD1` - `SHFWD5` | Shuttle forward (5 speeds) |
| `SHREV1` - `SHREV5` | Shuttle reverse (5 speeds) |
| `JLEFT` | Jog left (frame back) |
| `JRIGHT` | Jog right (frame forward) |

#### Navigation

| Command | Description |
|---------|-------------|
| `UP` | Navigate up |
| `DOWN` | Navigate down |
| `LEFT` | Navigate left |
| `RIGHT` | Navigate right |
| `SELECT` | OK / Select |
| `RETURN` | Return / Back |
| `EXIT` | Exit menu |

#### Menus

| Command | Description |
|---------|-------------|
| `MLTNAVI` | Home menu |
| `DSPSEL` | Display / Status |
| `TITLE` | Top menu / Title menu |
| `MENU` | Disc menu |
| `PUPMENU` | Pop-up menu |
| `SETUP` | Setup menu |

#### Number Keys

| Command | Description |
|---------|-------------|
| `D0` - `D9` | Numbers 0-9 |
| `D12` | Number 12 |
| `SHARP` | # key |
| `CLEAR` | * / Cancel |

#### Color Buttons

| Command | Description |
|---------|-------------|
| `RED` | Red button |
| `GREEN` | Green button |
| `BLUE` | Blue button |
| `YELLOW` | Yellow button |

#### Apps & Network

| Command | Description |
|---------|-------------|
| `NETFLIX` | Netflix (if supported) |
| `SKYPE` | Skype (older models) |
| `V_CAST` | VIERA Cast |
| `NETWORK` | Network menu |
| `MIRACAST` | Screen mirroring |

#### Audio & Video (UHD models)

| Command | Description |
|---------|-------------|
| `AUDIOSEL` | Audio selection |
| `TITLEONOFF` | Subtitle toggle |
| `CLOSED_CAPTION` | Closed captions |
| `3D` | 3D mode |
| `HDR_PICTUREMODE` | HDR picture mode |
| `PICTURESETTINGS` | Picture settings |
| `SOUNDEFFECT` | Sound effects |
| `HIGHCLARITY` | High clarity sound |
| `PLAYBACKINFO` | Playback information |
| `OSDONOFF` | On-screen display toggle |
| `P_IN_P` | Picture-in-picture |

## Troubleshooting

### "Cannot connect to device"

1. **Verify network connectivity**: Ensure Home Assistant and the player are on the same subnet
2. **Check player settings**: Confirm Remote Device Operation is ON and Registration Type is Automatic
3. **Test with ping**: From your Home Assistant host, try `ping <player-ip>`
4. **Check firewall**: Ensure port 80 is not blocked between HA and the player
5. **Restart player**: Power cycle the Blu-ray player completely (not just standby)

### Player shows as "Unavailable"

1. **Player is off**: The player must be in Quick Start mode to respond when "off"
2. **IP changed**: If your player's IP changed, reconfigure the integration
3. **Network issue**: Check your network connection

### Commands not working (UHD players)

1. **Voice Control disabled**: Panasonic discontinued Voice Control in June 2023
2. **Need player key**: UHD players require authentication for remote commands
3. **Firmware issue**: Consider patched firmware for full functionality

### Status not updating

1. **Polling delay**: Status updates every 10 seconds
2. **UHD limitation**: UHD players only report elapsed time, not duration or chapters
3. **Standby state**: Some status info unavailable in standby

### Slow response to commands

This is a known limitation of the player's network protocol. Commands may take 1-3 seconds to execute. Avoid sending rapid repeated commands.

## Known Limitations

1. **Same subnet required**: Player must be on same network subnet as Home Assistant
2. **UHD status limited**: UHD players only report elapsed time, no duration or chapters
3. **UHD authentication**: UHD players need player key or patched firmware for commands
4. **No volume control**: Blu-ray players do not have volume control over network
5. **Response latency**: Commands may take 1-3 seconds to execute
6. **IP-based identification**: Changing the player's IP requires reconfiguring the integration

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Protocol reverse-engineering based on work from the [openHAB community](https://www.openhab.org/addons/bindings/panasonicbdp/)
- Inspired by the [Panacotta library](https://github.com/u1f35c/python-panacotta)
- Thanks to the Home Assistant community for testing and feedback
