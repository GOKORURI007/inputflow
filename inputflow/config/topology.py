"""Topology management for screen relationships and edge detection."""

from enum import Enum
from typing import List, Optional, Tuple

from loguru import logger

from .models import TopologyEntry


class Direction(Enum):
    """Screen switching directions."""

    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"


class TopologyManager:
    """Manages screen relationships and handles edge-based screen switching."""

    def __init__(self):
        """Initialize TopologyManager."""
        self._topology: List[TopologyEntry] = []
        self._current_ip: Optional[str] = None
        self._screen_width: int = 1920
        self._screen_height: int = 1080
        self._edge_threshold: int = 5  # pixels from edge to trigger switching

    def load_topology(
        self, topology_entries: List[TopologyEntry], current_ip: str
    ) -> None:
        """Load topology configuration."""
        self._topology = topology_entries
        self._current_ip = current_ip
        logger.info(
            f"Loaded topology with {len(topology_entries)} entries for IP {current_ip}"
        )

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """Set current screen dimensions for edge detection."""
        self._screen_width = width
        self._screen_height = height
        logger.debug(f"Screen dimensions set to {width}x{height}")

    def set_edge_threshold(self, threshold: int) -> None:
        """Set edge threshold in pixels."""
        self._edge_threshold = threshold
        logger.debug(f"Edge threshold set to {threshold} pixels")

    def get_target_for_direction(self, direction: Direction) -> Optional[str]:
        """Get the target IP for a given direction from current screen."""
        if not self._current_ip:
            logger.warning("Current IP not set, cannot determine target")
            return None

        current_entry = self._get_current_topology_entry()
        if not current_entry:
            logger.warning(f"No topology entry found for current IP {self._current_ip}")
            return None

        target = current_entry.get_direction_target(direction.value)
        if target:
            logger.debug(f"Target for direction {direction.value}: {target}")
        else:
            logger.debug(f"No target configured for direction {direction.value}")

        return target

    def is_at_edge(self, x: int, y: int, direction: Direction) -> bool:
        """Check if coordinates are at the specified edge of the screen."""
        threshold = self._edge_threshold

        if direction == Direction.LEFT:
            return x <= threshold
        elif direction == Direction.RIGHT:
            return x >= (self._screen_width - threshold)
        elif direction == Direction.UP:
            return y <= threshold
        elif direction == Direction.DOWN:
            return y >= (self._screen_height - threshold)

        return False

    def should_switch_screen(self, x: int, y: int) -> Optional[str]:
        """
        Determine if screen switching should occur based on mouse position.
        Returns target IP if switching should occur, None otherwise.
        """
        if not self._current_ip:
            return None

        # Check each direction for edge penetration
        for direction in Direction:
            if self.is_at_edge(x, y, direction):
                target = self.get_target_for_direction(direction)
                if target:
                    logger.info(
                        f"Screen switch triggered: {direction.value} to {target}"
                    )
                    return target

        return None

    def get_edge_coordinates_for_direction(
        self, direction: Direction
    ) -> Tuple[int, int]:
        """Get the coordinates where the cursor should appear on the target screen."""
        if direction == Direction.LEFT:
            # Coming from right edge, appear on left edge
            return (self._screen_width - self._edge_threshold, self._screen_height // 2)
        elif direction == Direction.RIGHT:
            # Coming from left edge, appear on right edge
            return (self._edge_threshold, self._screen_height // 2)
        elif direction == Direction.UP:
            # Coming from bottom edge, appear on top edge
            return (self._screen_width // 2, self._screen_height - self._edge_threshold)
        elif direction == Direction.DOWN:
            # Coming from top edge, appear on bottom edge
            return (self._screen_width // 2, self._edge_threshold)

        return (self._screen_width // 2, self._screen_height // 2)

    def get_all_targets(self) -> List[str]:
        """Get all configured target IPs from current topology entry."""
        current_entry = self._get_current_topology_entry()
        if not current_entry:
            return []

        targets = []
        for direction in Direction:
            target = current_entry.get_direction_target(direction.value)
            if target and target not in targets:
                targets.append(target)

        return targets

    def _get_current_topology_entry(self) -> Optional[TopologyEntry]:
        """Get the topology entry for the current IP."""
        if not self._current_ip:
            return None

        for entry in self._topology:
            if entry.self_ip == self._current_ip:
                return entry

        return None

    def validate_topology(self) -> bool:
        """Validate the loaded topology configuration."""
        if not self._topology:
            logger.error("No topology entries loaded")
            return False

        if not self._current_ip:
            logger.error("Current IP not set")
            return False

        current_entry = self._get_current_topology_entry()
        if not current_entry:
            logger.error(f"No topology entry found for current IP {self._current_ip}")
            return False

        # Check if at least one direction is configured
        has_direction = any(
            [
                current_entry.left,
                current_entry.right,
                current_entry.up,
                current_entry.down,
            ]
        )

        if not has_direction:
            logger.warning(
                f"No directional relationships configured for IP {self._current_ip}"
            )

        logger.info("Topology validation passed")
        return True
