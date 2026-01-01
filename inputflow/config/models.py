"""Configuration data models for InputFlow."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class NetworkConfig:
    """Network configuration settings."""
    role: str  # "server" or "client"
    bind_ip: str
    port: int
    tcp_nodelay: bool = True
    
    def __post_init__(self):
        """Validate network configuration."""
        if self.role not in ("server", "client"):
            raise ValueError(f"Invalid role: {self.role}. Must be 'server' or 'client'")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Invalid port: {self.port}. Must be between 1 and 65535")


@dataclass
class TopologyEntry:
    """Screen topology entry defining relationships between screens."""
    self_ip: str
    left: Optional[str] = None
    right: Optional[str] = None
    up: Optional[str] = None
    down: Optional[str] = None
    
    def get_direction_target(self, direction: str) -> Optional[str]:
        """Get the target IP for a given direction."""
        direction_map = {
            "left": self.left,
            "right": self.right,
            "up": self.up,
            "down": self.down
        }
        return direction_map.get(direction.lower())


@dataclass
class HotkeyConfig:
    """Hotkey configuration settings."""
    switch_lock: str = "ctrl+t"
    switch_loop_between_screens: str = "ctrl+grave"
    
    def __post_init__(self):
        """Validate hotkey configuration."""
        if not self.switch_lock or not self.switch_loop_between_screens:
            raise ValueError("Hotkey configurations cannot be empty")


@dataclass
class Config:
    """Main configuration container."""
    network: NetworkConfig
    topology: List[TopologyEntry]
    shortcuts: HotkeyConfig
    
    def __post_init__(self):
        """Validate complete configuration."""
        if not self.topology:
            raise ValueError("Topology configuration cannot be empty")
        
        # Validate that all topology entries have unique self_ip
        self_ips = [entry.self_ip for entry in self.topology]
        if len(self_ips) != len(set(self_ips)):
            raise ValueError("Duplicate self_ip entries found in topology")
    
    def get_topology_for_ip(self, ip: str) -> Optional[TopologyEntry]:
        """Get topology entry for a specific IP address."""
        for entry in self.topology:
            if entry.self_ip == ip:
                return entry
        return None