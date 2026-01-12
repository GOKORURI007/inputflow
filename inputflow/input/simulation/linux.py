import platform
from typing import Optional, Union

from inputflow.config.models import Config
from inputflow.core.keymaps import hid_to_ecode_btn, hid_to_ecode_key
from inputflow.input.simulation import InputSimulation

if platform.system() == "Linux":
    try:
        import evdev
    except ImportError:
        evdev = None


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
            **{f"f{i}": getattr(evdev.ecodes, f"KEY_F{i}") for i in range(1, 13)},
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

    def click_mouse(self, button: int, pressed: bool):
        # btn_code = (
        #     self._map_int_to_evdev_button(button) if isinstance(button, int) else None
        # )
        btn_code = hid_to_ecode_btn(button)
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

    def click_key(self, key: int, pressed: bool):
        key_code = hid_to_ecode_key(key)
        if key_code:
            self._device.write(evdev.ecodes.EV_KEY, key_code, 1 if pressed else 0)
            self._device.syn()
        else:
            self.logger.warning(f"No evdev key found for '{key}'")

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
