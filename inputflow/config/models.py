from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NetworkConfig:
    role: str = "client"  # "server" or "client"
    bind_ip: str = "0.0.0.0"
    port: int = 50007
    server_ip: Optional[str] = None # IP of the server to connect to in client mode



@dataclass
class TopologyEntry:
    self_ip: str = "127.0.0.1"
    left: Optional[str] = None
    right: Optional[str] = None
    up: Optional[str] = None
    down: Optional[str] = None


@dataclass
class HotkeyConfig:
    switch_lock: str = "ctrl+alt+l"
    switch_loop_between_screens: str = "ctrl+alt+s"


@dataclass
class CaptureConfig:
    move_throttle_ms: int = 16

@dataclass
class DisplayConfig:
    width: int = 1920
    height: int = 1080

@dataclass
class Config:
    network: NetworkConfig = field(default_factory=NetworkConfig)
    topology: List[TopologyEntry] = field(default_factory=list)
    shortcuts: HotkeyConfig = field(default_factory=HotkeyConfig)
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)