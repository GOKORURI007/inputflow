from typing import Callable

from pynput.keyboard import Key
from pynput.mouse import Button

from inputflow.core.events import (
    EventType,
    InputEvent,
    KeyboardEvent,
    MouseClickEvent,
)
from inputflow.core.keymaps import (
    hid_to_name_btn,
    hid_to_name_key,
    vk_to_hid_btn,
    vk_to_hid_key,
)

from .base import InputCapture


class PynputCapture(InputCapture):
    """Input capture for Windows and macOS using pynput."""

    def __init__(
        self, logger, config, event_callback: Callable[[InputEvent], None], **kwargs
    ):
        super().__init__(
            logger=logger, config=config, event_callback=event_callback, **kwargs
        )
        from pynput import keyboard, mouse

        def pynput_on_press(key):
            self.on_key_event(key, True)  # Pass key object for conversion in super

        def pynput_on_release(key):
            self.on_key_event(key, False)  # Pass key object for conversion in super

        self._mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_scroll=self.on_mouse_scroll,
            on_click=self.on_mouse_click,
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

    def on_mouse_click(self, x: int, y: int, button: Button, pressed: bool):
        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        if not isinstance(button, Button):
            self.logger.warning(f"Unknown mouse button type for capture: {button}")
        button_value = vk_to_hid_btn(button)
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

    def on_key_event(self, key: Key, pressed: bool):
        key_value: int

        if hasattr(key, "value"):
            key_value = vk_to_hid_key(key.value.vk)
        else:
            key_value = vk_to_hid_key(key.vk)

        event_data = KeyboardEvent(key_code=key_value, pressed=pressed)
        self.event_callback(InputEvent(event_type=EventType.KEYBOARD, data=event_data))
        self.logger.debug(
            f"Key {str(hid_to_name_key(key_value))}:{key_value} {'pressed' if pressed else 'released'}"
        )
