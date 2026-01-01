"""
InputFlow - Cross-platform keyboard and mouse sharing tool.

A lightweight, high-performance Python application that enables seamless
keyboard and mouse sharing across multiple computers through network communication.
"""

__version__ = "0.1.0"
__author__ = "InputFlow Team"

# Configuration exports
from inputflow.config.models import (Config, HotkeyConfig, NetworkConfig, TopologyEntry)
# Core exports
from inputflow.core.events import (EventType, InputEvent, KeyboardEvent, MouseButton,
                                   MouseClickEvent, MouseMoveEvent, MouseScrollEvent)
from inputflow.core.exceptions import (ConfigurationError, CoordinateTransformError,
                                       HotkeyError, InputCaptureError, InputFlowError,
                                       InputSimulationError, NetworkError,
                                       PermissionError, PlatformError, TopologyError)
from inputflow.core.logging import get_logger, setup_logging
# Input exports
from inputflow.input import (InputCapture, InputSimulation, Platform, PlatformDetector,
                             PlatformFactory)
# Network exports
from inputflow.network.messages import (MessageType, NetworkMessage,
                                        NetworkMessageFactory)

__all__ = [
    # Core
    "InputEvent", "EventType", "MouseButton",
    "MouseMoveEvent", "MouseClickEvent", "MouseScrollEvent", "KeyboardEvent",
    "InputFlowError", "ConfigurationError", "NetworkError",
    "InputCaptureError", "InputSimulationError", "PlatformError",
    "PermissionError", "TopologyError", "CoordinateTransformError", "HotkeyError",
    "setup_logging", "get_logger",
    # Configuration
    "Config", "NetworkConfig", "TopologyEntry", "HotkeyConfig",
    # Network
    "NetworkMessage", "MessageType", "NetworkMessageFactory",
    # Input
    "PlatformDetector", "PlatformFactory", "Platform",
    "InputCapture", "InputSimulation",
]