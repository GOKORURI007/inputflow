import pickle

import zmq

from inputflow.core.events import EventType, InputEvent


class NetworkServer:
    def __init__(self, logger):
        self.logger = logger
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)

    def bind(self, ip: str, port: int):
        """
        Binds the server to a specific IP and port.
        """
        bind_address = f"tcp://{ip}:{port}"
        try:
            self.socket.bind(bind_address)
            self.logger.info(f"NetworkServer bound to {bind_address}")
        except zmq.ZMQError as e:
            self.logger.error(f"Failed to bind server to {bind_address}: {e}")
            raise

    def send_event(self, event: InputEvent):
        """
        Serializes and sends an input event.
        """
        try:
            serialized_event = pickle.dumps(event)
            self.socket.send(serialized_event)
            if event.event_type == EventType.KEYBOARD:
                self.logger.debug(f"Sent event: {event}")
        except Exception as e:
            self.logger.error(f"Failed to send event: {e}")

    def close(self):
        """
        Closes the server socket and context.
        """
        self.logger.info("Closing NetworkServer.")
        self.socket.close()
        self.context.term()
