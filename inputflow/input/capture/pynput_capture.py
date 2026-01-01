"""Pynput-based input capture implementation for Windows and macOS."""

from typing import Optional

try:
    from pynput import mouse, keyboard
    from pynput.mouse import Button as PynputMouseButton
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

from inputflow.core.events import InputEvent, MouseButton
from inputflow.core.exceptions import InputCaptureError, PlatformError
from inputflow.core.logging import get_logger
from inputflow.core.coordinates import CoordinateTransformer
from inputflow.input.base import InputCapture

logger = get_logger(__name__)


class PynputInputCapture(InputCapture):
    """Input capture implementation using pynput library."""
    
    def __init__(self):
        super().__init__()
        
        if not PYNPUT_AVAILABLE:
            raise PlatformError("pynput library is not available")
        
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._coordinate_transformer = CoordinateTransformer()
        
        # Get screen dimensions for coordinate normalization
        self._screen_width, self._screen_height = self._coordinate_transformer.get_screen_dimensions()
        
        logger.info(f"PynputInputCapture initialized with screen dimensions: {self._screen_width}x{self._screen_height}")
    
    def start_monitoring(self) -> None:
        """Start monitoring for input events using pynput."""
        if self._is_monitoring:
            logger.warning("Input capture is already monitoring")
            return
        
        try:
            # Start mouse listener
            self._mouse_listener = mouse.Listener(
                on_move=self._on_mouse_move,
                on_click=self._on_mouse_click,
                on_scroll=self._on_mouse_scroll
            )
            self._mouse_listener.start()
            
            # Start keyboard listener
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self._keyboard_listener.start()
            
            self._is_monitoring = True
            logger.info("Started pynput input monitoring")
            
        except Exception as e:
            self._cleanup_listeners()
            raise InputCaptureError(f"Failed to start input monitoring: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring for input events."""
        if not self._is_monitoring:
            return
        
        self._cleanup_listeners()
        self._is_monitoring = False
        logger.info("Stopped pynput input monitoring")
    
    def _cleanup_listeners(self) -> None:
        """Clean up active listeners."""
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
    
    def _on_mouse_move(self, x: int, y: int) -> None:
        """Handle mouse movement events."""
        try:
            # Normalize coordinates
            norm_x, norm_y = self._coordinate_transformer.normalize_coordinates(
                x, y, self._screen_width, self._screen_height
            )
            
            # Create and emit event
            event = InputEvent.mouse_move(norm_x, norm_y)
            self._emit_event(event)
            
        except Exception as e:
            logger.error(f"Error processing mouse move event: {e}")
    
    def _on_mouse_click(self, x: int, y: int, button: PynputMouseButton, pressed: bool) -> None:
        """Handle mouse click events."""
        try:
            # Convert pynput button to our button enum
            mouse_button = self._convert_mouse_button(button)
            if mouse_button is None:
                return  # Unsupported button
            
            # Normalize coordinates
            norm_x, norm_y = self._coordinate_transformer.normalize_coordinates(
                x, y, self._screen_width, self._screen_height
            )
            
            # Create and emit event
            event = InputEvent.mouse_click(mouse_button, pressed, norm_x, norm_y)
            self._emit_event(event)
            
        except Exception as e:
            logger.error(f"Error processing mouse click event: {e}")
    
    def _on_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Handle mouse scroll events."""
        try:
            # Create and emit event
            event = InputEvent.mouse_scroll(dx, dy)
            self._emit_event(event)
            
        except Exception as e:
            logger.error(f"Error processing mouse scroll event: {e}")
    
    def _on_key_press(self, key) -> None:
        """Handle key press events."""
        self._handle_key_event(key, pressed=True)
    
    def _on_key_release(self, key) -> None:
        """Handle key release events."""
        self._handle_key_event(key, pressed=False)
    
    def _handle_key_event(self, key, pressed: bool) -> None:
        """Handle keyboard events."""
        try:
            # Convert key to key code
            key_code = self._convert_key_to_code(key)
            if key_code is None:
                return  # Unsupported key
            
            # Create and emit event
            event = InputEvent.keyboard(key_code, pressed)
            self._emit_event(event)
            
        except Exception as e:
            logger.error(f"Error processing keyboard event: {e}")
    
    def _convert_mouse_button(self, button: PynputMouseButton) -> Optional[MouseButton]:
        """Convert pynput mouse button to our MouseButton enum."""
        button_mapping = {
            PynputMouseButton.left: MouseButton.LEFT,
            PynputMouseButton.right: MouseButton.RIGHT,
            PynputMouseButton.middle: MouseButton.MIDDLE,
        }
        
        # Handle additional buttons if available
        if hasattr(PynputMouseButton, 'x1'):
            button_mapping[PynputMouseButton.x1] = MouseButton.X1
        if hasattr(PynputMouseButton, 'x2'):
            button_mapping[PynputMouseButton.x2] = MouseButton.X2
        
        return button_mapping.get(button)
    
    def _convert_key_to_code(self, key) -> Optional[int]:
        """Convert pynput key to integer key code."""
        try:
            # Handle special keys
            if hasattr(key, 'vk') and key.vk is not None:
                return key.vk
            
            # Handle character keys
            if hasattr(key, 'char') and key.char is not None:
                return ord(key.char.upper())
            
            # Handle named keys
            if hasattr(key, 'name'):
                # Map common special keys to virtual key codes
                special_keys = {
                    'space': 32,
                    'enter': 13,
                    'tab': 9,
                    'backspace': 8,
                    'delete': 46,
                    'escape': 27,
                    'shift': 16,
                    'ctrl': 17,
                    'alt': 18,
                    'cmd': 91,  # Windows key / Cmd key
                    'up': 38,
                    'down': 40,
                    'left': 37,
                    'right': 39,
                    'home': 36,
                    'end': 35,
                    'page_up': 33,
                    'page_down': 34,
                }
                
                key_name = key.name.lower()
                if key_name in special_keys:
                    return special_keys[key_name]
                
                # Handle function keys
                if key_name.startswith('f') and key_name[1:].isdigit():
                    f_num = int(key_name[1:])
                    if 1 <= f_num <= 24:
                        return 111 + f_num  # F1 = 112, F2 = 113, etc.
            
            # If we can't convert, log and return None
            logger.debug(f"Could not convert key to code: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Error converting key to code: {e}")
            return None