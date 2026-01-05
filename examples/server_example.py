"""
An example script for the NetworkServer.
"""

import random
import time

from inputflow.config.manager import ConfigManager
from inputflow.core.events import EventType, InputEvent, KeyboardEvent, MouseMoveEvent
from inputflow.core.logging import get_logger
from inputflow.network.server import NetworkServer


def main():
    logger = get_logger("server_example")
    config_manager = ConfigManager()
    config = config_manager.load_config("config.toml.example")

    server = NetworkServer(logger=logger)
    try:
        server.bind(config.network.bind_ip, config.network.port)

        logger.info("Server started. Sending dummy events for 15 seconds...")

        end_time = time.time() + 15
        while time.time() < end_time:
            # Send a mouse move event
            mouse_event_data = MouseMoveEvent(
                normalized_x=random.random(),
                normalized_y=random.random(),
                timestamp=time.time(),
            )
            server.send_event(
                InputEvent(event_type=EventType.MOUSE_MOVE, data=mouse_event_data)
            )

            # Send a key press event
            key_event_data = KeyboardEvent(
                key_code=random.randint(65, 90),  # Random key 'A'-'Z'
                pressed=True,
                timestamp=time.time(),
            )
            server.send_event(
                InputEvent(event_type=EventType.KEYBOARD, data=key_event_data)
            )

            time.sleep(1)

        logger.info("Finished sending events.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        server.close()
        logger.info("Server shut down.")


if __name__ == "__main__":
    main()
