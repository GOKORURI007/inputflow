"""
An example script for the NetworkClient.
"""

import threading
import time

from inputflow.config.manager import ConfigManager
from inputflow.core.logging import get_logger
from inputflow.input.simulation import get_input_simulation
from inputflow.network.client import NetworkClient


def main():
    logger = get_logger("client_example")
    config_manager = ConfigManager()
    config = config_manager.load_config("client.toml")

    if not config.topology:
        logger.error("Topology is not configured. Client cannot determine its own IP.")
        return

    server_ip = config.network.server_ip
    client_ip = config.topology[0].self_ip

    if not server_ip:
        logger.error("Server IP is not configured in network settings.")
        return

    client = NetworkClient(logger=logger)
    input_simulation = get_input_simulation(logger=logger, config=config)

    def receive_loop():
        try:
            client.connect(server_ip, config.network.port, client_ip=client_ip)
            for event in client.receive_events():
                input_simulation.replay_event(event)
        except Exception as e:
            # The loop might break if the server closes the connection
            logger.info(f"Event reception stopped: {e}")

    receiver_thread = threading.Thread(target=receive_loop, daemon=True)
    receiver_thread.start()

    logger.info("Client started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Client shutting down.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
