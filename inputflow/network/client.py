import pickle
from typing import Iterator

import zmq

from inputflow.core.events import EventType, InputEvent


class NetworkClient:
    def __init__(self, logger):
        self.logger = logger
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)

    def connect(self, server_ip: str, port: int, client_ip: str):
        """
        Connects the client to a server and identifies itself.
        """
        connect_address = f"tcp://{server_ip}:{port}"
        try:
            self.socket.setsockopt_string(zmq.IDENTITY, client_ip)
            self.socket.connect(connect_address)
            self.logger.info(
                f"NetworkClient connected to {connect_address} with identity '{client_ip}'"
            )
            # Announce presence to the server
            self.socket.send(b"connect")
        except zmq.ZMQError as e:
            self.logger.error(f"Failed to connect client to {connect_address}: {e}")
            raise

    def receive_events(self) -> Iterator[InputEvent]:
        """
        A generator that receives, deserializes, and yields input events.
        """
        self.logger.info("Starting to receive events...")
        while True:
            try:
                serialized_event = self.socket.recv()
                event = pickle.loads(serialized_event)
                if event.event_type == EventType.KEYBOARD:
                    self.logger.debug(f"Received event: {event}")
                yield event
            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    self.logger.info("Context terminated, stopping event reception.")
                    break
                else:
                    self.logger.error(f"ZMQ error while receiving event: {e}")
                    break
            except Exception as e:
                self.logger.error(f"Error receiving or deserializing event: {e}")
                continue

    def close(self):
        """
        Notifies server of disconnection and closes the client socket.
        """
        self.logger.info("Closing NetworkClient.")
        try:
            # Notify the server about disconnection
            self.socket.send(b"disconnect")
        except zmq.ZMQError as e:
            self.logger.warning(
                f"Could not notify server of disconnection: {e}"
            )
        finally:
            self.socket.close()
            self.context.term()
