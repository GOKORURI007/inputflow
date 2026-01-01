"""Hotkey controller for global hotkey management and system control."""

import threading
from enum import Enum
from typing import Callable, Dict, Optional, Set

from loguru import logger
from pynput import keyboard

from inputflow.config.models import HotkeyConfig
from inputflow.core.exceptions import PlatformError


class HotkeyState(Enum):
    """Hotkey system states."""
    NORMAL = "normal"
    LOCKED = "locked"


class HotkeyController:
    """
    Manages global hotkeys for system control.
    
    Provides lock mode toggle functionality and screen cycling capabilities
    with configurable hotkey combinations from TOML configuration.
    """
    
    def __init__(self, hotkey_config: HotkeyConfig):
        """
        Initialize HotkeyController with configuration.
        
        Args:
            hotkey_config: Hotkey configuration from TOML
        """
        self.config = hotkey_config
        self._state = HotkeyState.NORMAL
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._lock = threading.Lock()
        self._callbacks: Dict[str, Callable] = {}
        self._registered_hotkeys: Set[str] = set()
        
        logger.info(f"HotkeyController initialized with lock hotkey: {self.config.switch_lock}, "
                   f"loop hotkey: {self.config.switch_loop_between_screens}")
    
    def register_hotkeys(self, hotkeys: Dict[str, Callable]) -> None:
        """
        Register global hotkeys with their callback functions.
        
        Args:
            hotkeys: Dictionary mapping hotkey names to callback functions
                    Expected keys: 'lock_toggle', 'screen_cycle'
        """
        self._callbacks = hotkeys.copy()
        
        # Create hotkey mapping for pynput
        hotkey_mapping = {}
        
        # Register lock toggle hotkey
        if 'lock_toggle' in hotkeys:
            lock_hotkey = self._parse_hotkey(self.config.switch_lock)
            hotkey_mapping[lock_hotkey] = self._handle_lock_toggle
            self._registered_hotkeys.add('lock_toggle')
            logger.info(f"Registered lock toggle hotkey: {lock_hotkey}")
        
        # Register screen cycle hotkey
        if 'screen_cycle' in hotkeys:
            cycle_hotkey = self._parse_hotkey(self.config.switch_loop_between_screens)
            hotkey_mapping[cycle_hotkey] = self._handle_screen_cycle
            self._registered_hotkeys.add('screen_cycle')
            logger.info(f"Registered screen cycle hotkey: {cycle_hotkey}")
        
        try:
            # Stop existing listener if running
            if self._listener:
                self._listener.stop()
            
            # Create and start new listener
            self._listener = keyboard.GlobalHotKeys(hotkey_mapping)
            self._listener.start()
            logger.info("Global hotkey listener started successfully")
            
        except Exception as e:
            logger.error(f"Failed to register global hotkeys: {e}")
            raise PlatformError(f"Hotkey registration failed: {e}")
    
    def toggle_lock_mode(self) -> None:
        """Toggle lock mode state between NORMAL and LOCKED."""
        with self._lock:
            if self._state == HotkeyState.NORMAL:
                self._state = HotkeyState.LOCKED
                logger.info("Lock mode activated - automatic screen transitions disabled")
            else:
                self._state = HotkeyState.NORMAL
                logger.info("Lock mode deactivated - automatic screen transitions enabled")
    
    def cycle_screens(self) -> None:
        """Trigger screen cycling functionality."""
        logger.info("Screen cycling triggered via hotkey")
        # The actual screen cycling logic will be handled by the callback
        if 'screen_cycle' in self._callbacks:
            try:
                self._callbacks['screen_cycle']()
            except Exception as e:
                logger.error(f"Error during screen cycling: {e}")
    
    def is_locked(self) -> bool:
        """
        Check if the system is in lock mode.
        
        Returns:
            bool: True if locked (automatic transitions disabled), False otherwise
        """
        with self._lock:
            return self._state == HotkeyState.LOCKED
    
    def get_state(self) -> HotkeyState:
        """
        Get current hotkey system state.
        
        Returns:
            HotkeyState: Current state (NORMAL or LOCKED)
        """
        with self._lock:
            return self._state
    
    def set_state(self, state: HotkeyState) -> None:
        """
        Set hotkey system state.
        
        Args:
            state: New state to set
        """
        with self._lock:
            old_state = self._state
            self._state = state
            logger.info(f"Hotkey state changed from {old_state.value} to {state.value}")
    
    def stop(self) -> None:
        """Stop the hotkey listener and cleanup resources."""
        if self._listener:
            self._listener.stop()
            self._listener = None
            logger.info("Hotkey listener stopped")
        
        self._callbacks.clear()
        self._registered_hotkeys.clear()
    
    def _handle_lock_toggle(self) -> None:
        """Internal handler for lock toggle hotkey."""
        logger.debug("Lock toggle hotkey pressed")
        self.toggle_lock_mode()
        
        # Call registered callback if available
        if 'lock_toggle' in self._callbacks:
            try:
                self._callbacks['lock_toggle']()
            except Exception as e:
                logger.error(f"Error in lock toggle callback: {e}")
    
    def _handle_screen_cycle(self) -> None:
        """Internal handler for screen cycle hotkey."""
        logger.debug("Screen cycle hotkey pressed")
        self.cycle_screens()
    
    def _parse_hotkey(self, hotkey_string: str) -> str:
        """
        Parse hotkey string from config format to pynput format.
        
        Args:
            hotkey_string: Hotkey string from config (e.g., "ctrl+t", "ctrl+grave")
            
        Returns:
            str: Hotkey string in pynput format
        """
        # Convert common key names to pynput format
        key_mapping = {
            'ctrl': '<ctrl>',
            'alt': '<alt>',
            'shift': '<shift>',
            'cmd': '<cmd>',
            'grave': '`',  # backtick/grave accent
            'space': '<space>',
            'tab': '<tab>',
            'enter': '<enter>',
            'esc': '<esc>'
        }
        
        # Split by + and process each part
        parts = hotkey_string.lower().split('+')
        processed_parts = []
        
        for part in parts:
            part = part.strip()
            if part in key_mapping:
                processed_parts.append(key_mapping[part])
            else:
                # For regular keys, just use as-is
                processed_parts.append(part)
        
        result = '+'.join(processed_parts)
        logger.debug(f"Parsed hotkey '{hotkey_string}' to '{result}'")
        return result
    
    def get_registered_hotkeys(self) -> Set[str]:
        """
        Get set of currently registered hotkey names.
        
        Returns:
            Set[str]: Set of registered hotkey names
        """
        return self._registered_hotkeys.copy()
    
    def is_hotkey_registered(self, hotkey_name: str) -> bool:
        """
        Check if a specific hotkey is registered.
        
        Args:
            hotkey_name: Name of the hotkey to check
            
        Returns:
            bool: True if hotkey is registered, False otherwise
        """
        return hotkey_name in self._registered_hotkeys