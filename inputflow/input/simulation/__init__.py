import platform
from .base import InputSimulation
from .windows import PynputSimulation
from .linux import UInputSimulation

__all__ = [InputSimulation, PynputSimulation, UInputSimulation]

from inputflow.config.models import Config


def get_input_simulation(logger, config: Config) -> InputSimulation:
    """
    Factory function to get the appropriate input simulation implementation
    for the current platform.
    """
    if platform.system() in ("Windows", "Darwin"):
        return PynputSimulation(logger=logger, config=config)
    elif platform.system() == "Linux":
        import evdev
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