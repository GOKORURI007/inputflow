"""Core event data structures for InputFlow."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Union


class EventType(Enum):
    """Types of input events that can be captured and transmitted."""
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_SCROLL = "mouse_scroll"
    KEYBOARD = "keyboard"


class MouseButton(Enum):
    """Mouse button identifiers."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    X1 = "x1"
    X2 = "x2"


@dataclass
class MouseMoveEvent:
    """Mouse movement event with normalized coordinates."""
    normalized_x: float
    normalized_y: float
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class MouseClickEvent:
    """Mouse click event with button and position information."""
    button: MouseButton
    pressed: bool
    normalized_x: float
    normalized_y: float
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class MouseScrollEvent:
    """Mouse scroll wheel event."""
    delta_x: int
    delta_y: int
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class KeyboardEvent:
    """Keyboard key press/release event."""
    key_code: int
    pressed: bool
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class InputEvent:
    """Generic input event container."""
    event_type: EventType
    data: Union[MouseMoveEvent, MouseClickEvent, MouseScrollEvent, KeyboardEvent]
    
    @classmethod
    def mouse_move(cls, normalized_x: float, normalized_y: float) -> 'InputEvent':
        """Create a mouse movement event."""
        return cls(
            event_type=EventType.MOUSE_MOVE,
            data=MouseMoveEvent(normalized_x, normalized_y)
        )
    
    @classmethod
    def mouse_click(cls, button: MouseButton, pressed: bool, 
                   normalized_x: float, normalized_y: float) -> 'InputEvent':
        """Create a mouse click event."""
        return cls(
            event_type=EventType.MOUSE_CLICK,
            data=MouseClickEvent(button, pressed, normalized_x, normalized_y)
        )
    
    @classmethod
    def mouse_scroll(cls, delta_x: int, delta_y: int) -> 'InputEvent':
        """Create a mouse scroll event."""
        return cls(
            event_type=EventType.MOUSE_SCROLL,
            data=MouseScrollEvent(delta_x, delta_y)
        )
    
    @classmethod
    def keyboard(cls, key_code: int, pressed: bool) -> 'InputEvent':
        """Create a keyboard event."""
        return cls(
            event_type=EventType.KEYBOARD,
            data=KeyboardEvent(key_code, pressed)
        )