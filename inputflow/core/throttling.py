"""Event throttling system for performance optimization."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from inputflow.core.events import EventType, InputEvent
from inputflow.core.logging import get_logger

logger = get_logger(__name__)


class ThrottleMode(Enum):
    """Throttling modes for different event types."""
    NONE = "none"
    TIME_BASED = "time_based"
    DISTANCE_BASED = "distance_based"
    ADAPTIVE = "adaptive"


@dataclass
class ThrottleConfig:
    """Configuration for event throttling."""
    # Time-based throttling (microseconds)
    min_interval_us: int = 1000  # 1ms default
    
    # Distance-based throttling for mouse movement
    min_distance_pixels: float = 1.0
    
    # Adaptive throttling parameters
    high_frequency_threshold: int = 100  # events per second
    adaptive_multiplier: float = 2.0
    
    # Per-event-type configuration
    mouse_move_mode: ThrottleMode = ThrottleMode.TIME_BASED
    mouse_click_mode: ThrottleMode = ThrottleMode.NONE
    mouse_scroll_mode: ThrottleMode = ThrottleMode.TIME_BASED
    keyboard_mode: ThrottleMode = ThrottleMode.NONE


class EventThrottler:
    """
    Event throttling system to optimize performance for high-frequency events.
    
    Provides microsecond-level throttling for mouse movement events while
    maintaining accuracy and reducing network transmission rate.
    """
    
    def __init__(self, config: Optional[ThrottleConfig] = None):
        self._config = config or ThrottleConfig()
        
        # Track last event times per event type
        self._last_event_times: Dict[EventType, float] = {}
        
        # Track last mouse position for distance-based throttling
        self._last_mouse_x: Optional[float] = None
        self._last_mouse_y: Optional[float] = None
        
        # Adaptive throttling state
        self._event_counts: Dict[EventType, int] = {}
        self._last_count_reset: float = time.time()
        self._adaptive_multipliers: Dict[EventType, float] = {}
        
        logger.info(f"Event throttler initialized with config: {self._config}")
    
    def should_process_event(self, event: InputEvent) -> bool:
        """
        Determine if an event should be processed based on throttling rules.
        
        Args:
            event: The input event to check
            
        Returns:
            bool: True if the event should be processed, False if it should be throttled
        """
        current_time = time.time()
        event_type = event.event_type
        
        # Update event counts for adaptive throttling
        self._update_event_counts(event_type, current_time)
        
        # Get throttling mode for this event type
        throttle_mode = self._get_throttle_mode(event_type)
        
        if throttle_mode == ThrottleMode.NONE:
            return True
        
        # Check time-based throttling
        if throttle_mode in [ThrottleMode.TIME_BASED, ThrottleMode.ADAPTIVE]:
            if not self._check_time_throttle(event_type, current_time):
                logger.debug(f"Event {event_type} throttled by time")
                return False
        
        # Check distance-based throttling for mouse movement
        if (throttle_mode == ThrottleMode.DISTANCE_BASED and 
            event_type == EventType.MOUSE_MOVE):
            if not self._check_distance_throttle(event):
                logger.debug(f"Mouse move event throttled by distance")
                return False
        
        # Update last event time
        self._last_event_times[event_type] = current_time
        
        # Update last mouse position for distance tracking
        if event_type == EventType.MOUSE_MOVE:
            self._update_last_mouse_position(event)
        
        return True
    
    def _get_throttle_mode(self, event_type: EventType) -> ThrottleMode:
        """Get the throttling mode for a specific event type."""
        mode_map = {
            EventType.MOUSE_MOVE: self._config.mouse_move_mode,
            EventType.MOUSE_CLICK: self._config.mouse_click_mode,
            EventType.MOUSE_SCROLL: self._config.mouse_scroll_mode,
            EventType.KEYBOARD: self._config.keyboard_mode,
        }
        return mode_map.get(event_type, ThrottleMode.NONE)
    
    def _check_time_throttle(self, event_type: EventType, current_time: float) -> bool:
        """
        Check if enough time has passed since the last event of this type.
        
        Args:
            event_type: The type of event to check
            current_time: Current timestamp in seconds
            
        Returns:
            bool: True if the event should be processed
        """
        last_time = self._last_event_times.get(event_type, 0)
        
        # Calculate minimum interval (convert microseconds to seconds)
        min_interval = self._config.min_interval_us / 1_000_000
        
        # Apply adaptive multiplier if enabled
        if self._get_throttle_mode(event_type) == ThrottleMode.ADAPTIVE:
            multiplier = self._adaptive_multipliers.get(event_type, 1.0)
            min_interval *= multiplier
        
        time_since_last = current_time - last_time
        return time_since_last >= min_interval
    
    def _check_distance_throttle(self, event: InputEvent) -> bool:
        """
        Check if the mouse has moved far enough to warrant processing.
        
        Args:
            event: Mouse movement event
            
        Returns:
            bool: True if the event should be processed
        """
        if event.event_type != EventType.MOUSE_MOVE:
            return True
        
        if self._last_mouse_x is None or self._last_mouse_y is None:
            return True
        
        # Calculate distance moved
        data = event.data
        dx = abs(data.normalized_x - self._last_mouse_x)
        dy = abs(data.normalized_y - self._last_mouse_y)
        distance = (dx * dx + dy * dy) ** 0.5
        
        # Convert normalized distance to approximate pixel distance
        # This is a rough approximation - in practice you'd use actual screen dimensions
        pixel_distance = distance * 1920  # Assume 1920px width for approximation
        
        return pixel_distance >= self._config.min_distance_pixels
    
    def _update_last_mouse_position(self, event: InputEvent) -> None:
        """Update the last known mouse position."""
        if event.event_type == EventType.MOUSE_MOVE:
            data = event.data
            self._last_mouse_x = data.normalized_x
            self._last_mouse_y = data.normalized_y
    
    def _update_event_counts(self, event_type: EventType, current_time: float) -> None:
        """
        Update event counts for adaptive throttling.
        
        Args:
            event_type: The type of event
            current_time: Current timestamp
        """
        # Reset counts every second
        if current_time - self._last_count_reset >= 1.0:
            self._calculate_adaptive_multipliers()
            self._event_counts.clear()
            self._last_count_reset = current_time
        
        # Increment count for this event type
        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1
    
    def _calculate_adaptive_multipliers(self) -> None:
        """Calculate adaptive throttling multipliers based on event frequency."""
        for event_type, count in self._event_counts.items():
            if count > self._config.high_frequency_threshold:
                # Increase throttling for high-frequency events
                multiplier = min(
                    self._config.adaptive_multiplier,
                    count / self._config.high_frequency_threshold
                )
                self._adaptive_multipliers[event_type] = multiplier
                logger.debug(f"Adaptive throttling: {event_type} multiplier = {multiplier}")
            else:
                # Reset multiplier for normal frequency events
                self._adaptive_multipliers[event_type] = 1.0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get throttling statistics.
        
        Returns:
            Dict containing throttling statistics
        """
        return {
            "config": self._config,
            "last_event_times": self._last_event_times.copy(),
            "event_counts": self._event_counts.copy(),
            "adaptive_multipliers": self._adaptive_multipliers.copy(),
            "last_mouse_position": (self._last_mouse_x, self._last_mouse_y),
        }
    
    def reset(self) -> None:
        """Reset all throttling state."""
        self._last_event_times.clear()
        self._last_mouse_x = None
        self._last_mouse_y = None
        self._event_counts.clear()
        self._adaptive_multipliers.clear()
        self._last_count_reset = time.time()
        logger.info("Event throttler state reset")


