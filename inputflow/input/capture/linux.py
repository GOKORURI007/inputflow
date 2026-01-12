import select
from threading import Event, Thread
from typing import Callable, Union

from pynput.keyboard import Key
from pynput.mouse import Button

from inputflow.core.events import EventType, InputEvent, KeyboardEvent, MouseClickEvent

from ...core.keymaps import (
    ecode_to_hid_btn,
    ecode_to_hid_key,
    hid_to_name_btn,
    hid_to_name_key,
    name_to_hid_key,
)
from .base import InputCapture


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
                            keycodes = key_event.keycode
                            if isinstance(keycodes, str):
                                keycodes = (keycodes,)
                            if any("BTN_" in k for k in keycodes):
                                # For evdev mouse buttons, map BTN_LEFT to 1, BTN_RIGHT to 2, BTN_MIDDLE to 3 (matching pynput)
                                self.on_mouse_click(
                                    self._x, self._y, key_event.scancode, is_pressed
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

    def on_mouse_click(self, x: int, y: int, button: int, pressed: bool):
        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        if isinstance(button, int):  # evdev keycodes are already integers
            button_value = ecode_to_hid_btn(button)
        else:  # Fallback for unexpected types
            button_value = 0  # Indicate unknown button
            self.logger.warning(f"Unknown mouse button type for capture: {button}")

        event_data = MouseClickEvent(
            button=button_value,
            pressed=pressed,
            normalized_x=normalized_x,
            normalized_y=normalized_y,
        )
        self.event_callback(
            InputEvent(event_type=EventType.MOUSE_CLICK, data=event_data)
        )
        self.logger.debug(
            f"Mouse {'pressed' if pressed else 'released'} button {hid_to_name_btn(button_value)}:{button_value} at ({x}, {y})"
        )

    def on_key_event(self, key: int, pressed: bool):
        if isinstance(key, int):
            key_value = ecode_to_hid_key(key)
        else:
            key_value = 0

        event_data = KeyboardEvent(key_code=key_value, pressed=pressed)
        self.event_callback(InputEvent(event_type=EventType.KEYBOARD, data=event_data))
        self.logger.debug(
            f"Key {hid_to_name_key(key_value)}:{key_value} {'pressed' if pressed else 'released'}"
        )
