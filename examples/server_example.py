"""
An example script for the NetworkServer.
"""

import random
import time

from inputflow.config.manager import ConfigManager
from inputflow.core.events import EventType, InputEvent, KeyboardEvent, MouseMoveEvent
from inputflow.core.logging import get_logger
from inputflow.input.capture import get_input_capture
from inputflow.network.server import NetworkServer


def main(ip="0.0.0.0"):
    logger = get_logger("server_example")
    config_manager = ConfigManager()
    config = config_manager.load_config("config.toml.example")
    config.network.bind_ip = ip
    server = NetworkServer(logger=logger)

    # Event handler for captured input
    def event_handler(event: InputEvent):
        server.send_event(event)

    try:
        server.bind(config.network.bind_ip, config.network.port)

        input_capture = get_input_capture(
            logger=logger, config=config, event_callback=event_handler
        )
        input_capture.start_monitoring()

        logger.info("InputFlow server started. Press Ctrl+C to stop.")

        # Keep the main thread alive while input capture runs in its own threads
        # You might need a more sophisticated way to keep alive and handle shutdown
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"InputFlow server error: {e}")
    finally:
        # Check if input_capture was successfully initialized and started
        if (
                "input_capture" in locals()
                and hasattr(input_capture, "_monitoring")
                and input_capture._monitoring
        ):
            input_capture.stop_monitoring()
        server.close()


if __name__ == "__main__":
    main()
