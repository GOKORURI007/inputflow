import platform
from typing import Callable

from inputflow.config.models import Config
from inputflow.core.events import InputEvent
from .base import InputCapture
from .linux import EvdevCapture
from .windows import PynputCapture

__all__ = [InputCapture, EvdevCapture, PynputCapture]


def get_input_capture(
    logger,
    config: Config,
    event_callback: Callable[[InputEvent], None] = lambda _: ...,
    hotkey_callback: Callable[[str], None] = None,
    **kwargs,
) -> InputCapture:
    """
    Factory function to get the appropriate input capture implementation
    for the current platform.
    """
    if platform.system() == "Windows" or platform.system() == "Darwin":
        return PynputCapture(
            logger=logger,
            config=config,
            event_callback=event_callback,
            hotkey_callback=hotkey_callback,
            **kwargs,
        )
    elif platform.system() == "Linux":
        # evdev is a better choice for linux, especially for Wayland.
        # but pynput also has a linux implementation that can be a fallback.
        try:
            return EvdevCapture(
                logger=logger,
                config=config,
                event_callback=event_callback,
                hotkey_callback=hotkey_callback,
                **kwargs,
            )
        except ImportError:
            logger.warning("evdev library not found, falling back to pynput on Linux.")
            return PynputCapture(
                logger=logger,
                config=config,
                event_callback=event_callback,
                hotkey_callback=hotkey_callback,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Failed to initialize EvdevCapture: {e}")
            logger.warning("Falling back to pynput on Linux.")
            return PynputCapture(
                logger=logger,
                config=config,
                event_callback=event_callback,
                hotkey_callback=hotkey_callback,
                **kwargs,
            )
    else:
        raise NotImplementedError(f"Platform {platform} is not supported.")
