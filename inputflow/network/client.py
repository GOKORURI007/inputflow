import pickle
import threading
from typing import Iterator

import zmq

from inputflow.core.events import EventType, InputEvent


class NetworkClient:
    def __init__(self, logger):
        self.logger = logger
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self._stop_event = threading.Event()

    def connect(self, server_ip: str, port: int, client_ip: str):
        """
        Connects the client to a server and identifies itself.
        """
        connect_address = f'tcp://{server_ip}:{port}'
        try:
            self.socket.setsockopt_string(zmq.IDENTITY, client_ip)
            self.socket.connect(connect_address)
            self.logger.info(f"NetworkClient connected to {connect_address} with identity '{client_ip}'")
            # Announce presence to the server
            self.socket.send(b'connect')
        except zmq.ZMQError as e:
            self.logger.error(f'Failed to connect client to {connect_address}: {e}')
            raise

    def receive_events(self) -> Iterator[InputEvent]:
        """
        A generator that receives, deserializes, and yields input events.
        """
        self.logger.info('Starting to receive events...')
        while not self._stop_event.is_set():
            try:
                # Use poll to check if there is data to receive, with timeout
                if self.socket.poll(timeout=1000, flags=zmq.POLLIN) > 0:  # 1 second timeout
                    serialized_event = self.socket.recv(flags=zmq.NOBLOCK)
                    event = pickle.loads(serialized_event)
                    if event.event_type == EventType.KEYBOARD:
                        self.logger.debug(f'Received event: {event}')
                    yield event
            except zmq.Again:
                # This exception is raised when recv() is called with NOBLOCK and no data is available
                continue
            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    self.logger.info('Context terminated, stopping event reception.')
                    break
                elif self._stop_event.is_set():
                    # If stop event is set, exit gracefully
                    self.logger.info('Stop event set, stopping event reception.')
                    break
                else:
                    self.logger.error(f'ZMQ error while receiving event: {e}')
                    # Check if the socket is still valid before continuing
                    if 'not a socket' in str(e) or e.errno == zmq.ENOTSOCK:
                        self.logger.info('Socket is closed, stopping event reception.')
                        break
                    break
            except Exception as e:
                if self._stop_event.is_set():
                    self.logger.info('Stop event set, stopping event reception.')
                    break
                self.logger.error(f'Error receiving or deserializing event: {e}')
                continue

    def close(self):
        """
        Notifies server of disconnection and closes the client socket.
        """
        self.logger.info('Closing NetworkClient.')
        # Set the stop event first to signal other threads to stop
        self._stop_event.set()

        try:
            # Only try to send disconnect if socket is still valid
            if not self.context.closed and self.socket:
                # Notify the server about disconnection
                self.socket.send(b'disconnect')
        except zmq.ZMQError as e:
            self.logger.warning(f'Could not notify server of disconnection: {e}')
        except Exception as e:
            self.logger.warning(f'Unexpected error during disconnection: {e}')
        finally:
            try:
                self.socket.close(linger=0)  # Close with no linger
            except:
                pass  # Socket might already be closed
            try:
                self.context.term()  # Terminate context
            except:
                pass  # Context might already be terminated
