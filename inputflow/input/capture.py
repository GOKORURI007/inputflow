import abc
import select
import sys
import time
from threading import Event, Thread
from typing import Callable, Union

from inputflow.config.models import Config
from inputflow.core.coordinates import CoordinateTransformer
from inputflow.core.events import (
    EventType,
    InputEvent,
    KeyboardEvent,
    MouseClickEvent,
    MouseMoveEvent,
    MouseScrollEvent,
)


# TODO 解决鼠标按键和 ctrl 等特殊建的跨平台识别问题
class InputCapture(abc.ABC):
    """
    An abstract base class for input capturing.
    """

    def __init__(
        self,
        logger,
        config: Config,
        event_callback: Callable[[InputEvent], None],
        move_throttle_ms=16,
    ):
        self.logger = logger
        self.config = config
        self.event_callback = event_callback
        self._move_throttle_sec = (
            config.capture.move_throttle_ms / 1000.0
            if hasattr(config, "capture")
            and hasattr(config.capture, "move_throttle_ms")
            else move_throttle_ms / 1000.0
        )
        self._last_move_time = 0
        self.coord_transformer = CoordinateTransformer(
            screen_width=self.config.display.width,
            screen_height=self.config.display.height,
        )

    @abc.abstractmethod
    def start_monitoring(self):
        """Starts monitoring input events."""
        pass

    @abc.abstractmethod
    def stop_monitoring(self):
        """Stops monitoring input events."""
        pass

    def on_mouse_move(self, x: int, y: int):
        current_time = time.time()
        if current_time - self._last_move_time < self._move_throttle_sec:
            return
        self._last_move_time = current_time

        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        event_data = MouseMoveEvent(
            normalized_x=normalized_x, normalized_y=normalized_y
        )
        self.event_callback(
            InputEvent(event_type=EventType.MOUSE_MOVE, data=event_data)
        )
        self.logger.debug(
            f"Mouse moved to ({x}, {y}) -> Normalized ({normalized_x}, {normalized_y})"
        )

    def on_mouse_click(self, x: int, y: int, button: Union[int, object], pressed: bool):
        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)

        # Convert pynput.mouse.Button to int (value attribute) or evdev button code to int
        button_int: int
        if isinstance(button, int):  # evdev keycodes are already integers
            button_int = button
        elif hasattr(
            button, "value"
        ):  # pynput.mouse.Button has a value (e.g., 1, 2, 3)
            button_int = button.value
        else:  # Fallback for unexpected types
            button_int = 0  # Indicate unknown button
            self.logger.warning(f"Unknown mouse button type for capture: {button}")

        event_data = MouseClickEvent(
            button=button_int,
            pressed=pressed,
            normalized_x=normalized_x,
            normalized_y=normalized_y,
        )
        self.event_callback(
            InputEvent(event_type=EventType.MOUSE_CLICK, data=event_data)
        )
        self.logger.debug(
            f"Mouse {'pressed' if pressed else 'released'} button {button_int} at ({x}, {y})"
        )

    def on_mouse_scroll(self, x: int, y: int, dx: int, dy: int):
        # Coordinates are usually ignored for scroll events but included for consistency
        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        event_data = MouseScrollEvent(delta_x=dx, delta_y=dy)
        self.event_callback(
            InputEvent(event_type=EventType.MOUSE_SCROLL, data=event_data)
        )
        self.logger.debug(f"Mouse scrolled at ({x}, {y}) with delta ({dx}, {dy})")

    def on_key_event(
        self, key: Union[int, object], pressed: bool
    ):  # key from pynput or evdev
        # Convert pynput.keyboard.Key or KeyCode to a string representation for consistency
        key_repr: Union[int, str]
        if isinstance(key, int):  # Evdev keycode is already an int (scancode)
            key_repr = key
        elif (
            hasattr(key, "char") and key.char is not None
        ):  # pynput.keyboard.KeyCode (e.g., 'a', '1', '!')
            key_repr = key.char
        elif hasattr(
            key, "name"
        ):  # pynput.keyboard.Key (e.g., 'alt', 'ctrl', 'super', 'shift')
            key_repr = key.name
        else:  # Fallback for unexpected pynput objects or unknown types
            key_repr = str(key)  # Fallback to string representation

        event_data = KeyboardEvent(key_code=key_repr, pressed=pressed)
        self.event_callback(InputEvent(event_type=EventType.KEYBOARD, data=event_data))
        self.logger.debug(f"Key {key_repr} {'pressed' if pressed else 'released'}")


