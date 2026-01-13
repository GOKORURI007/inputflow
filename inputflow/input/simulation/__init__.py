import platform

from .base import InputSimulation
from .linux import UInputSimulation
from .windows import PynputSimulation

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
        try:
            import evdev
        except ImportError as e:
            logger.error(
                "evdev library not found, cannot use UInputSimulation on Linux."
            )
            raise RuntimeError(
                "evdev library not found, cannot use UInputSimulation on Linux."
            )

        return UInputSimulation(logger=logger, config=config)

    else:
        raise NotImplementedError(f"Platform {platform} is not supported.")
