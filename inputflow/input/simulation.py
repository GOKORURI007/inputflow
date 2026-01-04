import abc
import sys
import time

if sys.platform.startswith("linux"):
    try:
        import evdev
    except ImportError:
        evdev = None
else:
    evdev = None

from pynput import mouse, keyboard

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

    def __init__(self):
        self._mouse = mouse.Controller()
        self._keyboard = keyboard.Controller()
        self._key_map = self._build_key_map()

    def _build_key_map(self):
        key_map = {k.name: k for k in keyboard.Key}
        # Add aliases
        key_map["win"] = key_map.get("cmd", key_map.get("super"))
        key_map["super"] = key_map.get("super", key_map.get("cmd"))
        return key_map

    def _to_pynput_key(self, key_str: str):
        key_str = key_str.lower()
        if len(key_str) == 1:
            return key_str
        return self._key_map.get(key_str)

    def move_mouse_abs(self, x, y):
        self._mouse.position = (x, y)

    def move_mouse_rel(self, dx, dy):
        self._mouse.move(dx, dy)

    def click_mouse(self, button, pressed):
        if pressed:
            self._mouse.press(button)
        else:
            self._mouse.release(button)

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

    def __init__(self):
        if not evdev:
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
        except Exception as e:
            print(
                "Failed to create UInput device. Try running as root.", file=sys.stderr
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

    def click_mouse(self, button, pressed):
        if button == mouse.Button.left:
            btn_code = evdev.ecodes.BTN_LEFT
        elif button == mouse.Button.right:
            btn_code = evdev.ecodes.BTN_RIGHT
        elif button == mouse.Button.middle:
            btn_code = evdev.ecodes.BTN_MIDDLE
        else:
            return
        self._device.write(evdev.ecodes.EV_KEY, btn_code, 1 if pressed else 0)
        self._device.syn()

    def scroll_mouse(self, dx, dy):
        if dy != 0:
            self._device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_WHEEL, -dy)
        if dx != 0:
            self._device.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_HWHEEL, dx)
        self._device.syn()

    def press_key(self, key_str: str):
        key_code = self._map_str_to_evdev(key_str)
        if key_code is not None:
            self._device.write(evdev.ecodes.EV_KEY, key_code, 1)
            self._device.syn()
        else:
            print(f"Warning: No evdev key found for '{key_str}'")

    def release_key(self, key_str: str):
        key_code = self._map_str_to_evdev(key_str)
        if key_code is not None:
            self._device.write(evdev.ecodes.EV_KEY, key_code, 0)
            self._device.syn()
        else:
            print(f"Warning: No evdev key found for '{key_str}'")

    def __del__(self):
        if hasattr(self, "_device") and self._device:
            self._device.close()


def get_input_simulation() -> InputSimulation:
    """
    Factory function to get the appropriate input simulation implementation
    for the current platform.
    """
    platform = sys.platform
    if platform in ("win32", "darwin"):
        return PynputSimulation()
    elif platform.startswith("linux"):
        if evdev:
            return UInputSimulation()
        else:
            raise RuntimeError(
                "evdev library not found, cannot use UInputSimulation on Linux."
            )
    else:
        raise NotImplementedError(f"Platform {platform} is not supported.")
