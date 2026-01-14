import pickle
from threading import Event, Thread
from typing import List, Optional

import zmq

from inputflow.core.events import EventType, InputEvent, MouseMoveEvent


class NetworkServer:
    def __init__(self, logger):
        self.logger = logger
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        self.clients: List[bytes] = []
        self.active_client: Optional[bytes] = None
        self._stop_event = Event()
        self._listener_thread: Optional[Thread] = None

    @property
    def screens(self) -> List[str]:
        return ['server'] + [c.decode('utf-8') for c in self.clients]

    def cycle_active_screen(self):
        if not self.clients:
            self.active_client = None
            self.logger.info('No clients connected. Active screen is server.')
            return

        if self.active_client is None:
            # Server is active, switch to the first client
            self.active_client = self.clients[0]
        else:
            try:
                current_index = self.clients.index(self.active_client)
                if current_index == len(self.clients) - 1:
                    # Last client is active, switch back to server
                    self.active_client = None
                else:
                    # Switch to the next client
                    self.active_client = self.clients[current_index + 1]
            except ValueError:
                # Active client disconnected, switch to server
                self.active_client = None

        active_screen_name = self.active_client.decode('utf-8') if self.active_client else 'server'
        self.logger.info(f'Active screen switched to: {active_screen_name}')

    def bind(self, ip: str, port: int):
        bind_address = f'tcp://{ip}:{port}'
        try:
            self.socket.bind(bind_address)
            self.logger.info(f'NetworkServer bound to {bind_address}')
        except zmq.ZMQError as e:
            self.logger.error(f'Failed to bind server to {bind_address}: {e}')
            raise

    def start(self):
        self.logger.info('Starting server listener thread.')
        self._stop_event.clear()
        self._listener_thread = Thread(target=self._listen, daemon=True)
        self._listener_thread.start()

    def _listen(self):
        while not self._stop_event.is_set():
            if self.socket.poll(timeout=100):  # Poll with a timeout
                try:
                    client_identity, message = self.socket.recv_multipart()
                    if message == b'connect':
                        if client_identity not in self.clients:
                            self.clients.append(client_identity)
                            self.logger.info(
                                f'Client connected: {client_identity.decode("utf-8")}. '
                                f'Current clients: {[c.decode() for c in self.clients]}'
                            )
                    elif message == b'disconnect':
                        if client_identity in self.clients:
                            self.clients.remove(client_identity)
                            self.logger.info(f'Client disconnected: {client_identity.decode("utf-8")}')
                            if self.active_client == client_identity:
                                self.active_client = None
                                self.logger.info('Active client disconnected. Switched to server.')
                except zmq.ZMQError as e:
                    if not self._stop_event.is_set():
                        self.logger.error(f'ZMQ error in listener: {e}')
                    break

    def send_event(self, event: InputEvent, client_identity: bytes):
        try:
            if event.event_type == EventType.MOUSE_MOVE:
                move_event: MouseMoveEvent = event.data
                relative_move_event = MouseMoveEvent(
                    normalized_x=-1,
                    normalized_y=-1,
                    dx=move_event.dx,
                    dy=move_event.dy,
                )
                event_to_send = InputEvent(event_type=EventType.MOUSE_MOVE, data=relative_move_event)
            else:
                event_to_send = event

            serialized_event = pickle.dumps(event_to_send)
            self.socket.send_multipart([client_identity, serialized_event])

            if event.event_type == EventType.KEYBOARD:
                self.logger.debug(f'Sent event to {client_identity.decode("utf-8")}: {event_to_send}')

        except Exception as e:
            self.logger.error(f'Failed to send event to {client_identity.decode("utf-8")}: {e}')

    def close(self):
        self.logger.info('Closing NetworkServer.')
        self._stop_event.set()
        if self._listener_thread:
            self._listener_thread.join()
        self.socket.close()
        self.context.term()
