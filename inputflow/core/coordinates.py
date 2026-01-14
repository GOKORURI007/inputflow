from typing import Tuple


class CoordinateTransformer:
    def __init__(self, screen_width: int, screen_height: int):
        if screen_width <= 0 or screen_height <= 0:
            raise ValueError('Screen dimensions must be positive')
        self.screen_width = screen_width
        self.screen_height = screen_height

    def normalize(self, x: int, y: int) -> Tuple[float, float]:
        """Converts absolute pixel coordinates to normalized coordinates (0.0 - 1.0)."""
        norm_x = x / self.screen_width
        norm_y = y / self.screen_height
        # Clamp values to be within [0.0, 1.0]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        return norm_x, norm_y

    def denormalize(self, norm_x: float, norm_y: float) -> Tuple[int, int]:
        """Converts normalized coordinates back to absolute pixel coordinates."""
        x = int(norm_x * self.screen_width)
        y = int(norm_y * self.screen_height)
        # Clamp values to be within the screen bounds
        x = max(0, min(self.screen_width, x))
        y = max(0, min(self.screen_height, y))
        return x, y
