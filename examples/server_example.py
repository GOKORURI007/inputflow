"""
An example script for the NetworkServer.
"""

import time

from inputflow.config.manager import ConfigManager
from inputflow.core.events import InputEvent
from inputflow.core.logging import get_logger
from inputflow.input.capture import get_input_capture
from inputflow.network.server import NetworkServer


def main():
    logger = get_logger("server_example")
    config_manager = ConfigManager()
    config = config_manager.load_config("server.toml")
    server = NetworkServer(logger=logger)

    # Event handler for captured input
    def event_handler(event: InputEvent):
        if server.active_client:
            server.send_event(event, client_identity=server.active_client)

    # Hotkey handler
    def hotkey_handler(hotkey_name: str):
        logger.info(f"Hotkey '{hotkey_name}' pressed.")
        if hotkey_name == "switch_loop_between_screens":
            server.cycle_active_screen()

    try:
        server.bind(config.network.bind_ip, config.network.port)
        server.start()

        input_capture = get_input_capture(
            logger=logger,
            config=config,
            event_callback=event_handler,
            hotkey_callback=hotkey_handler,
        )
        input_capture.start_monitoring()

        logger.info("InputFlow server started. Press Ctrl+C to stop.")

        # Keep the main thread alive while input capture runs in its own threads
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
