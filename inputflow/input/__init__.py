"""Input capture and simulation components for InputFlow."""

from .base import InputCapture, InputSimulation
from .platform import Platform, PlatformDetector, PlatformFactory

__all__ = [
    'PlatformDetector',
    'PlatformFactory', 
    'Platform',
    'InputCapture',
    'InputSimulation',
]