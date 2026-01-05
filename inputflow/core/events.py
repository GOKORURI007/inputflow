from dataclasses import dataclass
from enum import Enum
from typing import Union


class EventType(Enum):
    MOUSE_MOVE = 1
    MOUSE_CLICK = 2
    MOUSE_SCROLL = 3
    KEYBOARD = 4


@dataclass
class MouseMoveEvent:
    normalized_x: float
    normalized_y: float
    timestamp: float


@dataclass
class MouseClickEvent:
    button: int  # Using int for simplicity, can be mapped to a button enum later
    pressed: bool
    normalized_x: float
    normalized_y: float
    timestamp: float


@dataclass
class MouseScrollEvent:
    delta_x: int
    delta_y: int
    timestamp: float


@dataclass
class KeyboardEvent:
    key_code: int  # Using int for simplicity
    pressed: bool
    timestamp: float


@dataclass
class InputEvent:
    event_type: EventType
    data: Union[MouseMoveEvent, MouseClickEvent, MouseScrollEvent, KeyboardEvent]
