"""Tests for platform detection and factory functionality."""

import os
from unittest.mock import MagicMock, patch

import pytest

from inputflow.core.exceptions import PlatformError
from inputflow.input import Platform, PlatformDetector, PlatformFactory


class TestPlatformDetector:
    """Test platform detection functionality."""
    
    def test_detect_windows(self):
        """Test Windows platform detection."""
        with patch('platform.system', return_value='Windows'):
            detected = PlatformDetector.detect_platform()
            assert detected == Platform.WINDOWS
    
    def test_detect_macos(self):
        """Test macOS platform detection."""
        with patch('platform.system', return_value='Darwin'):
            detected = PlatformDetector.detect_platform()
            assert detected == Platform.MACOS
    
    def test_detect_linux_wayland(self):
        """Test Linux with Wayland detection."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0'}):
                detected = PlatformDetector.detect_platform()
                assert detected == Platform.LINUX_WAYLAND
    
    def test_detect_linux_hyprland(self):
        """Test Linux with Hyprland detection."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': 'test'}):
                detected = PlatformDetector.detect_platform()
                assert detected == Platform.LINUX_WAYLAND
    
    def test_detect_linux_x11(self):
        """Test Linux with X11 detection."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {'DISPLAY': ':0'}, clear=True):
                detected = PlatformDetector.detect_platform()
                assert detected == Platform.LINUX_X11
    
    def test_detect_linux_default_x11(self):
        """Test Linux defaults to X11 when display server is unclear."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {}, clear=True):
                detected = PlatformDetector.detect_platform()
                assert detected == Platform.LINUX_X11
    
    def test_unsupported_platform(self):
        """Test unsupported platform raises error."""
        with patch('platform.system', return_value='FreeBSD'):
            with pytest.raises(PlatformError, match="Unsupported platform"):
                PlatformDetector.detect_platform()
    
    def test_is_wayland(self):
        """Test Wayland detection helper."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0'}):
                assert PlatformDetector.is_wayland() is True
        
        with patch('platform.system', return_value='Windows'):
            assert PlatformDetector.is_wayland() is False
    
    def test_is_hyprland(self):
        """Test Hyprland detection helper."""
        with patch.dict(os.environ, {'HYPRLAND_INSTANCE_SIGNATURE': 'test'}):
            assert PlatformDetector.is_hyprland() is True
        
        with patch.dict(os.environ, {}, clear=True):
            assert PlatformDetector.is_hyprland() is False


class TestPlatformFactory:
    """Test platform factory functionality."""
    
    def test_factory_initialization(self):
        """Test factory initializes with detected platform."""
        with patch('platform.system', return_value='Windows'):
            factory = PlatformFactory()
            assert factory.platform == Platform.WINDOWS
    
    def test_create_input_capture_windows(self):
        """Test creating input capture on Windows."""
        with patch('platform.system', return_value='Windows'):
            factory = PlatformFactory()
            
            # Mock the pynput import to avoid dependency issues in tests
            with patch('inputflow.input.capture.pynput_capture.PYNPUT_AVAILABLE', True):
                with patch('inputflow.input.capture.pynput_capture.PynputInputCapture') as mock_capture:
                    mock_instance = MagicMock()
                    mock_capture.return_value = mock_instance
                    
                    capture = factory.create_input_capture()
                    assert capture == mock_instance
                    mock_capture.assert_called_once()
    
    def test_permissions_check_windows(self):
        """Test permission checking on Windows (should always return True)."""
        with patch('platform.system', return_value='Windows'):
            factory = PlatformFactory()
            assert factory.check_permissions() is True
    
    def test_permissions_check_linux(self):
        """Test permission checking on Linux."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {'DISPLAY': ':0'}):
                factory = PlatformFactory()
                
                # Test with good permissions
                with patch('os.access', return_value=True):
                    assert factory.check_permissions() is True
                
                # Test with bad permissions
                with patch('os.access', return_value=False):
                    assert factory.check_permissions() is False
    
    def test_permission_instructions_linux(self):
        """Test getting permission instructions for Linux."""
        with patch('platform.system', return_value='Linux'):
            with patch.dict(os.environ, {'DISPLAY': ':0'}):
                factory = PlatformFactory()
                
                # Test with bad permissions
                with patch('os.access', return_value=False):
                    instructions = factory.get_permission_instructions()
                    assert instructions is not None
                    assert "input" in instructions
                    assert "usermod" in instructions
                
                # Test with good permissions
                with patch('os.access', return_value=True):
                    instructions = factory.get_permission_instructions()
                    assert instructions is None