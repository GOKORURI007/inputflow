"""Uinput-based input simulation for Linux systems."""

import os
from typing import Dict, Optional

try:
    import uinput
    UINPUT_AVAILABLE = True
except ImportError:
    UINPUT_AVAILABLE = False

from inputflow.input.base import InputSimulation
from inputflow.core.events import InputEvent, EventType, MouseButton, MouseMoveEvent, MouseClickEvent, MouseScrollEvent, KeyboardEvent
from inputflow.core.throttling import EventThrottler, ThrottleConfig
from inputflow.core.logging import get_logger
from inputflow.core.exceptions import PlatformError

logger = get_logger(__name__)


class UinputInputSimulation(InputSimulation):
    """Input simulation using uinput for Linux systems."""
    
    def __init__(self, throttle_config: Optional[ThrottleConfig] = None):
        if not UINPUT_AVAILABLE:
            raise PlatformError("uinput library is not available")
        
        # Check permissions
        if not os.access("/dev/uinput", os.W_OK):
            raise PlatformError(
                "No write access to /dev/uinput. "
                "Run: sudo chmod 666 /dev/uinput or add user to input group"
            )
        
        self._device: Optional[uinput.Device] = None
        self._initialize_device()
        
        # Initialize throttling system
        self._throttler = EventThrottler(throttle_config)
        
        # Mouse button mapping
        self._button_map: Dict[MouseButton, int] = {
            MouseButton.LEFT: uinput.BTN_LEFT,
            MouseButton.RIGHT: uinput.BTN_RIGHT,
            MouseButton.MIDDLE: uinput.BTN_MIDDLE,
            MouseButton.X1: uinput.BTN_SIDE,
            MouseButton.X2: uinput.BTN_EXTRA,
        }
        
        logger.info("Uinput input simulation initialized with throttling")
    
    def _initialize_device(self) -> None:
        """Initialize the uinput virtual device."""
        try:
            # Define the capabilities of our virtual device
            events = (
                # Mouse events
                uinput.REL_X, uinput.REL_Y,  # Relative mouse movement
                uinput.ABS_X, uinput.ABS_Y,  # Absolute mouse movement
                uinput.BTN_LEFT, uinput.BTN_RIGHT, uinput.BTN_MIDDLE,  # Mouse buttons
                uinput.BTN_SIDE, uinput.BTN_EXTRA,  # Extra mouse buttons
                uinput.REL_WHEEL, uinput.REL_HWHEEL,  # Mouse wheel
                
                # Keyboard events - basic keys
                uinput.KEY_A, uinput.KEY_B, uinput.KEY_C, uinput.KEY_D, uinput.KEY_E,
                uinput.KEY_F, uinput.KEY_G, uinput.KEY_H, uinput.KEY_I, uinput.KEY_J,
                uinput.KEY_K, uinput.KEY_L, uinput.KEY_M, uinput.KEY_N, uinput.KEY_O,
                uinput.KEY_P, uinput.KEY_Q, uinput.KEY_R, uinput.KEY_S, uinput.KEY_T,
                uinput.KEY_U, uinput.KEY_V, uinput.KEY_W, uinput.KEY_X, uinput.KEY_Y,
                uinput.KEY_Z,
                
                # Numbers
                uinput.KEY_0, uinput.KEY_1, uinput.KEY_2, uinput.KEY_3, uinput.KEY_4,
                uinput.KEY_5, uinput.KEY_6, uinput.KEY_7, uinput.KEY_8, uinput.KEY_9,
                
                # Special keys
                uinput.KEY_SPACE, uinput.KEY_ENTER, uinput.KEY_BACKSPACE,
                uinput.KEY_TAB, uinput.KEY_ESC, uinput.KEY_DELETE,
                uinput.KEY_LEFT, uinput.KEY_RIGHT, uinput.KEY_UP, uinput.KEY_DOWN,
                
                # Modifier keys
                uinput.KEY_LEFTCTRL, uinput.KEY_RIGHTCTRL,
                uinput.KEY_LEFTSHIFT, uinput.KEY_RIGHTSHIFT,
                uinput.KEY_LEFTALT, uinput.KEY_RIGHTALT,
                uinput.KEY_LEFTMETA, uinput.KEY_RIGHTMETA,
            )
            
            # Create the virtual device
            self._device = uinput.Device(events, name="InputFlow Virtual Device")
            logger.info("Uinput virtual device created successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize uinput device: {e}")
            raise PlatformError(f"Failed to initialize uinput device: {e}")
    
    def __del__(self):
        """Clean up the uinput device."""
        if self._device:
            try:
                self._device.destroy()
            except Exception as e:
                logger.error(f"Error destroying uinput device: {e}")
    
    def simulate_event(self, event: InputEvent) -> bool:
        """
        Simulate an input event with throttling applied.
        
        Args:
            event: The input event to simulate
            
        Returns:
            bool: True if event was processed, False if throttled
        """
        if not self._device:
            raise PlatformError("Uinput device not initialized")
        
        # Apply throttling
        if not self._throttler.should_process_event(event):
            return False
        
        try:
            if event.event_type == EventType.MOUSE_MOVE:
                data: MouseMoveEvent = event.data
                # Note: This method expects absolute coordinates, not normalized
                logger.warning("simulate_event called with normalized coordinates - use specific methods instead")
                
            elif event.event_type == EventType.MOUSE_CLICK:
                data: MouseClickEvent = event.data
                # Note: This method expects absolute coordinates, not normalized
                logger.warning("simulate_event called with normalized coordinates - use specific methods instead")
                
            elif event.event_type == EventType.MOUSE_SCROLL:
                data: MouseScrollEvent = event.data
                self.scroll_mouse(data.delta_x, data.delta_y)
                
            elif event.event_type == EventType.KEYBOARD:
                data: KeyboardEvent = event.data
                self.press_key(data.key_code, data.pressed)
            
            return True
                
        except Exception as e:
            logger.error(f"Failed to simulate event {event.event_type}: {e}")
            raise
    
    def move_mouse(self, x: int, y: int) -> None:
        """
        Move the mouse cursor to the specified position.
        
        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
        """
        if not self._device:
            raise PlatformError("Uinput device not initialized")
        
        try:
            # For absolute positioning, we need to use ABS events
            # Note: This requires proper setup of absolute axes with min/max values
            # For now, we'll use relative movement as a fallback
            
            # Get current mouse position (this is simplified - in practice you'd track position)
            # For now, we'll use relative movement
            current_x, current_y = self._get_current_mouse_position()
            
            rel_x = x - current_x
            rel_y = y - current_y
            
            if rel_x != 0:
                self._device.emit(uinput.REL_X, rel_x)
            if rel_y != 0:
                self._device.emit(uinput.REL_Y, rel_y)
            
            self._device.syn()
            logger.debug(f"Mouse moved to ({x}, {y}) via relative movement ({rel_x}, {rel_y})")
            
        except Exception as e:
            logger.error(f"Failed to move mouse to ({x}, {y}): {e}")
            raise
    
    def click_mouse(self, button: str, pressed: bool, x: int, y: int) -> None:
        """
        Simulate a mouse click.
        
        Args:
            button: Mouse button identifier (string representation of MouseButton)
            pressed: True for press, False for release
            x: X coordinate in pixels
            y: Y coordinate in pixels
        """
        if not self._device:
            raise PlatformError("Uinput device not initialized")
        
        try:
            # Convert string button to MouseButton enum
            if isinstance(button, str):
                try:
                    mouse_button = MouseButton(button)
                except ValueError:
                    logger.error(f"Unknown mouse button: {button}")
                    return
            else:
                mouse_button = button
            
            # Move to position first
            self.move_mouse(x, y)
            
            # Get uinput button code
            button_code = self._button_map.get(mouse_button)
            if button_code is None:
                logger.warning(f"Mouse button {mouse_button} not supported by uinput")
                return
            
            # Perform click action
            self._device.emit(button_code, 1 if pressed else 0)
            self._device.syn()
            
            action = "pressed" if pressed else "released"
            logger.debug(f"Mouse button {button} {action} at ({x}, {y})")
            
        except Exception as e:
            logger.error(f"Failed to simulate mouse click {button} at ({x}, {y}): {e}")
            raise
    
    def scroll_mouse(self, dx: int, dy: int) -> None:
        """
        Simulate mouse scroll.
        
        Args:
            dx: Horizontal scroll delta
            dy: Vertical scroll delta
        """
        if not self._device:
            raise PlatformError("Uinput device not initialized")
        
        try:
            if dy != 0:
                self._device.emit(uinput.REL_WHEEL, dy)
            if dx != 0:
                self._device.emit(uinput.REL_HWHEEL, dx)
            
            self._device.syn()
            logger.debug(f"Mouse scrolled by ({dx}, {dy})")
            
        except Exception as e:
            logger.error(f"Failed to simulate mouse scroll ({dx}, {dy}): {e}")
            raise
    
    def press_key(self, key_code: int, pressed: bool) -> None:
        """
        Simulate a key press or release.
        
        Args:
            key_code: Key code to simulate
            pressed: True for press, False for release
        """
        if not self._device:
            raise PlatformError("Uinput device not initialized")
        
        try:
            # Convert key code to uinput key
            uinput_key = self._convert_key_code(key_code)
            
            if uinput_key is None:
                logger.warning(f"Key code {key_code} not supported")
                return
            
            self._device.emit(uinput_key, 1 if pressed else 0)
            self._device.syn()
            
            action = "pressed" if pressed else "released"
            logger.debug(f"Key {key_code} {action}")
            
        except Exception as e:
            logger.error(f"Failed to simulate key {key_code}: {e}")
            raise
    
    def _get_current_mouse_position(self) -> tuple[int, int]:
        """
        Get the current mouse position.
        
        This is a simplified implementation. In practice, you'd need to track
        the mouse position or query it from the system.
        
        Returns:
            Tuple of (x, y) coordinates
        """
        # For now, return a default position
        # In a real implementation, you'd track the position or query the system
        return (0, 0)
    
    def _convert_key_code(self, key_code: int) -> Optional[int]:
        """
        Convert a key code to a uinput key constant.
        
        This is a simplified implementation. In practice, you'd need a comprehensive
        mapping between platform-specific key codes and uinput key constants.
        
        Args:
            key_code: Platform-specific key code
            
        Returns:
            Uinput key constant or None if not supported
        """
        # Basic ASCII characters (A-Z)
        if 65 <= key_code <= 90:  # A-Z
            return getattr(uinput, f"KEY_{chr(key_code)}")
        
        # Numbers (0-9)
        if 48 <= key_code <= 57:  # 0-9
            return getattr(uinput, f"KEY_{chr(key_code)}")
        
        # Common special keys (this is platform-dependent and simplified)
        special_keys = {
            8: uinput.KEY_BACKSPACE,
            9: uinput.KEY_TAB,
            13: uinput.KEY_ENTER,
            27: uinput.KEY_ESC,
            32: uinput.KEY_SPACE,
            37: uinput.KEY_LEFT,
            38: uinput.KEY_UP,
            39: uinput.KEY_RIGHT,
            40: uinput.KEY_DOWN,
            46: uinput.KEY_DELETE,
        }
        
        return special_keys.get(key_code)
    
    def get_throttling_stats(self) -> dict:
        """Get throttling statistics."""
        return self._throttler.get_stats()
    
    def reset_throttling(self) -> None:
        """Reset throttling state."""
        self._throttler.reset()