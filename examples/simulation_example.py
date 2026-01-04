
import sys
import os
import time
import math

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from inputflow.input.simulation import get_input_simulation

def main():
    """
    An example script to test the InputSimulation functionality.
    """
    print("Initializing input simulation for this platform...")
    try:
        simulator = get_input_simulation()
    except (NotImplementedError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Starting simulation in 5 seconds...")
    print("Please focus a text editor or a safe window to see the effects.")
    time.sleep(5)

    # 1. Test typing
    print("Simulating typing 'Hello World!'")
    simulator.type_text("Hello World!")
    
    simulator.hotkey("enter")
    time.sleep(1)

    # 2. Test mouse movement (drawing a square)
    print("Simulating mouse drawing a square...")
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
    print("Simulating a hotkey (Super + q)...")
    print("This might show your desktop or trigger another system shortcut.")
    simulator.hotkey("super", 'q')
    time.sleep(1)
    
    print("Simulating another hotkey (Ctrl + a)...")
    simulator.hotkey("ctrl", 'a')
    time.sleep(1)

    # 4. Test mouse circle (absolute positioning)
    print("Simulating mouse drawing a circle...")
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


    print("\nSimulation finished.")


if __name__ == "__main__":
    main()

