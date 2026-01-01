"""Base classes for input capture and simulation."""

from abc import ABC, abstractmethod
from typing import Callable, Optional

from inputflow.core.events import InputEvent


class InputCapture(ABC):
    """Abstract base class for input capture implementations."""
    
    def __init__(self):
        self._event_callback: Optional[Callable[[InputEvent], None]] = None
        self._is_monitoring = False
    
    def set_event_callback(self, callback: Callable[[InputEvent], None]) -> None:
        """
        Set the callback function for captured input events.
        
        Args:
            callback: Function to call when an input event is captured
        """
        self._event_callback = callback
    
    @abstractmethod
    def start_monitoring(self) -> None:
        """Start monitoring for input events."""
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop monitoring for input events."""
        pass
    
    @property
    def is_monitoring(self) -> bool:
        """Check if currently monitoring input events."""
        return self._is_monitoring
    
    def _emit_event(self, event: InputEvent) -> None:
        """
        Emit an input event to the registered callback.
        
        Args:
            event: The input event to emit
        """
        if self._event_callback:
            self._event_callback(event)


class InputSimulation(ABC):
    """Abstract base class for input simulation implementations."""
    
    @abstractmethod
    def simulate_event(self, event: InputEvent) -> bool:
        """
        Simulate an input event.
        
        Args:
            event: The input event to simulate
            
        Returns:
            bool: True if event was processed, False if throttled
        """
        pass
    
    @abstractmethod
    def move_mouse(self, x: int, y: int) -> None:
        """
        Move the mouse cursor to the specified position.
        
        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
        """
        pass
    
    @abstractmethod
    def click_mouse(self, button: str, pressed: bool, x: int, y: int) -> None:
        """
        Simulate a mouse click.
        
        Args:
            button: Mouse button identifier
            pressed: True for press, False for release
            x: X coordinate in pixels
            y: Y coordinate in pixels
        """
        pass
    
    @abstractmethod
    def scroll_mouse(self, dx: int, dy: int) -> None:
        """
        Simulate mouse scroll.
        
        Args:
            dx: Horizontal scroll delta
            dy: Vertical scroll delta
        """
        pass
    
    @abstractmethod
    def press_key(self, key_code: int, pressed: bool) -> None:
        """
        Simulate a key press or release.
        
        Args:
            key_code: Key code to simulate
            pressed: True for press, False for release
        """
        pass