from pynput import keyboard, mouse
from pynput.keyboard import KeyCode
from pynput.mouse import Button

from inputflow.config.models import Config
from inputflow.input.simulation.base import InputSimulation
from inputflow.keymaps import hid_to_vk


class PynputSimulation(InputSimulation):
    """Input simulation for Windows and macOS using pynput."""

    def __init__(self, logger, config: Config):
        super().__init__(logger=logger, config=config)
        self._mouse = mouse.Controller()
        self._keyboard = keyboard.Controller()

    def move_mouse_abs(self, x, y):
        self._mouse.position = (x, y)

    def move_mouse_rel(self, dx, dy):
        self._mouse.move(dx, dy)

    def click_mouse(self, button: int, pressed: bool):
        pynput_button = hid_to_vk(button)
        if pynput_button:
            if pressed:
                self._mouse.press(Button[pynput_button])
            else:
                self._mouse.release(Button[pynput_button])
        else:
            self.logger.warning(f"PynputSimulation: Unknown mouse button: {button}")

    def scroll_mouse(self, dx, dy):
        self._mouse.scroll(dx, dy)

    def click_key(self, key: int, pressed: bool):
        pynput_key = KeyCode.from_vk(hid_to_vk(key))
        if pynput_key:
            if pressed:
                self._keyboard.press(pynput_key)
            else:
                self._keyboard.release(pynput_key)
        else:
            self.logger.warning(f"PynputSimulation: Unknown key: {key}")
