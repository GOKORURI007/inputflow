"""
Tests for coordinate transformation functionality.
"""

import pytest

from inputflow.core.coordinates import CoordinateTransformer


class TestCoordinateTransformer:
    """Test cases for CoordinateTransformer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = CoordinateTransformer()
    
    def test_normalize_coordinates_basic(self):
        """Test basic coordinate normalization."""
        # Test center of 1920x1080 screen
        norm_x, norm_y = self.transformer.normalize_coordinates(960, 540, 1920, 1080)
        assert abs(norm_x - 0.5) < 0.001
        assert abs(norm_y - 0.5) < 0.001
        
        # Test corners
        norm_x, norm_y = self.transformer.normalize_coordinates(0, 0, 1920, 1080)
        assert norm_x == 0.0
        assert norm_y == 0.0
        
        norm_x, norm_y = self.transformer.normalize_coordinates(1919, 1079, 1920, 1080)
        assert norm_x == 1.0
        assert norm_y == 1.0
    
    def test_denormalize_coordinates_basic(self):
        """Test basic coordinate denormalization."""
        # Test center
        x, y = self.transformer.denormalize_coordinates(0.5, 0.5, 1920, 1080)
        assert x == 959  # (1920-1) * 0.5 = 959.5 -> 959
        assert y == 539  # (1080-1) * 0.5 = 539.5 -> 539
        
        # Test corners
        x, y = self.transformer.denormalize_coordinates(0.0, 0.0, 1920, 1080)
        assert x == 0
        assert y == 0
        
        x, y = self.transformer.denormalize_coordinates(1.0, 1.0, 1920, 1080)
        assert x == 1919
        assert y == 1079
    
    def test_coordinate_round_trip(self):
        """Test that normalizing then denormalizing preserves coordinates."""
        test_cases = [
            (0, 0, 1920, 1080),
            (960, 540, 1920, 1080),
            (1919, 1079, 1920, 1080),
            (100, 200, 800, 600),
            (799, 599, 800, 600),
        ]
        
        for x, y, width, height in test_cases:
            norm_x, norm_y = self.transformer.normalize_coordinates(x, y, width, height)
            back_x, back_y = self.transformer.denormalize_coordinates(norm_x, norm_y, width, height)
            
            # Allow for small rounding differences
            assert abs(back_x - x) <= 1, f"X coordinate mismatch: {back_x} != {x}"
            assert abs(back_y - y) <= 1, f"Y coordinate mismatch: {back_y} != {y}"
    
    def test_normalize_coordinates_edge_cases(self):
        """Test coordinate normalization edge cases."""
        # Test coordinates outside screen bounds (should be clamped)
        norm_x, norm_y = self.transformer.normalize_coordinates(-10, -10, 1920, 1080)
        assert norm_x == 0.0
        assert norm_y == 0.0
        
        norm_x, norm_y = self.transformer.normalize_coordinates(2000, 1200, 1920, 1080)
        assert norm_x == 1.0
        assert norm_y == 1.0
        
        # Test single pixel screen
        norm_x, norm_y = self.transformer.normalize_coordinates(0, 0, 1, 1)
        assert norm_x == 0.0
        assert norm_y == 0.0
    
    def test_denormalize_coordinates_edge_cases(self):
        """Test coordinate denormalization edge cases."""
        # Test coordinates outside normalized range (should be clamped)
        x, y = self.transformer.denormalize_coordinates(-0.1, -0.1, 1920, 1080)
        assert x == 0
        assert y == 0
        
        x, y = self.transformer.denormalize_coordinates(1.1, 1.1, 1920, 1080)
        assert x == 1919
        assert y == 1079
        
        # Test single pixel screen
        x, y = self.transformer.denormalize_coordinates(0.5, 0.5, 1, 1)
        assert x == 0
        assert y == 0
    
    def test_invalid_screen_dimensions(self):
        """Test handling of invalid screen dimensions."""
        with pytest.raises(ValueError):
            self.transformer.normalize_coordinates(100, 100, 0, 1080)
        
        with pytest.raises(ValueError):
            self.transformer.normalize_coordinates(100, 100, 1920, 0)
        
        with pytest.raises(ValueError):
            self.transformer.denormalize_coordinates(0.5, 0.5, -1920, 1080)
        
        with pytest.raises(ValueError):
            self.transformer.denormalize_coordinates(0.5, 0.5, 1920, -1080)
    
    def test_get_screen_dimensions(self):
        """Test screen dimension detection."""
        width, height = self.transformer.get_screen_dimensions()
        
        # Should return positive dimensions
        assert width > 0
        assert height > 0
        
        # Should be reasonable screen dimensions
        assert width >= 640  # Minimum reasonable width
        assert height >= 480  # Minimum reasonable height
        assert width <= 7680  # Maximum reasonable width (8K)
        assert height <= 4320  # Maximum reasonable height (8K)
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Get dimensions to populate cache
        self.transformer.get_screen_dimensions()
        assert self.transformer._cached_dimensions is not None
        
        # Clear cache
        self.transformer.clear_cache()
        assert self.transformer._cached_dimensions is None