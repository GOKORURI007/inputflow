from typing import Callable

from pynput import keyboard

from inputflow.core.logging import get_logger

logger = get_logger(__name__)


class HotkeyManager:
    def __init__(self, shortcuts: dict[str, str], on_hotkey: Callable[[str], None]):
        self.shortcuts = shortcuts
        self.on_hotkey = on_hotkey
        self._hotkey_listener = None

    def start(self):
        logger.info("Starting hotkey listener.")
        try:
            self._hotkey_listener = keyboard.GlobalHotKeys(
                {
                    self.shortcuts[
                        "switch_loop_between_screens"
                    ]: lambda: self.on_hotkey("switch_loop_between_screens")
                }
            )
            self._hotkey_listener.start()
        except Exception as e:
            logger.error(f"Failed to start hotkey listener: {e}")
            raise

    def stop(self):
        if self._hotkey_listener:
            logger.info("Stopping hotkey listener.")
            self._hotkey_listener.stop()
            self._hotkey_listener = None