class PynputCapture(InputCapture):
    """Input capture for Windows and macOS using pynput."""

    def __init__(
        self, logger, config, event_callback: Callable[[InputEvent], None], **kwargs
    ):
        super().__init__(
            logger=logger, config=config, event_callback=event_callback, **kwargs
        )
        from pynput import keyboard, mouse

        # Pynput returns absolute coordinates for mouse move
        def pynput_on_move(x, y):
            self.on_mouse_move(x, y)

        # pynput.mouse.Button has a `value` attribute which is an int
        def pynput_on_click(x, y, button, pressed):
            self.on_mouse_click(
                x, y, button, pressed
            )  # Pass button object for conversion in super

        def pynput_on_scroll(x, y, dx, dy):
            self.on_mouse_scroll(x, y, dx, dy)

        def pynput_on_press(key):
            self.on_key_event(key, True)  # Pass key object for conversion in super

        def pynput_on_release(key):
            self.on_key_event(key, False)  # Pass key object for conversion in super

        self._mouse_listener = mouse.Listener(
            on_move=pynput_on_move,
            on_click=pynput_on_click,
            on_scroll=pynput_on_scroll,
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=pynput_on_press, on_release=pynput_on_release
        )
        self._monitoring = False

    def start_monitoring(self):
        if not self._monitoring:
            self._mouse_listener.start()
            self._keyboard_listener.start()
            self._monitoring = True
            self.logger.info("PynputCapture: Started monitoring.")

    def stop_monitoring(self):
        if self._monitoring:
            self._mouse_listener.stop()
            self._keyboard_listener.stop()
            self._monitoring = False
            self.logger.info("PynputCapture: Stopped monitoring.")


