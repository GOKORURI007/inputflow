import os
import sys

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from inputflow.input.capture import get_input_capture


def main():
    """
    A simple test script for InputCapture.
    """
    print("Initializing input capture for this platform...")
    try:
        # Pass a throttle value in ms for mouse move events
        input_capture = get_input_capture(move_throttle_ms=16)
    except NotImplementedError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during initialization: {e}")
        sys.exit(1)

    print("Starting input monitoring...")
    input_capture.start_monitoring()

    print(
        "\nMonitoring input for 30 seconds. Move your mouse, click, scroll, and type."
    )
    print("Press Enter in this terminal at any time to stop monitoring.")

    # In a real app, this would be handled differently (e.g., in a GUI loop
    # or a service). For this test, we'll just wait for user input.
    input("--------------------------------------------------\n")

    print("Stopping input monitoring...")
    input_capture.stop_monitoring()
    print("Test finished.")


if __name__ == "__main__":
    main()
