"""Pynput-based input simulation for Windows and macOS."""

from typing import Dict, Optional

try:
    from pynput.mouse import Button as PynputMouseButton, Listener as MouseListener
    from pynput.keyboard import Key as PynputKey, Listener as KeyboardListener
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

from inputflow.input.base import InputSimulation
from inputflow.core.events import InputEvent, EventType, MouseButton, MouseMoveEvent, MouseClickEvent, MouseScrollEvent, KeyboardEvent
from inputflow.core.throttling import EventThrottler, ThrottleConfig
from inputflow.core.logging import get_logger
from inputflow.core.exceptions import PlatformError

logger = get_logger(__name__)


class PynputInputSimulation(InputSimulation):
    """Input simulation using pynput library for Windows and macOS."""
    
    def __init__(self, throttle_config: Optional[ThrottleConfig] = None):
        if not PYNPUT_AVAILABLE:
            raise PlatformError("pynput library is not available")
        
        self._mouse_controller = mouse.Controller()
        self._keyboard_controller = keyboard.Controller()
        
        # Initialize throttling system
        self._throttler = EventThrottler(throttle_config)
        
        # Mouse button mapping
        self._button_map: Dict[MouseButton, PynputMouseButton] = {
            MouseButton.LEFT: PynputMouseButton.left,
            MouseButton.RIGHT: PynputMouseButton.right,
            MouseButton.MIDDLE: PynputMouseButton.middle,
            # Note: X1 and X2 buttons may not be supported by pynput
        }
        
        logger.info("Pynput input simulation initialized with throttling")
    
    def simulate_event(self, event: InputEvent) -> bool:
        """
        Simulate an input event with throttling applied.
        
        Args:
            event: The input event to simulate
            
        Returns:
            bool: True if event was processed, False if throttled
        """
        # Apply throttling
        if not self._throttler.should_process_event(event):
            return False
        
        try:
            if event.event_type == EventType.MOUSE_MOVE:
                data: MouseMoveEvent = event.data
                # Note: This method expects absolute coordinates, not normalized
                # The caller should denormalize coordinates before calling this
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
        try:
            self._mouse_controller.position = (x, y)
            logger.debug(f"Mouse moved to ({x}, {y})")
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
            
            # Get pynput button
            pynput_button = self._button_map.get(mouse_button)
            if pynput_button is None:
                logger.warning(f"Mouse button {mouse_button} not supported by pynput")
                return
            
            # Perform click action
            if pressed:
                self._mouse_controller.press(pynput_button)
                logger.debug(f"Mouse button {button} pressed at ({x}, {y})")
            else:
                self._mouse_controller.release(pynput_button)
                logger.debug(f"Mouse button {button} released at ({x}, {y})")
                
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
        try:
            self._mouse_controller.scroll(dx, dy)
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
        try:
            # Convert key code to pynput key
            # This is a simplified mapping - in practice, you'd need a more comprehensive mapping
            key = self._convert_key_code(key_code)
            
            if key is None:
                logger.warning(f"Key code {key_code} not supported")
                return
            
            if pressed:
                self._keyboard_controller.press(key)
                logger.debug(f"Key {key_code} pressed")
            else:
                self._keyboard_controller.release(key)
                logger.debug(f"Key {key_code} released")
                
        except Exception as e:
            logger.error(f"Failed to simulate key {key_code}: {e}")
            raise
    
    def _convert_key_code(self, key_code: int):
        """
        Convert a key code to a pynput key.
        
        This is a simplified implementation. In practice, you'd need a comprehensive
        mapping between platform-specific key codes and pynput keys.
        
        Args:
            key_code: Platform-specific key code
            
        Returns:
            Pynput key object or None if not supported
        """
        # Basic ASCII characters
        if 32 <= key_code <= 126:  # Printable ASCII
            return chr(key_code)
        
        # Common special keys (this is platform-dependent and simplified)
        special_keys = {
            8: PynputKey.backspace,
            9: PynputKey.tab,
            13: PynputKey.enter,
            27: PynputKey.esc,
            32: PynputKey.space,
            37: PynputKey.left,
            38: PynputKey.up,
            39: PynputKey.right,
            40: PynputKey.down,
            46: PynputKey.delete,
        }
        
        return special_keys.get(key_code)
    
    def get_throttling_stats(self) -> dict:
        """Get throttling statistics."""
        return self._throttler.get_stats()
    
    def reset_throttling(self) -> None:
        """Reset throttling state."""
        self._throttler.reset()