class EvdevCapture(InputCapture):
    """Input capture for Linux using evdev."""

    def __init__(
        self, logger, config, event_callback: Callable[[InputEvent], None], **kwargs
    ):
        super().__init__(
            logger=logger, config=config, event_callback=event_callback, **kwargs
        )
        import evdev

        self.evdev = evdev
        self._stop_event = Event()
        self._thread = None
        self._devices = []
        self._x, self._y = 0, 0  # Internal cursor position

    def _discover_devices(self):
        try:
            device_paths = self.evdev.list_devices()
        except Exception as e:
            self.logger.error(f"EvdevCapture: Could not list devices: {e}")
            return

        for path in device_paths:
            try:
                device = self.evdev.InputDevice(path)
                capabilities = device.capabilities(verbose=False)
                # It's a keyboard if it has keys
                has_keys = self.evdev.ecodes.EV_KEY in capabilities
                # It's a mouse if it has relative X and Y axes
                has_rel_xy = (
                    self.evdev.ecodes.EV_REL in capabilities
                    and self.evdev.ecodes.REL_X
                    in capabilities[self.evdev.ecodes.EV_REL]
                    and self.evdev.ecodes.REL_Y
                    in capabilities[self.evdev.ecodes.EV_REL]
                )

                if has_keys or has_rel_xy:
                    self._devices.append(device)
                    self.logger.info(
                        f"EvdevCapture: Monitoring device: {device.name} at {path}"
                    )

            except (IOError, PermissionError):
                pass  # Suppressing output for non-readable devices to avoid spam.

        if not self._devices:
            self.logger.warning(
                "EvdevCapture: No suitable input devices found or permission denied. Try running as root."
            )

    def _monitor(self):
        self.logger.info("EvdevCapture: Monitoring thread started.")
        fds = {dev.fd: dev for dev in self._devices}

        rel_dx, rel_dy = 0, 0
        scroll_dx, scroll_dy = 0, 0

        while not self._stop_event.is_set():
            try:
                r, w, x = select.select(fds, [], [], 0.1)
                if not r:
                    continue

                for fd in r:
                    device = fds[fd]
                    for event in device.read():
                        if event.type == self.evdev.ecodes.EV_SYN:
                            if rel_dx != 0 or rel_dy != 0:
                                self._x += rel_dx
                                self._y += rel_dy
                                # Evdev only gives relative coords, so our stored _x, _y is current mouse position.
                                self.on_mouse_move(self._x, self._y)
                                rel_dx, rel_dy = 0, 0
                            if scroll_dx != 0 or scroll_dy != 0:
                                # Coordinates for scroll are not usually passed, use current mouse position
                                self.on_mouse_scroll(
                                    self._x, self._y, scroll_dx, scroll_dy
                                )
                                scroll_dx, scroll_dy = 0, 0

                        elif event.type == self.evdev.ecodes.EV_REL:
                            if event.code == self.evdev.ecodes.REL_X:
                                rel_dx += event.value
                            elif event.code == self.evdev.ecodes.REL_Y:
                                rel_dy += event.value
                            elif event.code == self.evdev.ecodes.REL_WHEEL:
                                scroll_dy += event.value
                            elif event.code == self.evdev.ecodes.REL_HWHEEL:
                                scroll_dx += event.value

                        elif event.type == self.evdev.ecodes.EV_KEY:
                            key_event = self.evdev.categorize(event)
                            is_pressed = (
                                event.value == 1
                            )  # 1 for press, 0 for release, 2 for repeat

                            # Distinguish between mouse buttons and keyboard keys
                            if "BTN_" in key_event.keycode:
                                # For evdev mouse buttons, map BTN_LEFT to 1, BTN_RIGHT to 2, BTN_MIDDLE to 3 (matching pynput)
                                button_value = 0
                                if key_event.keycode == self.evdev.ecodes.BTN_LEFT:
                                    button_value = 1
                                elif key_event.keycode == self.evdev.ecodes.BTN_RIGHT:
                                    button_value = 2
                                elif key_event.keycode == self.evdev.ecodes.BTN_MIDDLE:
                                    button_value = 3  # Fixed: was 4, now 3
                                self.on_mouse_click(
                                    self._x, self._y, button_value, is_pressed
                                )
                            else:
                                self.on_key_event(
                                    key_event.scancode, is_pressed
                                )  # Use scancode for evdev keys

            except Exception as e:
                self.logger.error(f"EvdevCapture: Error in monitoring loop: {e}")
                break

        self.logger.info("EvdevCapture: Monitoring thread stopped.")

    def start_monitoring(self):
        self.logger.info("EvdevCapture: Starting monitoring...")
        self.logger.warning(
            "NOTE: evdev requires running as root or user in the 'input' group."
        )

        # Discover devices in the main thread before starting the monitor thread
        try:
            self._discover_devices()
        except Exception as e:
            self.logger.error(f"EvdevCapture: Failed to discover devices: {e}")
            return

        if not self._devices:
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._monitor)
        self._thread.start()

    def stop_monitoring(self):
        self.logger.info("EvdevCapture: Stopping monitoring...")
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None

        for device in self._devices:
            try:
                device.close()
            except Exception as e:
                self.logger.error(
                    f"EvdevCapture: Error while closing device {device.path}: {e}"
                )
        self._devices = []


def get_input_capture(
    logger,
    config: Config,
    event_callback: Callable[[InputEvent], None] = lambda _: ...,
    **kwargs,
) -> InputCapture:
    """
    Factory function to get the appropriate input capture implementation
    for the current platform.
    """
    platform = sys.platform
    if platform == "win32" or platform == "darwin":
        return PynputCapture(
            logger=logger, config=config, event_callback=event_callback, **kwargs
        )
    elif platform.startswith("linux"):
        # evdev is a better choice for linux, especially for Wayland.
        # but pynput also has a linux implementation that can be a fallback.
        try:
            return EvdevCapture(
                logger=logger, config=config, event_callback=event_callback, **kwargs
            )
        except ImportError:
            logger.warning("evdev library not found, falling back to pynput on Linux.")
            return PynputCapture(
                logger=logger, config=config, event_callback=event_callback, **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to initialize EvdevCapture: {e}")
            logger.warning("Falling back to pynput on Linux.")
            return PynputCapture(
                logger=logger, config=config, event_callback=event_callback, **kwargs
            )
    else:
        raise NotImplementedError(f"Platform {platform} is not supported.")
