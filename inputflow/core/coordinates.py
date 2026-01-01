"""
Coordinate transformation system for cross-platform input sharing.

This module provides coordinate normalization and denormalization functionality
to handle different screen resolutions and scaling factors across platforms.
"""

import platform
from typing import Tuple


class CoordinateTransformer:
    """
    Handles coordinate transformation between absolute pixels and normalized coordinates.
    
    Provides bidirectional conversion to ensure mouse positioning works correctly
    across heterogeneous display setups with different resolutions and scaling factors.
    """
    
    def __init__(self):
        """Initialize the coordinate transformer."""
        self._cached_dimensions = None
        
    def normalize_coordinates(self, x: int, y: int, screen_width: int, screen_height: int) -> Tuple[float, float]:
        """
        Convert absolute pixel coordinates to normalized coordinates (0.0-1.0 range).
        
        Args:
            x: Absolute X coordinate in pixels
            y: Absolute Y coordinate in pixels
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            
        Returns:
            Tuple of normalized coordinates (norm_x, norm_y) in range [0.0, 1.0]
            
        Requirements: 7.1, 7.2, 7.4, 7.5
        """
        if screen_width <= 0 or screen_height <= 0:
            raise ValueError("Screen dimensions must be positive")
            
        # Clamp coordinates to screen bounds to handle edge cases
        x = max(0, min(x, screen_width - 1))
        y = max(0, min(y, screen_height - 1))
        
        # Convert to normalized coordinates
        norm_x = x / (screen_width - 1) if screen_width > 1 else 0.0
        norm_y = y / (screen_height - 1) if screen_height > 1 else 0.0
        
        # Ensure coordinates are within [0.0, 1.0] range
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        
        return norm_x, norm_y
    
    def denormalize_coordinates(self, norm_x: float, norm_y: float, screen_width: int, screen_height: int) -> Tuple[int, int]:
        """
        Convert normalized coordinates (0.0-1.0 range) back to absolute pixel coordinates.
        
        Args:
            norm_x: Normalized X coordinate in range [0.0, 1.0]
            norm_y: Normalized Y coordinate in range [0.0, 1.0]
            screen_width: Target screen width in pixels
            screen_height: Target screen height in pixels
            
        Returns:
            Tuple of absolute pixel coordinates (x, y)
            
        Requirements: 7.2, 7.3, 7.4, 7.5
        """
        if screen_width <= 0 or screen_height <= 0:
            raise ValueError("Screen dimensions must be positive")
            
        # Clamp normalized coordinates to valid range
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))
        
        # Convert to absolute coordinates
        x = int(norm_x * (screen_width - 1)) if screen_width > 1 else 0
        y = int(norm_y * (screen_height - 1)) if screen_height > 1 else 0
        
        # Ensure coordinates are within screen bounds
        x = max(0, min(x, screen_width - 1))
        y = max(0, min(y, screen_height - 1))
        
        return x, y
    
    def get_screen_dimensions(self) -> Tuple[int, int]:
        """
        Get the current screen dimensions.
        
        Returns:
            Tuple of screen dimensions (width, height) in pixels
            
        Requirements: 7.3
        """
        # Use cached dimensions if available to avoid repeated system calls
        if self._cached_dimensions is not None:
            return self._cached_dimensions
            
        try:
            # Try to get screen dimensions using platform-specific methods
            if platform.system() == "Windows":
                return self._get_windows_screen_dimensions()
            elif platform.system() == "Darwin":  # macOS
                return self._get_macos_screen_dimensions()
            elif platform.system() == "Linux":
                return self._get_linux_screen_dimensions()
            else:
                # Fallback for unknown platforms
                return self._get_fallback_screen_dimensions()
                
        except Exception:
            # If all methods fail, return a reasonable default
            return 1920, 1080
    
    def _get_windows_screen_dimensions(self) -> Tuple[int, int]:
        """Get screen dimensions on Windows."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            
            # Handle high DPI scaling
            try:
                # Try to get DPI awareness
                user32.SetProcessDPIAware()
                # Get actual screen dimensions accounting for DPI scaling
                width = user32.GetSystemMetrics(0)
                height = user32.GetSystemMetrics(1)
            except Exception:
                pass  # Fall back to basic dimensions
                
            self._cached_dimensions = (width, height)
            return width, height
        except Exception:
            raise RuntimeError("Failed to get Windows screen dimensions")
    
    def _get_macos_screen_dimensions(self) -> Tuple[int, int]:
        """Get screen dimensions on macOS."""
        try:
            import subprocess
            import json
            
            # Use system_profiler to get display information
            result = subprocess.run([
                'system_profiler', 'SPDisplaysDataType', '-json'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                displays = data.get('SPDisplaysDataType', [])
                if displays:
                    # Get the main display resolution
                    main_display = displays[0]
                    resolution = main_display.get('_spdisplays_resolution', '')
                    if 'x' in resolution:
                        width_str, height_str = resolution.split(' x ')
                        width = int(width_str)
                        height = int(height_str)
                        self._cached_dimensions = (width, height)
                        return width, height
            
            # Fallback: try using Cocoa if available
            try:
                import Cocoa
                screen = Cocoa.NSScreen.mainScreen()
                frame = screen.frame()
                width = int(frame.size.width)
                height = int(frame.size.height)
                self._cached_dimensions = (width, height)
                return width, height
            except ImportError:
                pass
                
        except Exception:
            pass
            
        raise RuntimeError("Failed to get macOS screen dimensions")
    
    def _get_linux_screen_dimensions(self) -> Tuple[int, int]:
        """Get screen dimensions on Linux."""
        try:
            # Try X11 first
            try:
                import subprocess
                result = subprocess.run([
                    'xrandr', '--current'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if ' connected primary ' in line or ' connected ' in line:
                            # Parse resolution from xrandr output
                            parts = line.split()
                            for part in parts:
                                if 'x' in part and '+' in part:
                                    resolution = part.split('+')[0]
                                    if 'x' in resolution:
                                        width_str, height_str = resolution.split('x')
                                        width = int(width_str)
                                        height = int(height_str)
                                        self._cached_dimensions = (width, height)
                                        return width, height
            except Exception:
                pass
            
            # Try Wayland/wlr-randr for Hyprland
            try:
                import subprocess
                result = subprocess.run([
                    'wlr-randr'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'current' in line and 'x' in line:
                            # Parse resolution from wlr-randr output
                            parts = line.split()
                            for part in parts:
                                if 'x' in part and part.replace('x', '').replace('.', '').isdigit():
                                    width_str, height_str = part.split('x')
                                    width = int(float(width_str))
                                    height = int(float(height_str))
                                    self._cached_dimensions = (width, height)
                                    return width, height
            except Exception:
                pass
                
        except Exception:
            pass
            
        raise RuntimeError("Failed to get Linux screen dimensions")
    
    def _get_fallback_screen_dimensions(self) -> Tuple[int, int]:
        """Fallback method to get screen dimensions."""
        try:
            # Try using tkinter as a last resort
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()  # Hide the window
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            root.destroy()
            self._cached_dimensions = (width, height)
            return width, height
        except Exception:
            pass
            
        # Ultimate fallback
        return 1920, 1080
    
    def clear_cache(self):
        """Clear cached screen dimensions to force re-detection."""
        self._cached_dimensions = None