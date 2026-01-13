import pickle
from typing import Iterator

import zmq

from inputflow.core.events import EventType, InputEvent


class NetworkClient:
    def __init__(self, logger):
        self.logger = logger
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)

    def connect(self, server_ip: str, port: int, client_ip: str):
        """
        Connects the client to a server and subscribes to a topic.
        """
        connect_address = f"tcp://{server_ip}:{port}"
        try:
            self.socket.connect(connect_address)
            self.socket.setsockopt_string(zmq.SUBSCRIBE, client_ip)
            self.logger.info(
                f"NetworkClient connected to {connect_address}, subscribed to topic '{client_ip}'"
            )
        except zmq.ZMQError as e:
            self.logger.error(f"Failed to connect client to {connect_address}: {e}")
            raise

    def receive_events(self) -> Iterator[InputEvent]:
        """
        A generator that receives, deserializes, and yields input events from multipart messages.
        """
        self.logger.info("Starting to receive events...")
        while True:
            try:
                topic, serialized_event = self.socket.recv_multipart()
                event = pickle.loads(serialized_event)
                if event.event_type == EventType.KEYBOARD:
                    self.logger.debug(
                        f"Received event on topic {topic.decode()}: {event}"
                    )
                yield event
            except zmq.ZMQError as e:
                # This can happen on socket close, so we check if it's intentional
                if e.errno == zmq.ETERM:
                    self.logger.info("Context terminated, stopping event reception.")
                    break
                else:
                    self.logger.error(f"ZMQ error while receiving event: {e}")
                    break
            except Exception as e:
                self.logger.error(f"Error receiving or deserializing event: {e}")
                # Decide if we should break or continue
                continue

    def close(self):
        """
        Closes the client socket and context.
        """
        self.logger.info("Closing NetworkClient.")
        self.socket.close()
        self.context.term()
