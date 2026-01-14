import abc
import time
from typing import Callable

from pynput.keyboard import Key
from pynput.mouse import Button

from inputflow.config.models import Config
from inputflow.core.coordinates import CoordinateTransformer
from inputflow.core.events import (
    EventType,
    InputEvent,
    MouseMoveEvent,
    MouseScrollEvent,
)


class InputCapture(abc.ABC):
    """
    An abstract base class for input capturing.
    """

    def __init__(
        self,
        logger,
        config: Config,
        event_callback: Callable[[InputEvent], None],
        hotkey_callback: Callable[[str], None] = None,
        move_throttle_ms=16,
    ):
        self.logger = logger
        self.config = config
        self.event_callback = event_callback
        self.hotkey_callback = hotkey_callback
        self._move_throttle_sec = (
            config.capture.move_throttle_ms / 1000.0
            if hasattr(config, 'capture') and hasattr(config.capture, 'move_throttle_ms')
            else move_throttle_ms / 1000.0
        )
        self._last_move_time = 0
        self._last_x = None
        self._last_y = None
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

    @abc.abstractmethod
    def on_key_event(self, key: int | Key, pressed: bool):
        pass

    @abc.abstractmethod
    def on_mouse_click(self, x: int, y: int, button: int | Button, pressed: bool):
        pass

    def on_mouse_move(self, x: int, y: int, log: bool = False):
        current_time = time.time()
        if current_time - self._last_move_time < self._move_throttle_sec:
            return
        self._last_move_time = current_time

        dx = x - self._last_x if self._last_x is not None else 0
        dy = y - self._last_y if self._last_y is not None else 0
        self._last_x, self._last_y = x, y

        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        event_data = MouseMoveEvent(normalized_x=normalized_x, normalized_y=normalized_y, dx=dx, dy=dy)
        self.event_callback(InputEvent(event_type=EventType.MOUSE_MOVE, data=event_data))
        if log:
            self.logger.debug(
                f'Mouse moved to ({x}, {y}) -> Normalized ({normalized_x}, {normalized_y}), Relative ({dx}, {dy})'
            )

    def on_mouse_scroll(self, x: int, y: int, dx: int, dy: int, log: bool = False):
        # Coordinates are usually ignored for scroll events but included for consistency
        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        event_data = MouseScrollEvent(delta_x=dx, delta_y=dy)
        self.event_callback(InputEvent(event_type=EventType.MOUSE_SCROLL, data=event_data))
        if log:
            self.logger.debug(f'Mouse scrolled at ({x}, {y}) with delta ({dx}, {dy})')
