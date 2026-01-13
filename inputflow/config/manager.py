import tomllib
from pathlib import Path

from inputflow.config.models import Config, HotkeyConfig, NetworkConfig, TopologyEntry
from inputflow.core.logging import get_logger

logger = get_logger("config_manager")


class ConfigManager:
    def __init__(self):
        self.config: Config = Config()  # Default config

    def load_config(self, config_path: str) -> Config:
        config_file_path = Path(config_path)
        if not config_file_path.exists():
            logger.warning(
                f"Config file not found at {config_path}. Using default configuration."
            )
            return self.config

        try:
            with open(config_file_path, "rb") as f:
                toml_config = tomllib.load(f)

            self.config = self._parse_and_validate(toml_config)
            logger.info(f"Configuration loaded successfully from {config_path}.")
        except tomllib.TOMLDecodeError as e:
            logger.error(f"Error decoding TOML config file {config_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {e}")
            raise

        return self._config

    @staticmethod
    def _parse_and_validate(toml_data: dict) -> Config:
        # Parse NetworkConfig
        network_data = toml_data.get("network", {})
        network_config = NetworkConfig(**network_data)

        # Parse Topology
        topology_data = toml_data.get("topology", [])
        topology_config = []
        for entry in topology_data:
            topology_config.append(TopologyEntry(**entry))

        # Parse HotkeyConfig
        shortcuts_data = toml_data.get("shortcuts", {})
        shortcuts_config = HotkeyConfig(**shortcuts_data)

        return Config(
            network=network_config, topology=topology_config, shortcuts=shortcuts_config
        )
