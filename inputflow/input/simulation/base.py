import abc
import time

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


class InputSimulation(abc.ABC):
    """
    An abstract base class for input simulation.
    """

    def __init__(self, logger, config: Config):
        self.logger = logger
        self.config = config
        self.coord_transformer = CoordinateTransformer(
            screen_width=self.config.display.width,
            screen_height=self.config.display.height,
        )

    @abc.abstractmethod
    def move_mouse_abs(self, x, y):
        """Moves the mouse to an absolute position."""
        pass

    @abc.abstractmethod
    def move_mouse_rel(self, dx, dy):
        """Moves the mouse by a relative offset."""
        pass

    @abc.abstractmethod
    def click_mouse(self, button, pressed):
        """Simulates a mouse click."""
        pass

    @abc.abstractmethod
    def scroll_mouse(self, dx, dy):
        """Simulates mouse scrolling."""
        pass

    @abc.abstractmethod
    def click_key(self, key, pressed):
        """Simulates a key press from a string representation."""
        pass

    def replay_event(self, event: InputEvent):
        """Replays a received InputEvent."""
        if event.event_type == EventType.MOUSE_MOVE:
            data: MouseMoveEvent = event.data
            if data.dx is not None and data.dy is not None:
                self.move_mouse_rel(data.dx, data.dy)
            else:
                abs_x, abs_y = self.coord_transformer.denormalize(
                    data.normalized_x, data.normalized_y
                )
                self.move_mouse_abs(abs_x, abs_y)
        elif event.event_type == EventType.MOUSE_CLICK:
            data: MouseClickEvent = event.data
            abs_x, abs_y = self.coord_transformer.denormalize(
                data.normalized_x, data.normalized_y
            )
            # For click, we move to position first, then click.
            self.move_mouse_abs(abs_x, abs_y)
            self.click_mouse(data.button, data.pressed)
        elif event.event_type == EventType.MOUSE_SCROLL:
            data: MouseScrollEvent = event.data
            self.scroll_mouse(data.delta_x, data.delta_y)
        elif event.event_type == EventType.KEYBOARD:
            data: KeyboardEvent = event.data
            # KeyboardEvent.key_code can be int (evdev scancode) or str (pynput key name/char)
            self.click_key(data.key_code, data.pressed)
        else:
            self.logger.warning(f"Unknown event type received: {event.event_type}")

    def hotkey(self, *key_strs):
        """Simulates a hotkey combination from string representations."""
        for key in key_strs:
            self.click_key(key, pressed=True)
        time.sleep(0.01)  # Small delay between press and release
        for key in reversed(key_strs):
            self.click_key(key, pressed=False)
