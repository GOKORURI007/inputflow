"""Platform detection and factory system for InputFlow."""

import os
import platform
from enum import Enum
from typing import Optional, TYPE_CHECKING

from inputflow.core.exceptions import PlatformError
from inputflow.core.logging import get_logger

if TYPE_CHECKING:
    from .base import InputCapture, InputSimulation

logger = get_logger(__name__)


class Platform(Enum):
    """Supported platforms."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX_X11 = "linux_x11"
    LINUX_WAYLAND = "linux_wayland"


class PlatformDetector:
    """Detects the current platform and display server."""
    
    @staticmethod
    def detect_platform() -> Platform:
        """
        Detect the current platform and display server.
        
        Returns:
            Platform: The detected platform
            
        Raises:
            PlatformError: If platform detection fails or platform is unsupported
        """
        system = platform.system().lower()
        
        if system == "windows":
            logger.info("Detected platform: Windows")
            return Platform.WINDOWS
        elif system == "darwin":
            logger.info("Detected platform: macOS")
            return Platform.MACOS
        elif system == "linux":
            return PlatformDetector._detect_linux_display_server()
        else:
            raise PlatformError(f"Unsupported platform: {system}")
    
    @staticmethod
    def _detect_linux_display_server() -> Platform:
        """
        Detect the display server on Linux systems.
        
        Returns:
            Platform: Either LINUX_X11 or LINUX_WAYLAND
            
        Raises:
            PlatformError: If display server detection fails
        """
        # Check for Wayland session
        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        xdg_session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        
        # Check for Hyprland specifically
        hyprland_instance = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        
        if wayland_display or xdg_session_type == "wayland" or hyprland_instance:
            if hyprland_instance:
                logger.info("Detected platform: Linux with Hyprland (Wayland)")
            else:
                logger.info("Detected platform: Linux with Wayland")
            return Platform.LINUX_WAYLAND
        
        # Check for X11 session
        display = os.environ.get("DISPLAY")
        if display or xdg_session_type == "x11":
            logger.info("Detected platform: Linux with X11")
            return Platform.LINUX_X11
        
        # Default to X11 if we can't determine
        logger.warning("Could not determine Linux display server, defaulting to X11")
        return Platform.LINUX_X11
    
    @staticmethod
    def is_wayland() -> bool:
        """Check if running on Wayland."""
        try:
            platform_type = PlatformDetector.detect_platform()
            return platform_type == Platform.LINUX_WAYLAND
        except PlatformError:
            return False
    
    @staticmethod
    def is_hyprland() -> bool:
        """Check if running on Hyprland."""
        return os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") is not None


class PlatformFactory:
    """Factory for creating platform-specific implementations."""
    
    def __init__(self):
        self._platform = PlatformDetector.detect_platform()
        logger.info(f"Platform factory initialized for: {self._platform.value}")
    
    @property
    def platform(self) -> Platform:
        """Get the detected platform."""
        return self._platform
    
    def create_input_capture(self) -> "InputCapture":
        """
        Create platform-specific input capture implementation.
        
        Returns:
            InputCapture: Platform-specific input capture instance
            
        Raises:
            PlatformError: If platform is not supported
        """
        if self._platform == Platform.WINDOWS:
            from .capture.pynput_capture import PynputInputCapture
            return PynputInputCapture()
        elif self._platform == Platform.MACOS:
            from .capture.pynput_capture import PynputInputCapture
            return PynputInputCapture()
        elif self._platform == Platform.LINUX_WAYLAND:
            from .capture.evdev_capture import EvdevInputCapture
            return EvdevInputCapture()
        elif self._platform == Platform.LINUX_X11:
            # For X11, we can use either pynput or evdev
            # Let's prefer evdev for consistency on Linux
            from .capture.evdev_capture import EvdevInputCapture
            return EvdevInputCapture()
        else:
            raise PlatformError(f"No input capture implementation for platform: {self._platform}")
    
    def create_input_simulation(self, throttle_config=None) -> "InputSimulation":
        """
        Create platform-specific input simulation implementation.
        
        Args:
            throttle_config: Optional throttling configuration
        
        Returns:
            InputSimulation: Platform-specific input simulation instance
            
        Raises:
            PlatformError: If platform is not supported
        """
        if self._platform == Platform.WINDOWS:
            from .simulation.pynput_simulation import PynputInputSimulation
            return PynputInputSimulation(throttle_config)
        elif self._platform == Platform.MACOS:
            from .simulation.pynput_simulation import PynputInputSimulation
            return PynputInputSimulation(throttle_config)
        elif self._platform == Platform.LINUX_WAYLAND:
            from .simulation.uinput_simulation import UinputInputSimulation
            return UinputInputSimulation(throttle_config)
        elif self._platform == Platform.LINUX_X11:
            # For X11, we can use pynput
            from .simulation.pynput_simulation import PynputInputSimulation
            return PynputInputSimulation(throttle_config)
        else:
            raise PlatformError(f"No input simulation implementation for platform: {self._platform}")
    
    def check_permissions(self) -> bool:
        """
        Check if the current user has necessary permissions for input operations.
        
        Returns:
            bool: True if permissions are sufficient, False otherwise
        """
        if self._platform in [Platform.LINUX_WAYLAND, Platform.LINUX_X11]:
            return self._check_linux_permissions()
        
        # Windows and macOS don't require special permissions for pynput
        return True
    
    def _check_linux_permissions(self) -> bool:
        """
        Check Linux-specific permissions for input devices.
        
        Returns:
            bool: True if permissions are sufficient
        """
        # Check /dev/input access for input capture
        input_accessible = os.access("/dev/input", os.R_OK)
        if not input_accessible:
            logger.error("No read access to /dev/input - input capture may fail")
        
        # Check /dev/uinput access for input simulation (Wayland)
        if self._platform == Platform.LINUX_WAYLAND:
            uinput_accessible = os.access("/dev/uinput", os.W_OK)
            if not uinput_accessible:
                logger.error("No write access to /dev/uinput - input simulation may fail")
            return input_accessible and uinput_accessible
        
        return input_accessible
    
    def get_permission_instructions(self) -> Optional[str]:
        """
        Get instructions for fixing permission issues.
        
        Returns:
            Optional[str]: Instructions for fixing permissions, or None if no issues
        """
        if not self.check_permissions():
            if self._platform in [Platform.LINUX_WAYLAND, Platform.LINUX_X11]:
                return (
                    "Linux permission issues detected. To fix:\n"
                    "1. Add your user to the 'input' group: sudo usermod -a -G input $USER\n"
                    "2. For Wayland/Hyprland, ensure /dev/uinput access: sudo chmod 666 /dev/uinput\n"
                    "3. Log out and log back in for group changes to take effect"
                )
        return None