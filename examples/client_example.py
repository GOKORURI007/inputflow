"""
An example script for the NetworkClient.
"""

import threading

from inputflow.config.manager import ConfigManager
from inputflow.core.logging import get_logger
from inputflow.network.client import NetworkClient


def main(ip="127.0.0.1"):
    logger = get_logger("client_example")
    config_manager = ConfigManager()
    config = config_manager.load_config("config.toml.example")

    # Assuming the server is on localhost if topology is empty or misconfigured for this example
    server_ip = ip

    client = NetworkClient(logger=logger)

    def receive_loop():
        try:
            client.connect(server_ip, config.network.port)
            for event in client.receive_events():
                logger.info(f"Received event: {event}")
        except Exception as e:
            # The loop might break if the server closes the connection
            logger.info(f"Event reception stopped: {e}")

    # Run the receiver in a separate thread
    receiver_thread = threading.Thread(target=receive_loop, daemon=True)
    receiver_thread.start()

    logger.info("Client started. Listening for events for 20 seconds...")

    # Let the receiver run for a while
    receiver_thread.join(timeout=20)

    logger.info("Client shutting down.")
    client.close()


if __name__ == "__main__":
    main(ip="192.168.123.154")
