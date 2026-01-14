from dataclasses import asdict
from typing import Callable

from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button

from inputflow.core.events import (
    EventType,
    InputEvent,
    KeyboardEvent,
    MouseClickEvent,
)

from ...keymaps import hid_to_name, hid_to_vk, name_to_hid, vk_to_hid
from .base import InputCapture


class HotKeyManager(keyboard.GlobalHotKeys):
    def __init__(self, hotkeys: list[keyboard.HotKey], *args, **kwargs):
        super().__init__(hotkeys={}, *args, **kwargs)
        self._hotkeys = hotkeys
        super(keyboard.GlobalHotKeys, self).__init__(
            on_press=self._on_press, on_release=self._on_release, *args, **kwargs
        )

    @staticmethod
    def _get_standard_key(key):
        """
        将所有传入的 key 转换为只包含 VK 信息的 KeyCode 对象，
        确保与初始化时使用的 KeyCode.from_vk(...) 能够匹配。
        """
        if isinstance(key, KeyCode):
            # 如果是普通的 KeyCode，提取其 VK
            return KeyCode.from_vk(key.vk)
        if isinstance(key, Key):
            # 如果是特殊键 (Ctrl, Alt 等)，pynput 也会分配对应的 VK
            return KeyCode.from_vk(key.value.vk if hasattr(key.value, 'vk') else key.value)
        return key

    def _on_press(self, key):
        # 转换传入的 key，确保其能匹配到 HotKey 集合中的 KeyCode.from_vk
        std_key = self._get_standard_key(key)
        for hotkey in self._hotkeys:
            hotkey.press(std_key)

    def _on_release(self, key):
        std_key = self._get_standard_key(key)
        for hotkey in self._hotkeys:
            hotkey.release(std_key)


class PynputCapture(InputCapture):
    """Input capture for Windows and macOS using pynput."""

    def __init__(
        self,
        logger,
        config,
        event_callback: Callable[[InputEvent], None],
        hotkey_callback: Callable[[str], None] = None,
        **kwargs,
    ):
        super().__init__(
            logger=logger,
            config=config,
            event_callback=event_callback,
            hotkey_callback=hotkey_callback,
            **kwargs,
        )

        def pynput_on_press(key):
            self.on_key_event(key, True)  # Pass key object for conversion in super

        def pynput_on_release(key):
            self.on_key_event(key, False)  # Pass key object for conversion in super

        self._mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_scroll=self.on_mouse_scroll,
            on_click=self.on_mouse_click,
        )
        self._keyboard_listener = keyboard.Listener(on_press=pynput_on_press, on_release=pynput_on_release)

        self._hotkey_listener = None
        if self.hotkey_callback:
            shortcuts = asdict(self.config.shortcuts)
            hotkeys = [
                keyboard.HotKey(
                    [KeyCode.from_vk(hid_to_vk(name_to_hid(key_name.strip()))) for key_name in v.split('+')],
                    lambda: self.hotkey_callback(k),
                )
                for k, v in shortcuts.items()
            ]
            self._hotkey_listener = HotKeyManager(hotkeys)

        self._monitoring = False

    def start_monitoring(self):
        if not self._monitoring:
            self._mouse_listener.start()
            self._keyboard_listener.start()
            if self._hotkey_listener:
                self._hotkey_listener.start()
            self._monitoring = True
            self.logger.info('PynputCapture: Started monitoring.')

    def stop_monitoring(self):
        if self._monitoring:
            self._mouse_listener.stop()
            self._keyboard_listener.stop()
            if self._hotkey_listener:
                self._hotkey_listener.stop()
            self._monitoring = False
            self.logger.info('PynputCapture: Stopped monitoring.')

    def on_mouse_click(self, x: int, y: int, button: Button, pressed: bool):
        normalized_x, normalized_y = self.coord_transformer.normalize(x, y)
        if not isinstance(button, Button):
            self.logger.warning(f'Unknown mouse button type for capture: {button}')
        button_value = vk_to_hid(button.name)
        event_data = MouseClickEvent(
            button=button_value,
            pressed=pressed,
            normalized_x=normalized_x,
            normalized_y=normalized_y,
        )
        self.event_callback(InputEvent(event_type=EventType.MOUSE_CLICK, data=event_data))
        self.logger.debug(
            f'Mouse {"pressed" if pressed else "released"} button {hid_to_name(button_value)}:{button_value} at ({x}, {y})'
        )

    def on_key_event(self, key: Key, pressed: bool):
        key_value: int

        if hasattr(key, 'value'):
            key_value = vk_to_hid(key.value.vk)
        else:
            key_value = vk_to_hid(key.vk)

        event_data = KeyboardEvent(key_code=key_value, pressed=pressed)
        self.event_callback(InputEvent(event_type=EventType.KEYBOARD, data=event_data))
        self.logger.debug(f'Key {str(hid_to_name(key_value))}:{key_value} {"pressed" if pressed else "released"}')
