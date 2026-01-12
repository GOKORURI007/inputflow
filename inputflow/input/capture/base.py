import abc
import select
import sys
import time
from threading import Event, Thread
from typing import Callable, Union

from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

from inputflow.config.models import Config
from inputflow.core import keymaps
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

    def on_mouse_move(self, x: int, y: int, log: bool = False):
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
        if log:
            self.logger.debug(
                f"Mouse moved to ({x}, {y}) -> Normalized ({normalized_x}, {normalized_y})"
            )

    @abc.abstractmethod
    def on_mouse_click(self, x: int, y: int, button: Union[int, Button], pressed: bool):
        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        print(button)
        if isinstance(button, int):  # evdev keycodes are already integers
            button_int = button
        elif hasattr(button, "name"):  # pynput.mouse.Button has a value (e.g., 1, 2, 3)
            button_int = keymaps.PYNPUT_TO_EVCODE.get(button.name, 0)
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

    def on_mouse_scroll(self, x: int, y: int, dx: int, dy: int, log: bool = False):
        # Coordinates are usually ignored for scroll events but included for consistency
        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        event_data = MouseScrollEvent(delta_x=dx, delta_y=dy)
        self.event_callback(
            InputEvent(event_type=EventType.MOUSE_SCROLL, data=event_data)
        )
        if log:
            self.logger.debug(f"Mouse scrolled at ({x}, {y}) with delta ({dx}, {dy})")

    @abc.abstractmethod
    def on_key_event(self, key: Union[str, Key], pressed: bool):
        key_repr: str
        if isinstance(key, str):
            key_repr = key
        elif (
            hasattr(key, "char") and key.char is not None
        ):  # pynput.keyboard.KeyCode (e.g., 'a', '1', '!')
            key_repr = keymaps.PYNPUT_TO_STR.get(key.__str__(), key.char)
        elif hasattr(key, "name"):
            key_repr = keymaps.PYNPUT_TO_STR.get(key.__str__(), key.name)
        else:
            key_repr = str(key)

        event_data = KeyboardEvent(key_code=key_repr, pressed=pressed)
        self.event_callback(InputEvent(event_type=EventType.KEYBOARD, data=event_data))
        self.logger.debug(f"Key {key_repr} {'pressed' if pressed else 'released'}")
