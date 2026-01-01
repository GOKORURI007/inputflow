"""Evdev-based input capture implementation for Linux."""

import os
import threading
from typing import List, Optional

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

from inputflow.core.events import InputEvent, MouseButton
from inputflow.core.exceptions import InputCaptureError, PlatformError, PermissionError
from inputflow.core.logging import get_logger
from inputflow.core.coordinates import CoordinateTransformer
from inputflow.input.base import InputCapture

logger = get_logger(__name__)


class EvdevInputCapture(InputCapture):
    """Input capture implementation using evdev library for Linux."""
    
    def __init__(self):
        super().__init__()
        
        if not EVDEV_AVAILABLE:
            raise PlatformError("evdev library is not available")
        
        self._devices: List[InputDevice] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._coordinate_transformer = CoordinateTransformer()
        
        # Get screen dimensions for coordinate normalization
        self._screen_width, self._screen_height = self._coordinate_transformer.get_screen_dimensions()
        
        # Mouse state tracking
        self._mouse_x = 0
        self._mouse_y = 0
        
        logger.info(f"EvdevInputCapture initialized with screen dimensions: {self._screen_width}x{self._screen_height}")
    
    def start_monitoring(self) -> None:
        """Start monitoring for input events using evdev."""
        if self._is_monitoring:
            logger.warning("Input capture is already monitoring")
            return
        
        try:
            self._discover_devices()
            
            if not self._devices:
                raise InputCaptureError("No input devices found")
            
            # Start monitoring thread
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_devices, daemon=True)
            self._monitor_thread.start()
            
            self._is_monitoring = True
            logger.info(f"Started evdev input monitoring on {len(self._devices)} devices")
            
        except PermissionError as e:
            raise e
        except Exception as e:
            self._cleanup_devices()
            raise InputCaptureError(f"Failed to start input monitoring: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring for input events."""
        if not self._is_monitoring:
            return
        
        # Signal stop and wait for thread
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        
        self._cleanup_devices()
        self._is_monitoring = False
        logger.info("Stopped evdev input monitoring")
    
    def _discover_devices(self) -> None:
        """Discover and open input devices."""
        if not os.access("/dev/input", os.R_OK):
            raise PermissionError(
                "No read access to /dev/input. "
                "Add your user to the 'input' group: sudo usermod -a -G input $USER"
            )
        
        try:
            device_paths = evdev.list_devices()
            
            for path in device_paths:
                try:
                    device = InputDevice(path)
                    
                    # Check if device has capabilities we're interested in
                    capabilities = device.capabilities()
                    
                    # Look for mouse/keyboard capabilities
                    has_mouse = (
                        ecodes.EV_REL in capabilities or  # Relative movement (mouse)
                        ecodes.EV_ABS in capabilities     # Absolute movement (touchpad/tablet)
                    )
                    has_keyboard = ecodes.EV_KEY in capabilities
                    
                    if has_mouse or has_keyboard:
                        self._devices.append(device)
                        logger.debug(f"Added input device: {device.name} ({path})")
                
                except (OSError, PermissionError) as e:
                    logger.debug(f"Could not access device {path}: {e}")
                    continue
        
        except Exception as e:
            raise InputCaptureError(f"Failed to discover input devices: {e}")
    
    def _cleanup_devices(self) -> None:
        """Clean up opened devices."""
        for device in self._devices:
            try:
                device.close()
            except Exception as e:
                logger.debug(f"Error closing device {device.path}: {e}")
        
        self._devices.clear()
    
    def _monitor_devices(self) -> None:
        """Monitor all devices for input events."""
        try:
            # Create a mapping of file descriptors to devices
            fd_to_device = {device.fd: device for device in self._devices}
            
            while not self._stop_event.is_set():
                try:
                    # Use select to wait for events with timeout
                    import select
                    ready_fds, _, _ = select.select(fd_to_device.keys(), [], [], 0.1)
                    
                    for fd in ready_fds:
                        device = fd_to_device[fd]
                        try:
                            events = device.read()
                            for event in events:
                                self._process_event(event, device)
                        except OSError:
                            # Device was disconnected
                            logger.debug(f"Device {device.path} disconnected")
                            continue
                
                except Exception as e:
                    if not self._stop_event.is_set():
                        logger.error(f"Error in device monitoring: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Fatal error in device monitoring thread: {e}")
    
    def _process_event(self, event, device: InputDevice) -> None:
        """Process a single evdev event."""
        try:
            # Only process input events
            if event.type == ecodes.EV_SYN:
                return  # Synchronization events, ignore
            
            if event.type == ecodes.EV_REL:
                self._handle_relative_event(event)
            elif event.type == ecodes.EV_ABS:
                self._handle_absolute_event(event)
            elif event.type == ecodes.EV_KEY:
                self._handle_key_event(event)
        
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    def _handle_relative_event(self, event) -> None:
        """Handle relative movement events (mouse)."""
        if event.code == ecodes.REL_X:
            self._mouse_x += event.value
            self._mouse_x = max(0, min(self._mouse_x, self._screen_width - 1))
        elif event.code == ecodes.REL_Y:
            self._mouse_y += event.value
            self._mouse_y = max(0, min(self._mouse_y, self._screen_height - 1))
        elif event.code == ecodes.REL_WHEEL:
            # Vertical scroll
            scroll_event = InputEvent.mouse_scroll(0, event.value)
            self._emit_event(scroll_event)
        elif event.code == ecodes.REL_HWHEEL:
            # Horizontal scroll
            scroll_event = InputEvent.mouse_scroll(event.value, 0)
            self._emit_event(scroll_event)
        
        # Emit mouse move event for X/Y changes
        if event.code in (ecodes.REL_X, ecodes.REL_Y):
            norm_x, norm_y = self._coordinate_transformer.normalize_coordinates(
                self._mouse_x, self._mouse_y, self._screen_width, self._screen_height
            )
            move_event = InputEvent.mouse_move(norm_x, norm_y)
            self._emit_event(move_event)
    
    def _handle_absolute_event(self, event) -> None:
        """Handle absolute position events (touchpad, tablet)."""
        # For absolute devices, we need to get the device's axis info
        # This is more complex and device-specific
        # For now, we'll implement basic support
        
        if event.code == ecodes.ABS_X:
            # Convert absolute coordinate to screen coordinate
            # This is simplified - real implementation would need device calibration
            self._mouse_x = int((event.value / 65535.0) * self._screen_width)
        elif event.code == ecodes.ABS_Y:
            self._mouse_y = int((event.value / 65535.0) * self._screen_height)
        
        # Emit mouse move event
        if event.code in (ecodes.ABS_X, ecodes.ABS_Y):
            norm_x, norm_y = self._coordinate_transformer.normalize_coordinates(
                self._mouse_x, self._mouse_y, self._screen_width, self._screen_height
            )
            move_event = InputEvent.mouse_move(norm_x, norm_y)
            self._emit_event(move_event)
    
    def _handle_key_event(self, event) -> None:
        """Handle keyboard and mouse button events."""
        pressed = event.value == 1  # 1 = press, 0 = release, 2 = repeat
        
        # Skip repeat events
        if event.value == 2:
            return
        
        # Check if it's a mouse button
        mouse_button = self._convert_mouse_button(event.code)
        if mouse_button:
            # Get current mouse position for click event
            norm_x, norm_y = self._coordinate_transformer.normalize_coordinates(
                self._mouse_x, self._mouse_y, self._screen_width, self._screen_height
            )
            click_event = InputEvent.mouse_click(mouse_button, pressed, norm_x, norm_y)
            self._emit_event(click_event)
        else:
            # It's a keyboard key
            key_event = InputEvent.keyboard(event.code, pressed)
            self._emit_event(key_event)
    
    def _convert_mouse_button(self, key_code: int) -> Optional[MouseButton]:
        """Convert evdev key code to mouse button."""
        button_mapping = {
            ecodes.BTN_LEFT: MouseButton.LEFT,
            ecodes.BTN_RIGHT: MouseButton.RIGHT,
            ecodes.BTN_MIDDLE: MouseButton.MIDDLE,
        }
        
        # Handle additional buttons if available
        if hasattr(ecodes, 'BTN_SIDE'):
            button_mapping[ecodes.BTN_SIDE] = MouseButton.X1
        if hasattr(ecodes, 'BTN_EXTRA'):
            button_mapping[ecodes.BTN_EXTRA] = MouseButton.X2
        
        return button_mapping.get(key_code)