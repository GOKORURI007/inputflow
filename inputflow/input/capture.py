import abc
import select
import sys
import time
from threading import Event, Thread


class InputCapture(abc.ABC):
    """
    An abstract base class for input capturing.
    """

    def __init__(self, move_throttle_ms=16):
        self._move_throttle_sec = move_throttle_ms / 1000.0
        self._last_move_time = 0

    @abc.abstractmethod
    def start_monitoring(self):
        """Starts monitoring input events."""
        pass

    @abc.abstractmethod
    def stop_monitoring(self):
        """Stops monitoring input events."""
        pass

    def on_mouse_move(self, x, y):
        current_time = time.time()
        if current_time - self._last_move_time < self._move_throttle_sec:
            return
        self._last_move_time = current_time
        print(f"Mouse moved to ({x}, {y})")

    def on_mouse_click(self, x, y, button, pressed):
        print(
            f"Mouse {'pressed' if pressed else 'released'} button {button} at ({x}, {y})"
        )

    def on_mouse_scroll(self, x, y, dx, dy):
        print(f"Mouse scrolled at ({x}, {y}) with delta ({dx}, {dy})")

    def on_key_event(self, key, pressed):
        print(f"Key {key} {'pressed' if pressed else 'released'}")


class PynputCapture(InputCapture):
    """Input capture for Windows and macOS using pynput."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from pynput import keyboard, mouse

        self._mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll,
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._monitoring = False

    def _on_press(self, key):
        self.on_key_event(key, True)

    def _on_release(self, key):
        self.on_key_event(key, False)

    def start_monitoring(self):
        if not self._monitoring:
            self._mouse_listener.start()
            self._keyboard_listener.start()
            self._monitoring = True
            print("PynputCapture: Started monitoring.")

    def stop_monitoring(self):
        if self._monitoring:
            self._mouse_listener.stop()
            self._keyboard_listener.stop()
            self._monitoring = False
            print("PynputCapture: Stopped monitoring.")


class EvdevCapture(InputCapture):
    """Input capture for Linux using evdev."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import evdev

        self.evdev = evdev
        self._stop_event = Event()
        self._thread = None
        self._devices = []
        self._x, self._y = 0, 0  # Internal cursor position

    def _discover_devices(self):
        try:
            device_paths = self.evdev.list_devices()
        except Exception as e:
            print(f"EvdevCapture: Could not list devices: {e}")
            return

        for path in device_paths:
            try:
                device = self.evdev.InputDevice(path)
                capabilities = device.capabilities(verbose=False)
                # It's a keyboard if it has keys
                has_keys = self.evdev.ecodes.EV_KEY in capabilities
                # It's a mouse if it has relative X and Y axes
                has_rel_xy = (
                    self.evdev.ecodes.EV_REL in capabilities
                    and self.evdev.ecodes.REL_X in capabilities[self.evdev.ecodes.EV_REL]
                    and self.evdev.ecodes.REL_Y in capabilities[self.evdev.ecodes.EV_REL]
                )

                if has_keys or has_rel_xy:
                    self._devices.append(device)
                    print(f"EvdevCapture: Monitoring device: {device.name} at {path}")

            except (IOError, PermissionError):
                # This can happen if we don't have read permission.
                # print(f"EvdevCapture: No permissions to read {path}. Try running as root.")
                pass # Suppressing output for non-readable devices to avoid spam.

        if not self._devices:
            print("EvdevCapture: No suitable input devices found or permission denied. Try running as root.")

    def _monitor(self):
        print("EvdevCapture: Monitoring thread started.")
        fds = {dev.fd: dev for dev in self._devices}

        rel_dx, rel_dy = 0, 0
        scroll_dx, scroll_dy = 0, 0

        while not self._stop_event.is_set():
            try:
                r, w, x = select.select(fds, [], [], 0.1)
                if not r:
                    continue

                for fd in r:
                    device = fds[fd]
                    for event in device.read():
                        if event.type == self.evdev.ecodes.EV_SYN:
                            if rel_dx != 0 or rel_dy != 0:
                                self._x += rel_dx
                                self._y += rel_dy
                                self.on_mouse_move(self._x, self._y)
                                rel_dx, rel_dy = 0, 0
                            if scroll_dx != 0 or scroll_dy != 0:
                                self.on_mouse_scroll(
                                    self._x, self._y, scroll_dx, scroll_dy
                                )
                                scroll_dx, scroll_dy = 0, 0

                        elif event.type == self.evdev.ecodes.EV_REL:
                            if event.code == self.evdev.ecodes.REL_X:
                                rel_dx += event.value
                            elif event.code == self.evdev.ecodes.REL_Y:
                                rel_dy += event.value
                            elif event.code == self.evdev.ecodes.REL_WHEEL:
                                scroll_dy += event.value
                            elif event.code == self.evdev.ecodes.REL_HWHEEL:
                                scroll_dx += event.value

                        elif event.type == self.evdev.ecodes.EV_KEY:
                            key_event = self.evdev.categorize(event)
                            is_pressed = (
                                event.value == 1
                            )  # 1 for press, 0 for release, 2 for repeat

                            # Distinguish between mouse buttons and keyboard keys
                            if "BTN_" in key_event.keycode:
                                self.on_mouse_click(
                                    self._x, self._y, key_event.keycode, is_pressed
                                )
                            else:
                                self.on_key_event(key_event.keycode, is_pressed)

            except Exception as e:
                print(f"EvdevCapture: Error in monitoring loop: {e}")
                break

        print("EvdevCapture: Monitoring thread stopped.")

    def start_monitoring(self):
        print("EvdevCapture: Starting monitoring...")
        print("NOTE: evdev requires running as root or user in the 'input' group.")

        # Discover devices in the main thread before starting the monitor thread
        try:
            self._discover_devices()
        except Exception as e:
            print(f"EvdevCapture: Failed to discover devices: {e}")
            return

        if not self._devices:
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._monitor)
        self._thread.start()

    def stop_monitoring(self):
        print("EvdevCapture: Stopping monitoring...")
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None

        for device in self._devices:
            try:
                device.close()
            except Exception as e:
                print(f"EvdevCapture: Error while closing device {device.path}: {e}")
        self._devices = []


def get_input_capture(**kwargs) -> InputCapture:
    """
    Factory function to get the appropriate input capture implementation
    for the current platform.
    """
    platform = sys.platform
    if platform == "win32" or platform == "darwin":
        return PynputCapture(**kwargs)
    elif platform.startswith("linux"):
        # evdev is a better choice for linux, especially for Wayland.
        # but pynput also has a linux implementation that can be a fallback.
        try:
            import evdev

            return EvdevCapture(**kwargs)
        except ImportError:
            print("evdev library not found, falling back to pynput on Linux.")
            return PynputCapture(**kwargs)
        except Exception as e:
            print(f"Failed to initialize EvdevCapture: {e}")
            print("Falling back to pynput on Linux.")
            return PynputCapture(**kwargs)
    else:
        raise NotImplementedError(f"Platform {platform} is not supported.")
