from inputflow.config.models import Config
from inputflow.input.simulation import InputSimulation
from inputflow.keymaps import hid_to_ecode


class UInputSimulation(InputSimulation):
    """Input simulation for Linux using evdev.uinput."""

    def __init__(self, logger, config: Config):
        super().__init__(logger=logger, config=config)

        try:
            import evdev
        except ImportError:
            logger.error(
                "evdev library not found, cannot use UInputSimulation on Linux."
            )
            raise RuntimeError(
                "evdev library not found, cannot use UInputSimulation on Linux."
            )

        self.evdev = evdev
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

    def move_mouse_abs(self, x, y):
        dx = x - self._x
        dy = y - self._y
        self.move_mouse_rel(dx, dy)

    def move_mouse_rel(self, dx, dy):
        self._x += dx
        self._y += dy
        self._device.write(self.evdev.ecodes.EV_REL, self.evdev.ecodes.REL_X, dx)
        self._device.write(self.evdev.ecodes.EV_REL, self.evdev.ecodes.REL_Y, dy)
        self._device.syn()

    def click_mouse(self, button: int, pressed: bool):
        # btn_code = (
        #     self._map_int_to_evdev_button(button) if isinstance(button, int) else None
        # )
        btn_code = hid_to_ecode(button)
        if btn_code:
            self._device.write(self.evdev.ecodes.EV_KEY, btn_code, 1 if pressed else 0)
            self._device.syn()
        else:
            self.logger.warning(f"UInputSimulation: Unknown mouse button: {button}")

    def scroll_mouse(self, dx, dy):
        if dy != 0:
            self._device.write(self.evdev.ecodes.EV_REL, self.evdev.ecodes.REL_WHEEL, -dy)
        if dx != 0:
            self._device.write(self.evdev.ecodes.EV_REL, self.evdev.ecodes.REL_HWHEEL, dx)
        self._device.syn()

    def click_key(self, key: int, pressed: bool):
        key_code = hid_to_ecode(key)
        if key_code:
            self._device.write(self.evdev.ecodes.EV_KEY, key_code, 1 if pressed else 0)
            self._device.syn()
        else:
            self.logger.warning(f"No evdev key found for '{key}'")

    def __del__(self):
        if hasattr(self, "_device") and self._device:
            self._device.close()
