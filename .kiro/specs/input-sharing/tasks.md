# Implementation Plan: InputFlow Cross-Platform Input Sharing

## Overview

This implementation plan breaks down the InputFlow system into discrete, manageable coding tasks. Each task builds incrementally on previous work, ensuring that core functionality is validated early through testing. The implementation follows a modular approach, starting with foundational components and progressing to integration and advanced features.

## Tasks

- [x] 1. Set up project structure and core data models
  - Create Python package structure with proper __init__.py files
  - Define core data classes for events, configuration, and network messages
  - Set up logging configuration using loguru
  - Create base exception classes for error handling
  - _Requirements: 8.2_

- [ ]* 1.1 Write property test for coordinate normalization round-trip
  - **Property 1: Coordinate Normalization Round-Trip**
  - **Validates: Requirements 7.1, 7.2, 7.4, 7.5**

- [x] 2. Implement configuration management system
  - [x] 2.1 Create TOML configuration parser and validator
    - Implement ConfigManager class with TOML parsing
    - Add validation for network, topology, and hotkey configurations
    - Handle missing configuration files with defaults
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 2.2 Write property test for configuration validation
    - **Property 5: Configuration Validation Completeness**
    - **Validates: Requirements 6.2, 6.3, 6.4, 6.5**

  - [x] 2.3 Implement topology management
    - Create TopologyManager class for screen relationship handling
    - Implement edge detection logic for screen switching
    - Add support for directional relationships (Left/Right/Up/Down)
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 2.4 Write property test for edge detection accuracy
    - **Property 6: Edge Detection Accuracy**
    - **Validates: Requirements 3.3**

- [x] 3. Implement coordinate transformation system
  - [x] 3.1 Create CoordinateTransformer class
    - Implement coordinate normalization (pixels to 0.0-1.0 range)
    - Implement coordinate denormalization (0.0-1.0 to pixels)
    - Add screen dimension detection
    - Handle different screen resolutions and scaling factors
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 3.2 Write property test for coordinate normalization range
    - **Property 8: Coordinate Normalization Range**
    - **Validates: Requirements 1.4, 3.5**

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement platform detection and input abstraction
  - [x] 5.1 Create platform detection system
    - Implement automatic OS detection (Windows, macOS, Linux)
    - Add Wayland/Hyprland detection for Linux systems
    - Create factory pattern for platform-specific implementations
    - _Requirements: 2.4, 2.5_

  - [ ]* 5.2 Write property test for platform-specific library selection
    - **Property 4: Platform-Specific Library Selection**
    - **Validates: Requirements 2.4**

  - [x] 5.3 Implement input capture layer
    - Create InputCapture base class and platform-specific implementations
    - Implement pynput-based capture for Windows/macOS
    - Implement evdev-based capture for Linux
    - Add permission checking for Linux /dev/input access
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.5_

  - [ ]* 5.4 Write property test for input event capture completeness
    - **Property 2: Input Event Capture Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 6. Implement input simulation layer
  - [x] 6.1 Create input simulation system
    - Create InputSimulation base class and platform-specific implementations
    - Implement pynput-based simulation for Windows/macOS
    - Implement uinput-based simulation for Linux
    - Add permission checking for Linux /dev/uinput access
    - _Requirements: 1.2, 2.1, 2.2, 2.3, 2.5_

  - [x] 6.2 Add event throttling for performance optimization
    - Implement microsecond-level throttling for high-frequency mouse events
    - Add configurable throttling parameters
    - Maintain movement accuracy while reducing transmission rate
    - _Requirements: 4.5_

  - [ ]* 6.3 Write property test for throttling effectiveness
    - **Property 9: Throttling Effectiveness**
    - **Validates: Requirements 4.5**

- [x] 7. Implement network communication layer
  - [x] 7.1 Create UDP network server and client
    - Implement NetworkServer class with UDP socket binding
    - Implement NetworkClient class with UDP socket connection
    - Add binary packet serialization for efficiency
    - Handle configurable IP binding and port settings
    - _Requirements: 1.3, 1.5_

  - [x] 7.2 Implement event serialization and transmission
    - Create binary packet format for input events
    - Implement event serialization and deserialization
    - Add timestamp handling for event ordering
    - Ensure normalized coordinate transmission
    - _Requirements: 1.2, 1.4_

  - [ ]* 7.3 Write property test for network event transmission integrity
    - **Property 3: Network Event Transmission Integrity**
    - **Validates: Requirements 1.2, 4.1, 4.2, 4.3, 4.4**

- [x] 8. Implement hotkey control system
  - [x] 8.1 Create hotkey controller
    - Implement HotkeyController class with global hotkey registration
    - Add lock mode toggle functionality (Ctrl+T default)
    - Add screen cycling functionality (Ctrl+` default)
    - Handle configurable hotkey combinations from TOML
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 8.2 Write property test for hotkey state management
    - **Property 7: Hotkey State Management**
    - **Validates: Requirements 5.1, 5.2**

  - [x] 8.3 Implement lock mode behavior
    - Add lock mode state management
    - Prevent automatic screen transitions when locked
    - Maintain lock state across system operations
    - _Requirements: 5.5_

  - [ ]* 8.4 Write property test for lock mode prevention
    - **Property 10: Lock Mode Prevention**
    - **Validates: Requirements 5.5**

- [x] 9. Create main application entry points
  - [x] 9.1 Implement server application
    - Create main server entry point with configuration loading
    - Integrate input capture, coordinate transformation, and network transmission
    - Add topology-based screen switching logic
    - Implement cursor locking during screen transitions
    - _Requirements: 1.1, 3.4, 8.1, 8.3_

  - [x] 9.2 Implement client application
    - Create main client entry point with configuration loading
    - Integrate network reception, coordinate transformation, and input simulation
    - Add proper event handling and error recovery
    - _Requirements: 1.2, 8.1, 8.3_

  - [ ]* 9.3 Write integration tests for server-client communication
    - Test end-to-end input sharing functionality
    - Verify proper event transmission and simulation
    - Test error handling and recovery scenarios
    - _Requirements: 1.1, 1.2_

- [x] 10. Add command-line interface and logging
  - [x] 10.1 Create CLI interface
    - Implement command-line argument parsing
    - Add configuration file path specification
    - Add verbose logging options
    - Ensure no graphical components are created
    - _Requirements: 8.1_

  - [x] 10.2 Implement comprehensive logging
    - Add startup configuration status logging
    - Add network binding information display
    - Add input event processing logs
    - Add clear error messages with troubleshooting guidance
    - _Requirements: 8.3, 8.4, 8.5_

- [ ] 11. Final integration and testing
  - [ ] 11.1 Wire all components together
    - Integrate all system components into cohesive server and client applications
    - Add proper initialization and shutdown procedures
    - Implement graceful error handling and recovery
    - _Requirements: All requirements_

  - [ ]* 11.2 Write comprehensive integration tests
    - Test complete input sharing workflows
    - Test error conditions and recovery
    - Test performance under high-frequency input
    - _Requirements: All requirements_

- [ ] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using hypothesis library
- Unit tests validate specific examples and edge cases
- Checkpoints ensure incremental validation of system functionality
- Implementation uses Python with platform-specific libraries (pynput, evdev, uinput)
- All network communication uses UDP protocol for low-latency performance