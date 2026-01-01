# InputFlow Usage Guide

## Overview

InputFlow provides two main applications:
- **Server**: Captures input events and transmits them to clients
- **Client**: Receives input events and simulates them locally

## Quick Start

### 1. Configuration

Copy the example configuration:
```bash
cp config.toml.example config.toml
```

Edit `config.toml` to match your network setup:
- Set the correct IP addresses for your computers
- Configure the topology (which computer is to the left/right/up/down)
- Adjust hotkeys if needed

### 2. Running the Server

On the computer where you want to capture input:
```bash
# Using the module interface
python -m inputflow server

# Or directly
python inputflow/server.py

# With verbose logging
python -m inputflow server --verbose

# With custom config file
python -m inputflow server --config /path/to/config.toml
```

### 3. Running the Client

On the computer where you want to simulate input:
```bash
# Using the module interface
python -m inputflow client

# Or directly
python inputflow/client.py

# With verbose logging
python -m inputflow client --verbose

# Override server IP from command line
python -m inputflow client --server 192.168.1.10

# With custom config file
python -m inputflow client --config /path/to/config.toml
```

## Default Hotkeys

- **Ctrl+T**: Toggle lock mode (disable/enable automatic screen switching)
- **Ctrl+`**: Manually cycle between screens

## Configuration Example

```toml
[network]
role = "server"
bind_ip = "0.0.0.0"
port = 9999

[[topology]]
self_ip = "192.168.1.10"
right = "192.168.1.11"

[[topology]]
self_ip = "192.168.1.11"
left = "192.168.1.10"

[shortcuts]
switch_lock = "ctrl+t"
switch_loop_between_screens = "ctrl+grave"
```

## Troubleshooting

### Permission Issues (Linux)

If you encounter permission errors on Linux:
```bash
# Add user to input group
sudo usermod -a -G input $USER

# For Wayland/Hyprland, ensure uinput access
sudo chmod 666 /dev/uinput

# Log out and log back in
```

### Connection Issues

1. Check firewall settings - ensure port 9999 (or your configured port) is open
2. Verify IP addresses in configuration are correct
3. Ensure both computers are on the same network
4. Check logs with `--verbose` flag for detailed error information

### Input Not Working

1. Verify the correct platform libraries are installed:
   - Windows/macOS: `pynput` should work automatically
   - Linux: May need `evdev` and `uinput` packages
2. Check permissions (especially on Linux)
3. Verify screen dimensions are detected correctly in logs

## Platform-Specific Notes

### Windows
- Uses `pynput` for both capture and simulation
- No special permissions required

### macOS
- Uses `pynput` for both capture and simulation
- May require accessibility permissions for input capture

### Linux (X11)
- Uses `evdev` for capture, `pynput` for simulation
- Requires read access to `/dev/input`

### Linux (Wayland/Hyprland)
- Uses `evdev` for capture, `uinput` for simulation
- Requires read access to `/dev/input` and write access to `/dev/uinput`