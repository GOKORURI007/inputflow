"""UDP network client for InputFlow."""

import socket
import threading
import time
from typing import Callable, Iterator, Optional

from loguru import logger

from inputflow.core.events import InputEvent
from .messages import MessageType, NetworkMessage, NetworkMessageFactory


class NetworkClient:
    """UDP network client for receiving input events."""
    
    def __init__(self, server_ip: str, port: int = 9999, local_port: Optional[int] = None):
        """Initialize network client.
        
        Args:
            server_ip: Server IP address to connect to
            port: Server port to connect to
            local_port: Local port to bind to (optional, uses system assigned)
        """
        self.server_ip = server_ip
        self.port = port
        self.local_port = local_port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self._receive_thread: Optional[threading.Thread] = None
        self._event_callback: Optional[Callable[[InputEvent], None]] = None
        self._last_heartbeat = 0.0
        
    def connect(self, server_ip: Optional[str] = None, port: Optional[int] = None) -> None:
        """Connect to server.
        
        Args:
            server_ip: Server IP address (optional, uses instance default)
            port: Server port (optional, uses instance default)
            
        Raises:
            OSError: If connection fails
        """
        server_ip = server_ip or self.server_ip
        server_port = port or self.port
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to local port if specified
            if self.local_port:
                self.socket.bind(("0.0.0.0", self.local_port))
                logger.info(f"Client bound to local port {self.local_port}")
            
            # Set socket timeout for non-blocking operations
            self.socket.settimeout(1.0)
            
            self.server_ip = server_ip
            self.port = server_port
            self.running = True
            
            logger.info(f"Network client connecting to {server_ip}:{server_port}")
            
            # Send initial handshake
            self._send_handshake()
            
            # Start receive thread
            self._start_receive_thread()
            
        except OSError as e:
            logger.error(f"Failed to connect to {server_ip}:{server_port}: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            raise
    
    def set_event_callback(self, callback: Callable[[InputEvent], None]) -> None:
        """Set callback function for received input events.
        
        Args:
            callback: Function to call when input event is received
        """
        self._event_callback = callback
        logger.debug("Event callback set")
    
    def receive_events(self) -> Iterator[InputEvent]:
        """Generator that yields received input events.
        
        Yields:
            InputEvent: Received input events
            
        Note:
            This is a blocking generator. Use set_event_callback for non-blocking operation.
        """
        if not self.socket or not self.running:
            logger.warning("Client not connected")
            return
        
        logger.info("Starting event reception loop")
        
        while self.running:
            try:
                # Receive data with timeout
                data, addr = self.socket.recvfrom(4096)
                
                # Parse network message
                message = NetworkMessage.from_bytes(data)
                
                # Handle different message types
                if message.message_type == MessageType.INPUT_EVENT:
                    event = self._parse_input_event(message)
                    if event:
                        yield event
                elif message.message_type == MessageType.HEARTBEAT:
                    self._handle_heartbeat(message)
                
            except socket.timeout:
                # Timeout is expected, continue loop
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error receiving events: {e}")
                    time.sleep(0.1)
    
    def is_connected(self) -> bool:
        """Check if client is connected and receiving heartbeats.
        
        Returns:
            True if connected and receiving heartbeats, False otherwise
        """
        if not self.running or not self.socket:
            return False
        
        # Consider connected if we received a heartbeat in the last 60 seconds
        return time.time() - self._last_heartbeat < 60.0
    
    def close(self) -> None:
        """Close the client and cleanup resources."""
        logger.info("Closing network client")
        self.running = False
        
        # Stop receive thread
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2.0)
        
        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None
        
        logger.info("Network client closed")
    
    def _send_handshake(self) -> None:
        """Send handshake message to server."""
        try:
            handshake_msg = NetworkMessageFactory.create_handshake_message(
                source_ip="client",
                client_info="InputFlow client"
            )
            
            message_bytes = handshake_msg.to_bytes(use_binary=False)  # Use JSON for handshake
            self.socket.sendto(message_bytes, (self.server_ip, self.port))
            
            logger.debug(f"Sent handshake to {self.server_ip}:{self.port}")
            
        except Exception as e:
            logger.warning(f"Failed to send handshake: {e}")
    
    def _start_receive_thread(self) -> None:
        """Start background thread for receiving messages."""
        self._receive_thread = threading.Thread(
            target=self._receive_loop,
            daemon=True,
            name="NetworkClient-Receive"
        )
        self._receive_thread.start()
    
    def _receive_loop(self) -> None:
        """Background thread for receiving and processing messages."""
        logger.info("Started receive loop")
        
        while self.running:
            try:
                # Receive data with timeout
                data, addr = self.socket.recvfrom(4096)
                
                # Parse network message
                message = NetworkMessage.from_bytes(data)
                
                # Handle different message types
                if message.message_type == MessageType.INPUT_EVENT:
                    event = self._parse_input_event(message)
                    if event and self._event_callback:
                        self._event_callback(event)
                elif message.message_type == MessageType.HEARTBEAT:
                    self._handle_heartbeat(message)
                
            except socket.timeout:
                # Timeout is expected, continue loop
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error in receive loop: {e}")
                    time.sleep(0.1)
        
        logger.info("Receive loop stopped")
    
    def _parse_input_event(self, message: NetworkMessage) -> Optional[InputEvent]:
        """Parse network message into InputEvent.
        
        Args:
            message: Network message containing input event data
            
        Returns:
            InputEvent if parsing successful, None otherwise
        """
        return NetworkMessageFactory.message_to_input_event(message)
    
    def _handle_heartbeat(self, message: NetworkMessage) -> None:
        """Handle heartbeat message from server.
        
        Args:
            message: Heartbeat message
        """
        self._last_heartbeat = time.time()
        logger.debug(f"Received heartbeat from {message.source_ip}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()