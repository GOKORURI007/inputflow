"""
A simple test script for InputCapture.
"""

import sys

from inputflow.config.manager import ConfigManager
from inputflow.core.logging import get_logger
from inputflow.input.capture import get_input_capture


def main():
    logger = get_logger("capture_example")
    config_manager = ConfigManager()
    config = config_manager.load_config("config.example.toml")

    logger.info("Initializing input capture for this platform...")
    try:
        # Pass a throttle value in ms for mouse move events from config
        input_capture = get_input_capture(
            logger=logger,
            config=config,
            move_throttle_ms=config.capture.move_throttle_ms,
        )
    except NotImplementedError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during initialization: {e}")
        sys.exit(1)

    logger.info("Starting input monitoring...")
    input_capture.start_monitoring()

    logger.info(
        "\nMonitoring input for 30 seconds. Move your mouse, click, scroll, and type."
    )
    logger.info("Press Enter in this terminal at any time to stop monitoring.")

    # In a real app, this would be handled differently (e.g., in a GUI loop
    # or a service). For this test, we'll just wait for user input.
    input("--------------------------------------------------\n")

    logger.info("Stopping input monitoring...")
    input_capture.stop_monitoring()
    logger.info("Test finished.")


if __name__ == "__main__":
    main()
