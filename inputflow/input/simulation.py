import abc
import sys
import time
from typing import Optional, Union

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

if sys.platform.startswith("linux"):
    try:
        import evdev
    except ImportError:
        evdev = None
else:
    evdev = None

from pynput import keyboard, mouse

# Shift mappings for typing
SHIFT_MAP = {
    "~": "`",
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    '"': "'",
    "<": ",",
    ">": ".",
    "?": "/",
}


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
    def press_key(self, key_str: str):
        """Simulates a key press from a string representation."""
        pass

    @abc.abstractmethod
    def release_key(self, key_str: str):
        """Simulates a key release from a string representation."""
        pass

    def replay_event(self, event: InputEvent):
        """Replays a received InputEvent."""
        if event.event_type == EventType.MOUSE_MOVE:
            data: MouseMoveEvent = event.data
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
            self.press_key(data.key_code) if data.pressed else self.release_key(
                data.key_code
            )
        else:
            self.logger.warning(f"Unknown event type received: {event.event_type}")

    def hotkey(self, *key_strs):
        """Simulates a hotkey combination from string representations."""
        for key in key_strs:
            self.press_key(key)
        time.sleep(0.01)  # Small delay between press and release
        for key in reversed(key_strs):
            self.release_key(key)

    def type_text(self, text: str):
        """Simulates typing a string of text."""
        for char in text:
            if "A" <= char <= "Z" or char in SHIFT_MAP:
                char_to_press = SHIFT_MAP.get(char, char.lower())
                self.hotkey("shift", char_to_press)
            else:
                self.hotkey(char)
            time.sleep(0.02)


class PynputSimulation(InputSimulation):
    """Input simulation for Windows and macOS using pynput."""

    def __init__(self, logger, config: Config):
        super().__init__(logger=logger, config=config)
        self._mouse = mouse.Controller()
        self._keyboard = keyboard.Controller()
        self._key_map = self._build_key_map()

    def _build_key_map(self):
        key_map = {k.name: k for k in keyboard.Key}
        # Add aliases
        key_map["win"] = key_map.get("cmd", key_map.get("super"))
        key_map["super"] = key_map.get("super", key_map.get("cmd"))
        return key_map

    def _to_pynput_key(
        self, key_str: Union[int, str]
    ):  # Accepts int for evdev scancodes
        if isinstance(
            key_str, int
        ):  # If it's an evdev scancode, try to find a pynput equivalent (basic)
            # This is a simplification; a full mapping table would be needed
            # For now, it assumes ASCII-like scancodes for alphanumeric and maps directly to char
            if 97 <= key_str <= 122:
                return chr(key_str)  # 'a' to 'z'
            if 48 <= key_str <= 57:
                return chr(key_str)  # '0' to '9'

            # Need more complex mapping for special keys/modifiers
            self.logger.warning(
                f"PynputSimulation: No direct mapping for evdev scancode {key_str}. Ignoring."
            )
            return None

        key_str = str(key_str).lower()  # Ensure it's a string
        if len(key_str) == 1:
            return key_str
        return self._key_map.get(key_str)

    def _map_int_to_pynput_button(self, button_int: int):
        if button_int == 1:
            return mouse.Button.left
        if button_int == 2:
            return mouse.Button.right
        if button_int == 3:
            return mouse.Button.middle  # Corrected
        return None

    def move_mouse_abs(self, x, y):
        self._mouse.position = (x, y)

    def move_mouse_rel(self, dx, dy):
        self._mouse.move(dx, dy)

    def click_mouse(self, button: Union[int, object], pressed: bool):
        pynput_button = (
            self._map_int_to_pynput_button(button)
            if isinstance(button, int)
            else button
        )
        if pynput_button:
            if pressed:
                self._mouse.press(pynput_button)
            else:
                self._mouse.release(pynput_button)
        else:
            self.logger.warning(f"PynputSimulation: Unknown mouse button: {button}")

    def scroll_mouse(self, dx, dy):
        self._mouse.scroll(dx, dy)

    def press_key(self, key_str: str):
        key = self._to_pynput_key(key_str)
        if key:
            self._keyboard.press(key)

    def release_key(self, key_str: str):
        key = self._to_pynput_key(key_str)
        if key:
            self._keyboard.release(key)

    def type_text(self, text: str):
        # pynput has a dedicated `type` method which is more reliable
        self._keyboard.type(text)


