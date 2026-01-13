"""
An example script for the NetworkServer.
"""

import time
from dataclasses import asdict

from inputflow.config.manager import ConfigManager
from inputflow.core.events import InputEvent
from inputflow.core.hotkeys import HotkeyManager
from inputflow.core.logging import get_logger
from inputflow.input.capture import get_input_capture
from inputflow.network.server import NetworkServer


def main(ip="0.0.0.0"):
    logger = get_logger("server_example")
    config_manager = ConfigManager()
    config = config_manager.load_config("config.example.toml")
    config.network.bind_ip = ip
    server = NetworkServer(logger=logger)
    server.configure_screens(config.topology)

    # Event handler for captured input
    def event_handler(event: InputEvent):
        if server.active_screen != "server":
            server.send_event(event, topic=server.active_screen)

    # Hotkey handler
    def hotkey_handler(hotkey_name: str):
        logger.info(f"Hotkey '{hotkey_name}' pressed.")
        if hotkey_name == "switch_loop_between_screens":
            server.cycle_active_screen()

    try:
        server.bind(config.network.bind_ip, config.network.port)

        input_capture = get_input_capture(
            logger=logger, config=config, event_callback=event_handler
        )
        input_capture.start_monitoring()

        hotkey_manager = HotkeyManager(
            shortcuts=asdict(config.shortcuts), on_hotkey=hotkey_handler
        )
        hotkey_manager.start()

        logger.info("InputFlow server started. Press Ctrl+C to stop.")

        # Keep the main thread alive while input capture runs in its own threads
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"InputFlow server error: {e}")
    finally:
        if "hotkey_manager" in locals() and hotkey_manager._hotkey_listener:
            hotkey_manager.stop()
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
