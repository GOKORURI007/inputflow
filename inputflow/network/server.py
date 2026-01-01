"""UDP network server for InputFlow."""

import socket
import threading
import time
from typing import Dict, Optional

from loguru import logger

from inputflow.core.events import InputEvent
from .messages import NetworkMessageFactory


class NetworkServer:
    """UDP network server for transmitting input events."""
    
    def __init__(self, bind_ip: str = "0.0.0.0", port: int = 9999):
        """Initialize network server.
        
        Args:
            bind_ip: IP address to bind to
            port: Port number to bind to
        """
        self.bind_ip = bind_ip
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.clients: Dict[str, float] = {}  # client_ip -> last_seen_timestamp
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        
    def bind(self, ip: Optional[str] = None, port: Optional[int] = None) -> None:
        """Bind server to IP address and port.
        
        Args:
            ip: IP address to bind to (optional, uses instance default)
            port: Port to bind to (optional, uses instance default)
            
        Raises:
            OSError: If binding fails
        """
        bind_ip = ip or self.bind_ip
        bind_port = port or self.port
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((bind_ip, bind_port))
            
            self.bind_ip = bind_ip
            self.port = bind_port
            self.running = True
            
            logger.info(f"Network server bound to {bind_ip}:{bind_port}")
            
            # Start background threads
            self._start_background_threads()
            
        except OSError as e:
            logger.error(f"Failed to bind server to {bind_ip}:{bind_port}: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            raise
    
    def send_event(self, event: InputEvent, target_ip: str, target_port: Optional[int] = None) -> bool:
        """Send input event to target client.
        
        Args:
            event: Input event to send
            target_ip: Target client IP address
            target_port: Target client port (optional, uses server port)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.socket or not self.running:
            logger.warning("Server not running, cannot send event")
            return False
        
        try:
            # Create network message from input event
            message = NetworkMessageFactory.create_input_event_message(event, self.bind_ip)
            # Use binary format for input events for better performance
            message_bytes = message.to_bytes(use_binary=True)
            
            # Send to target
            port = target_port or self.port
            self.socket.sendto(message_bytes, (target_ip, port))
            
            logger.debug(f"Sent {event.event_type.value} event to {target_ip}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send event to {target_ip}: {e}")
            return False
    
    def broadcast_event(self, event: InputEvent) -> int:
        """Broadcast input event to all known clients.
        
        Args:
            event: Input event to broadcast
            
        Returns:
            Number of clients the event was sent to
        """
        if not self.clients:
            logger.debug("No clients to broadcast to")
            return 0
        
        sent_count = 0
        for client_ip in list(self.clients.keys()):
            if self.send_event(event, client_ip):
                sent_count += 1
        
        return sent_count
    
    def register_client(self, client_ip: str) -> None:
        """Register a client for broadcasting.
        
        Args:
            client_ip: Client IP address to register
        """
        self.clients[client_ip] = time.time()
        logger.info(f"Registered client: {client_ip}")
    
    def unregister_client(self, client_ip: str) -> None:
        """Unregister a client.
        
        Args:
            client_ip: Client IP address to unregister
        """
        if client_ip in self.clients:
            del self.clients[client_ip]
            logger.info(f"Unregistered client: {client_ip}")
    
    def get_clients(self) -> Dict[str, float]:
        """Get dictionary of registered clients and their last seen timestamps.
        
        Returns:
            Dictionary mapping client IP to last seen timestamp
        """
        return self.clients.copy()
    
    def close(self) -> None:
        """Close the server and cleanup resources."""
        logger.info("Closing network server")
        self.running = False
        
        # Stop background threads
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1.0)
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)
        
        # Close socket
        if self.socket:
            self.socket.close()
            self.socket = None
        
        # Clear clients
        self.clients.clear()
        
        logger.info("Network server closed")
    
    def _start_background_threads(self) -> None:
        """Start background threads for heartbeat and cleanup."""
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="NetworkServer-Heartbeat"
        )
        self._heartbeat_thread.start()
        
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="NetworkServer-Cleanup"
        )
        self._cleanup_thread.start()
    
    def _heartbeat_loop(self) -> None:
        """Background thread for sending heartbeat messages to clients."""
        while self.running:
            try:
                if self.clients:
                    heartbeat_msg = NetworkMessageFactory.create_heartbeat_message(self.bind_ip)
                    # Use JSON format for heartbeat messages
                    heartbeat_bytes = heartbeat_msg.to_bytes(use_binary=False)
                    
                    for client_ip in list(self.clients.keys()):
                        try:
                            self.socket.sendto(heartbeat_bytes, (client_ip, self.port))
                        except Exception as e:
                            logger.warning(f"Failed to send heartbeat to {client_ip}: {e}")
                
                time.sleep(30.0)  # Send heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(5.0)
    
    def _cleanup_loop(self) -> None:
        """Background thread for cleaning up stale clients."""
        while self.running:
            try:
                current_time = time.time()
                stale_clients = []
                
                for client_ip, last_seen in self.clients.items():
                    if current_time - last_seen > 120.0:  # 2 minutes timeout
                        stale_clients.append(client_ip)
                
                for client_ip in stale_clients:
                    self.unregister_client(client_ip)
                    logger.info(f"Removed stale client: {client_ip}")
                
                time.sleep(60.0)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(10.0)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()