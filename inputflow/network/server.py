import pickle
from typing import List

import zmq

from inputflow.core.events import EventType, InputEvent, MouseMoveEvent


class NetworkServer:
    def __init__(self, logger):
        self.logger = logger
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.screens: List[str] = ["server"]
        self.active_screen_index = 0

    @property
    def active_screen(self) -> str:
        return self.screens[self.active_screen_index]

    def configure_screens(self, topology):
        for entry in topology:
            for ip in [entry.self_ip, entry.left, entry.right, entry.up, entry.down]:
                if ip and ip not in self.screens:
                    self.screens.append(ip)
        self.logger.info(f"Configured screens: {self.screens}")

    def cycle_active_screen(self):
        self.active_screen_index = (self.active_screen_index + 1) % len(self.screens)
        self.logger.info(f"Active screen switched to: {self.active_screen}")

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

    def send_event(self, event: InputEvent, topic: str):
        """
        Serializes and sends an input event to a specific topic.
        """
        try:
            # For mouse movements, send only relative coordinates
            if event.event_type == EventType.MOUSE_MOVE:
                move_event: MouseMoveEvent = event.data
                # Create a new event with only relative data for the client
                relative_move_event = MouseMoveEvent(
                    normalized_x=-1,
                    normalized_y=-1,
                    dx=move_event.dx,
                    dy=move_event.dy,
                )
                event_to_send = InputEvent(
                    event_type=EventType.MOUSE_MOVE, data=relative_move_event
                )
            else:
                event_to_send = event

            serialized_event = pickle.dumps(event_to_send)
            self.socket.send_multipart([topic.encode("utf-8"), serialized_event])

            if event.event_type == EventType.KEYBOARD:
                self.logger.debug(f"Sent event to {topic}: {event_to_send}")

        except Exception as e:
            self.logger.error(f"Failed to send event to {topic}: {e}")

    def close(self):
        """
        Closes the server socket and context.
        """
        self.logger.info("Closing NetworkServer.")
        self.socket.close()
        self.context.term()
