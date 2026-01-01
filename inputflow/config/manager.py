"""Configuration manager for loading and validating TOML configuration files."""

import os
from typing import Any, Dict, Optional

import toml
from loguru import logger

from .models import Config, HotkeyConfig, NetworkConfig, TopologyEntry


class ConfigManager:
    """Manages loading and validation of TOML configuration files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize ConfigManager with optional config path."""
        self.config_path = config_path or "config.toml"
        self._config: Optional[Config] = None
    
    def load_config(self, path: Optional[str] = None) -> Config:
        """Load configuration from TOML file."""
        config_file = path or self.config_path
        
        try:
            if not os.path.exists(config_file):
                logger.warning(f"Configuration file {config_file} not found, using defaults")
                return self._create_default_config()
            
            with open(config_file, "r", encoding="utf-8") as f:
                toml_data = toml.load(f)
            
            logger.info(f"Loaded configuration from {config_file}")
            config = self._parse_config(toml_data)
            self._config = config
            return config
            
        except toml.TomlDecodeError as e:
            logger.error(f"Failed to parse TOML file {config_file}: {e}")
            raise ValueError(f"Invalid TOML format in {config_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")
            raise
    
    def validate_config(self, config: Config) -> bool:
        """Validate configuration object."""
        try:
            # Validation is handled by dataclass __post_init__ methods
            # Additional validation can be added here if needed
            logger.info("Configuration validation passed")
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_network_config(self) -> NetworkConfig:
        """Get network configuration."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config.network
    
    def get_topology_config(self) -> list[TopologyEntry]:
        """Get topology configuration."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config.topology
    
    def get_hotkey_config(self) -> HotkeyConfig:
        """Get hotkey configuration."""
        if not self._config:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")
        return self._config.shortcuts
    
    def _parse_config(self, toml_data: Dict[str, Any]) -> Config:
        """Parse TOML data into Config object."""
        # Parse network configuration
        network_data = toml_data.get("network", {})
        network_config = NetworkConfig(
            role=network_data.get("role", "server"),
            bind_ip=network_data.get("bind_ip", "0.0.0.0"),
            port=network_data.get("port", 9999),
            tcp_nodelay=network_data.get("tcp_nodelay", True)
        )
        
        # Parse topology configuration
        topology_data = toml_data.get("topology", [])
        topology_entries = []
        for entry_data in topology_data:
            topology_entry = TopologyEntry(
                self_ip=entry_data.get("self_ip", ""),
                left=entry_data.get("left"),
                right=entry_data.get("right"),
                up=entry_data.get("up"),
                down=entry_data.get("down")
            )
            topology_entries.append(topology_entry)
        
        # Parse hotkey configuration
        shortcuts_data = toml_data.get("shortcuts", {})
        hotkey_config = HotkeyConfig(
            switch_lock=shortcuts_data.get("switch_lock", "ctrl+t"),
            switch_loop_between_screens=shortcuts_data.get("switch_loop_between_screens", "ctrl+grave")
        )
        
        return Config(
            network=network_config,
            topology=topology_entries,
            shortcuts=hotkey_config
        )
    
    def _create_default_config(self) -> Config:
        """Create default configuration when config file is missing."""
        logger.info("Creating default configuration")
        
        default_network = NetworkConfig(
            role="server",
            bind_ip="0.0.0.0",
            port=9999,
            tcp_nodelay=True
        )
        
        default_topology = [
            TopologyEntry(
                self_ip="127.0.0.1",
                right="192.168.1.100"
            )
        ]
        
        default_hotkeys = HotkeyConfig(
            switch_lock="ctrl+t",
            switch_loop_between_screens="ctrl+grave"
        )
        
        return Config(
            network=default_network,
            topology=default_topology,
            shortcuts=default_hotkeys
        )