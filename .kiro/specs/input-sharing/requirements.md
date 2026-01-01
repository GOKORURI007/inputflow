# Requirements Document

## Introduction

InputFlow is a lightweight, high-performance Python cross-platform keyboard and mouse sharing tool. It synchronizes physical keyboard and mouse operations across multiple computers through network communication, supporting seamless switching between Windows, macOS, and Linux (including Hyprland/Wayland) systems.

## Glossary

- **Server**: The computer that captures physical input from keyboard and mouse
- **Client**: The computer that receives and simulates input events
- **Topology**: The logical arrangement and relationship between connected screens/computers
- **Edge_Penetration**: The mechanism that triggers screen switching when mouse reaches screen boundaries
- **Normalized_Coordinates**: Floating-point coordinates (0.0-1.0) used for cross-resolution compatibility
- **Input_Capture**: The process of detecting physical keyboard and mouse events
- **Input_Simulation**: The process of reproducing keyboard and mouse events on target systems
- **UDP_Protocol**: User Datagram Protocol used for low-latency network communication
- **TOML_Config**: Configuration file format used for system settings

## Requirements

### Requirement 1: Network Communication Architecture

**User Story:** As a system architect, I want a UDP-based client-server architecture, so that input events can be transmitted with minimal latency across the network.

#### Acceptance Criteria

1. THE Server SHALL capture physical input events from keyboard and mouse
2. THE Client SHALL receive network packets and simulate corresponding input events
3. WHEN network communication is established, THE System SHALL use UDP protocol for data transmission
4. THE System SHALL transmit normalized coordinates to handle different screen resolutions
5. THE System SHALL bind to configurable IP address and port from TOML configuration

### Requirement 2: Cross-Platform Input Handling

**User Story:** As a user, I want the system to work across Windows, macOS, and Linux platforms, so that I can share input between different operating systems.

#### Acceptance Criteria

1. WHEN running on Windows, THE System SHALL use pynput for both input capture and simulation
2. WHEN running on macOS, THE System SHALL use pynput for both input capture and simulation  
3. WHEN running on Linux with Wayland, THE System SHALL use evdev for input capture and pynput (with uinput backend) for input simulation
4. THE System SHALL automatically detect the operating system and select appropriate input methods
5. WHEN running on Linux, THE System SHALL check permissions for /dev/input and /dev/uinput access

### Requirement 3: Desktop Topology Management

**User Story:** As a user, I want to define the logical arrangement of my screens, so that mouse movement can seamlessly transition between connected computers.

#### Acceptance Criteria

1. THE System SHALL read topology configuration from TOML file defining screen relationships
2. THE System SHALL support directional relationships (Left/Right/Up/Down) between screens
3. WHEN mouse reaches a configured screen edge, THE System SHALL trigger screen switching
4. THE System SHALL lock local cursor and activate remote mode during screen transitions
5. THE System SHALL convert absolute pixel coordinates to normalized floating-point coordinates (0.0-1.0)

### Requirement 4: Real-time Input Synchronization

**User Story:** As a user, I want keyboard and mouse actions to be synchronized in real-time, so that I can work seamlessly across multiple computers.

#### Acceptance Criteria

1. THE System SHALL capture and transmit mouse movement events in real-time
2. THE System SHALL capture and transmit mouse click events (left, right, middle, and others buttons)
3. THE System SHALL capture and transmit mouse scroll wheel events
4. THE System SHALL capture and transmit keyboard key press and release events
5. WHEN high-frequency mouse movement occurs, THE System SHALL apply simple throttling to optimize performance

### Requirement 5: Hotkey Control System

**User Story:** As a user, I want global hotkeys to control the input sharing behavior, so that I can prevent accidental screen switching and manually control transitions.

#### Acceptance Criteria

1. WHEN the configured lock hotkey is pressed, THE System SHALL toggle automatic edge switching on/off
2. WHEN the configured loop hotkey is pressed, THE System SHALL cycle control between all connected clients
3. THE System SHALL read hotkey configurations from TOML file
4. THE System SHALL provide default hotkeys (Ctrl+T for lock toggle, Ctrl+` for loop switching)

### Requirement 6: Configuration File Management

**User Story:** As a user, I want a simple configuration file to define network settings and topology, so that the system can start without manual intervention.

#### Acceptance Criteria

1. THE System SHALL read configuration from config.toml file in the same directory
2. 一切从简，作为一个函数读取toml即可

### Requirement 7: Coordinate Transformation System

**User Story:** As a developer, I want coordinate normalization between different screen resolutions, so that mouse positioning works correctly across heterogeneous display setups.

#### Acceptance Criteria

1. WHEN capturing mouse coordinates, THE System SHALL convert absolute pixels to normalized coordinates (0.0-1.0)
2. WHEN simulating mouse movement, THE System SHALL convert normalized coordinates back to target screen pixels
3. THE Coordinate_Transformer SHALL handle different screen resolutions and scaling factors
4. THE System SHALL maintain accurate cursor positioning across resolution differences
5. THE System SHALL preserve relative mouse movement precision during coordinate conversion
6. 一切从简，作为一个函数实现即可

### Requirement 8: Command-Line Interface

**User Story:** As a user, I want a simple command-line interface with logging, so that I can monitor system status and troubleshoot issues.

#### Acceptance Criteria

1. THE System SHALL provide command-line interface without graphical components
2. THE System SHALL output operational logs using loguru library
3. WHEN system starts, THE System SHALL display configuration status and network binding information
4. WHEN input events are processed, THE System SHALL log relevant debugging information
5. WHEN errors occur, THE System SHALL display error messages
6. 一切从简，不需要定义任何exception，尽量检索try-catch使用