class ThrottledEventProcessor:
    """
    Event processor that applies throttling before processing events.
    
    This class wraps an event processing function and applies throttling
    to reduce the rate of high-frequency events.
    """
    
    def __init__(self, processor_func, throttle_config: Optional[ThrottleConfig] = None):
        """
        Initialize the throttled event processor.
        
        Args:
            processor_func: Function to call for processing events
            throttle_config: Throttling configuration
        """
        self._processor_func = processor_func
        self._throttler = EventThrottler(throttle_config)
        self._processed_count = 0
        self._throttled_count = 0
    
    def process_event(self, event: InputEvent) -> bool:
        """
        Process an event with throttling applied.
        
        Args:
            event: The input event to process
            
        Returns:
            bool: True if the event was processed, False if throttled
        """
        if self._throttler.should_process_event(event):
            self._processor_func(event)
            self._processed_count += 1
            return True
        else:
            self._throttled_count += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        throttler_stats = self._throttler.get_stats()
        return {
            "processed_count": self._processed_count,
            "throttled_count": self._throttled_count,
            "throttle_ratio": (
                self._throttled_count / (self._processed_count + self._throttled_count)
                if (self._processed_count + self._throttled_count) > 0 else 0
            ),
            "throttler": throttler_stats,
        }
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self._processed_count = 0
        self._throttled_count = 0
        self._throttler.reset()