class UInputSimulation(InputSimulation):
    """Input simulation for Linux using evdev.uinput."""

    def __init__(self, logger, config: Config):
        super().__init__(logger=logger, config=config)
        if not evdev:
            self.logger.error(
                "evdev library is required for UInputSimulation on Linux."
            )
            raise RuntimeError(
                "evdev library is required for UInputSimulation on Linux."
            )

        self._build_key_map()

        key_codes = list(self._key_map.values())

        buttons = [
            evdev.ecodes.BTN_LEFT,
            evdev.ecodes.BTN_RIGHT,
            evdev.ecodes.BTN_MIDDLE,
        ]

        events = {
            evdev.ecodes.EV_REL: [
                evdev.ecodes.REL_X,
                evdev.ecodes.REL_Y,
                evdev.ecodes.REL_WHEEL,
                evdev.ecodes.REL_HWHEEL,
            ],
            evdev.ecodes.EV_KEY: key_codes + buttons,
        }

        try:
            self._device = evdev.UInput(events=events, name="inputflow-virtual-device")
            self._x, self._y = 0, 0
            self.logger.info("UInputSimulation: Virtual device created successfully.")
        except Exception as e:
            self.logger.error(
                f"Failed to create UInput device. Try running as root. Error: {e}"
            )
            raise e

    def _build_key_map(self):
        self._key_map = {
            **{
                chr(c): getattr(evdev.ecodes, f"KEY_{chr(c).upper()}")
                for c in range(ord("a"), ord("z") + 1)
            },
            **{
                chr(c): getattr(evdev.ecodes, f"KEY_{chr(c)}")
                for c in range(ord("0"), ord("9") + 1)
            },
            "enter": evdev.ecodes.KEY_ENTER,
            "esc": evdev.ecodes.KEY_ESC,
            "backspace": evdev.ecodes.KEY_BACKSPACE,
            "tab": evdev.ecodes.KEY_TAB,
            "space": evdev.ecodes.KEY_SPACE,
            " ": evdev.ecodes.KEY_SPACE,
            "`": evdev.ecodes.KEY_GRAVE,
            "-": evdev.ecodes.KEY_MINUS,
            "=": evdev.ecodes.KEY_EQUAL,
            "[": evdev.ecodes.KEY_LEFTBRACE,
            "]": evdev.ecodes.KEY_RIGHTBRACE,
            "\\": evdev.ecodes.KEY_BACKSLASH,
            ";": evdev.ecodes.KEY_SEMICOLON,
            "'": evdev.ecodes.KEY_APOSTROPHE,
            ",": evdev.ecodes.KEY_COMMA,
            ".": evdev.ecodes.KEY_DOT,
            "/": evdev.ecodes.KEY_SLASH,
            "ctrl": evdev.ecodes.KEY_LEFTCTRL,
            "alt": evdev.ecodes.KEY_LEFTALT,
            "shift": evdev.ecodes.KEY_LEFTSHIFT,
            "super": evdev.ecodes.KEY_LEFTMETA,
            "cmd": evdev.ecodes.KEY_LEFTMETA,
            "win": evdev.ecodes.KEY_LEFTMETA,
            "up": evdev.ecodes.KEY_UP,
            "down": evdev.ecodes.KEY_DOWN,
            "left": evdev.ecodes.KEY_LEFT,
            "right": evdev.ecodes.KEY_RIGHT,
            **{f"f{i}": getattr(evdev.ecodes, f"KEY_F{i}") for i in range(1, 13)},
        }

    def _map_str_to_evdev(self, key_str: str):
        return self._key_map.get(key_str.lower())

    # New method to map int (scancode) to evdev keycode
    def _map_int_to_evdev(self, scancode: int):
        # This mapping is very basic and might need a full scancode-to-keycode table
        # For now, it assumes ASCII-like scancodes for alphanumeric and maps directly
        if 97 <= scancode <= 122:  # 'a' to 'z'
            return getattr(evdev.ecodes, f"KEY_{chr(scancode).upper()}", None)
        if 48 <= scancode <= 57:  # '0' to '9'
            return getattr(evdev.ecodes, f"KEY_{chr(scancode)}", None)

        # For special keys, we'd need a comprehensive lookup table or a more direct approach
        # This is a placeholder for now
        self.logger.warning(
            f"UInputSimulation: No direct mapping for scancode {scancode}. Ignoring."
        )
        return None

    def _map_int_to_evdev_button(self, button_int: int):
        if button_int == 1:
            return evdev.ecodes.BTN_LEFT
        if button_int == 2:
            return evdev.ecodes.BTN_RIGHT
        if button_int == 3:
            return evdev.ecodes.BTN_MIDDLE  # Corrected
        return None

    def move_mouse_abs(self, x, y):
        dx = x - self._x
        dy = y - self._y
        self.move_mouse_rel(dx, dy)

    def move_mouse_rel(self, dx, dy):
        self._x += dx
        self._y += dy
        self._device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_X, dx)
        self._device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_Y, dy)
        self._device.syn()

    def click_mouse(self, button: Union[int, object], pressed: bool):
        btn_code = (
            self._map_int_to_evdev_button(button) if isinstance(button, int) else None
        )
        if btn_code:
            self._device.write(evdev.ecodes.EV_KEY, btn_code, 1 if pressed else 0)
            self._device.syn()
        else:
            self.logger.warning(f"UInputSimulation: Unknown mouse button: {button}")

    def scroll_mouse(self, dx, dy):
        if dy != 0:
            self._device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_WHEEL, -dy)
        if dx != 0:
            self._device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_HWHEEL, dx)
        self._device.syn()

    def press_key(
        self, key: Union[int, str]
    ):  # Accepts int for evdev scancodes, str for pynput key names/chars
        key_code: Optional[int] = None
        if isinstance(key, str):
            key_code = self._map_str_to_evdev(key)
        elif isinstance(key, int):
            key_code = self._map_int_to_evdev(key)  # Map int scancode to evdev keycode
        else:
            self.logger.warning(f"UInputSimulation: Unknown key type for press: {key}")
            return

        if key_code is not None:
            self._device.write(evdev.ecodes.EV_KEY, key_code, 1)
            self._device.syn()
        else:
            self.logger.warning(f"No evdev key found for '{key}'")

    def release_key(
        self, key: Union[int, str]
    ):  # Accepts int for evdev scancodes, str for pynput key names/chars
        key_code: Optional[int] = None
        if isinstance(key, str):
            key_code = self._map_str_to_evdev(key)
        elif isinstance(key, int):
            key_code = self._map_int_to_evdev(key)  # Map int scancode to evdev keycode
        else:
            self.logger.warning(
                f"UInputSimulation: Unknown key type for release: {key}"
            )
            return

        if key_code is not None:
            self._device.write(evdev.ecodes.EV_KEY, key_code, 0)
            self._device.syn()
        else:
            self.logger.warning(f"No evdev key found for '{key}'")

    def __del__(self):
        if hasattr(self, "_device") and self._device:
            self._device.close()


def get_input_simulation(logger, config: Config) -> InputSimulation:
    """
    Factory function to get the appropriate input simulation implementation
    for the current platform.
    """
    platform = sys.platform
    if platform in ("win32", "darwin"):
        return PynputSimulation(logger=logger, config=config)
    elif platform.startswith("linux"):
        if evdev:
            return UInputSimulation(logger=logger, config=config)
        else:
            logger.error(
                "evdev library not found, cannot use UInputSimulation on Linux."
            )
            raise RuntimeError(
                "evdev library not found, cannot use UInputSimulation on Linux."
            )
    else:
        raise NotImplementedError(f"Platform {platform} is not supported.")
