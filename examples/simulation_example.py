"""
An example script to test the InputSimulation functionality.
"""

import math
import sys
import time

from inputflow.config.manager import ConfigManager
from inputflow.core.keymaps import name_to_hid_key
from inputflow.core.logging import get_logger
from inputflow.input.simulation import get_input_simulation


def main():
    logger = get_logger("simulation_example")
    config_manager = ConfigManager()
    config = config_manager.load_config("config.example.toml")

    logger.info("Initializing input simulation for this platform...")
    try:
        simulator = get_input_simulation(logger=logger, config=config)
    except (NotImplementedError, RuntimeError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

    logger.info("Starting simulation in 5 seconds...")
    logger.info("Please focus a text editor or a safe window to see the effects.")
    time.sleep(5)

    # 1. Test typing
    # logger.info("Simulating typing 'Hello World!'")
    # simulator.type_text("Hello World!")

    simulator.hotkey(name_to_hid_key("KEY_ENTER"))
    time.sleep(1)

    # 2. Test mouse movement (drawing a square)
    logger.info("Simulating mouse drawing a square...")
    side_length = 50
    for _ in range(4):
        simulator.move_mouse_rel(side_length, 0)
        time.sleep(0.1)
        simulator.move_mouse_rel(0, side_length)
        time.sleep(0.1)
        simulator.move_mouse_rel(-side_length, 0)
        time.sleep(0.1)
        simulator.move_mouse_rel(0, -side_length)
        time.sleep(0.1)

    time.sleep(1)

    # 3. Test hotkeys
    logger.info("Simulating a hotkey (Super + q)...")
    logger.info("This might show your desktop or trigger another system shortcut.")
    simulator.hotkey(name_to_hid_key("KEY_LEFTMETA"), name_to_hid_key("KEY_Q"))
    time.sleep(1)

    logger.info("Simulating a hotkey (Super + d)...")
    simulator.hotkey(name_to_hid_key("KEY_LEFTMETA"), name_to_hid_key("KEY_D"))
    time.sleep(1)

    logger.info("Simulating another hotkey (Ctrl + a)...")
    simulator.hotkey(name_to_hid_key("KEY_LEFTCTRL"), name_to_hid_key("KEY_A"))
    time.sleep(1)

    # 4. Test mouse circle (absolute positioning)
    logger.info("Simulating mouse drawing a circle...")
    radius = 100
    steps = 50

    # Get current position to draw circle around it.
    # This is not available in the interface, so we draw from our last known pos.
    # We will draw relative to the center of the square we just drew.

    last_x, last_y = 0, 0
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        dx = int(x - last_x)
        dy = int(y - last_y)
        simulator.move_mouse_rel(dx, dy)
        last_x, last_y = x, y
        time.sleep(0.02)

    logger.info("\nSimulation finished.")


if __name__ == "__main__":
    main()
