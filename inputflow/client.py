#!/usr/bin/env python3
"""
InputFlow Client Application

Main client entry point that receives input events from the server and simulates
them on the local system. Integrates network reception, coordinate transformation,
input simulation, and proper event handling with error recovery.
"""

import signal
import sys
import time
from typing import Optional

from loguru import logger

from inputflow.config.manager import ConfigManager
from inputflow.core.coordinates import CoordinateTransformer
from inputflow.core.events import EventType, InputEvent
from inputflow.core.logging import (log_configuration_status, log_connection_status,
                                    log_error_with_troubleshooting, log_input_event,
                                    log_network_binding_info, log_performance_stats,
                                    log_platform_info, log_startup_banner, setup_logging)
from inputflow.core.throttling import ThrottleConfig
from inputflow.input.platform import PlatformFactory
from inputflow.network.client import NetworkClient


class InputFlowClient:
    """
    Main client application for InputFlow.
    
    Integrates network reception, coordinate transformation, and input simulation
    to provide seamless input event reproduction on the client system.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the InputFlow client.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.config = None
        
        # Core components
        self.platform_factory = None
        self.input_simulation = None
        self.network_client = None
        self.coordinate_transformer = CoordinateTransformer()
        
        # State management
        self.running = False
        self.server_ip = None
        self.server_port = 9999
        self.screen_dimensions = (1920, 1080)  # Default, will be updated
        
        # Connection state
        self.connected = False
        self.last_event_time = 0.0
        self.connection_retry_count = 0
        self.max_retry_attempts = 5
        self.retry_delay = 5.0  # seconds
        
        # Statistics
        self.stats = {
            'events_received': 0,
            'events_simulated': 0,
            'connection_attempts': 0,
            'connection_failures': 0,
            'simulation_errors': 0
        }
        
        logger.info("InputFlow client initialized")
    
    def load_configuration(self) -> None:
        """Load and validate configuration from TOML file."""
        try:
            self.config = self.config_manager.load_config()
            
            if not self.config_manager.validate_config(self.config):
                raise ValueError("Configuration validation failed")
            
            # For client, we need to find the server IP from topology
            network_config = self.config.network
            
            if network_config.role == "client":
                # Find server IP from topology configuration
                topology_config = self.config.topology
                if topology_config:
                    # Use the first topology entry to find server
                    # In a real implementation, this might be more sophisticated
                    for entry in topology_config:
                        if entry.self_ip != network_config.bind_ip:
                            # Assume any other IP in topology is the server
                            self.server_ip = entry.self_ip
                            break
                    
                    if not self.server_ip:
                        # Fallback: look for any configured direction targets
                        for entry in topology_config:
                            for direction_ip in [entry.left, entry.right, entry.up, entry.down]:
                                if direction_ip and direction_ip != network_config.bind_ip:
                                    self.server_ip = direction_ip
                                    break
                            if self.server_ip:
                                break
                
                if not self.server_ip:
                    raise ValueError("Could not determine server IP from configuration")
            else:
                # Configuration might be set up as server, but we're running as client
                # Use bind_ip as server IP
                self.server_ip = network_config.bind_ip
            
            self.server_port = network_config.port
            
            # Log configuration status
            config_dict = {
                'network': {
                    'role': network_config.role,
                    'bind_ip': network_config.bind_ip,
                    'port': network_config.port,
                    'tcp_nodelay': network_config.tcp_nodelay
                },
                'topology': [
                    {
                        'self_ip': entry.self_ip,
                        'left': entry.left,
                        'right': entry.right,
                        'up': entry.up,
                        'down': entry.down
                    } for entry in self.config.topology
                ] if self.config.topology else [],
                'shortcuts': {
                    'switch_lock': self.config.shortcuts.switch_lock,
                    'switch_loop_between_screens': self.config.shortcuts.switch_loop_between_screens
                } if hasattr(self.config, 'shortcuts') else {}
            }
            log_configuration_status(config_dict, self.config_path)
            
            logger.info(f"Configuration loaded - Server: {self.server_ip}:{self.server_port}")
            
        except Exception as e:
            troubleshooting_tips = [
                "Check if config.toml exists in the current directory",
                "Verify TOML syntax is correct (use a TOML validator)",
                "Ensure all required sections are present: [network], [topology]",
                "Check that server IP can be determined from topology",
                "Verify IP addresses and ports are valid"
            ]
            log_error_with_troubleshooting(str(e), "Configuration Error", troubleshooting_tips)
            raise
    
    def initialize_components(self) -> None:
        """Initialize all system components."""
        try:
            # Initialize platform factory and check permissions
            self.platform_factory = PlatformFactory()
            
            permissions_ok = self.platform_factory.check_permissions()
            if not permissions_ok:
                instructions = self.platform_factory.get_permission_instructions()
                if instructions:
                    troubleshooting_tips = [
                        "Run the application with appropriate permissions",
                        "On Linux: Add user to 'input' group or run with sudo",
                        "Check /dev/input and /dev/uinput permissions",
                        instructions
                    ]
                    log_error_with_troubleshooting(
                        "Insufficient permissions for input simulation", 
                        "Permission Error", 
                        troubleshooting_tips
                    )
                    raise RuntimeError("Insufficient permissions for input simulation")
            
            # Get screen dimensions
            self.screen_dimensions = self.coordinate_transformer.get_screen_dimensions()
            
            # Log platform information
            log_platform_info(
                self.platform_factory.platform.value, 
                permissions_ok, 
                self.screen_dimensions
            )
            
            # Initialize input simulation with throttling
            throttle_config = ThrottleConfig(
                min_interval_us=500,  # 0.5ms throttling for simulation
                min_distance_pixels=0.5
            )
            
            self.input_simulation = self.platform_factory.create_input_simulation(throttle_config)
            
            # Initialize network client
            self.network_client = NetworkClient(self.server_ip, self.server_port)
            self.network_client.set_event_callback(self._handle_received_event)
            
            # Log network connection information
            log_network_binding_info(self.server_ip, self.server_port, "client")
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            troubleshooting_tips = [
                "Check system permissions for input device access",
                "Verify server is running and accessible",
                "Ensure required libraries are installed (pynput, evdev)",
                "Check if running in a supported environment"
            ]
            log_error_with_troubleshooting(str(e), "Component Initialization Error", troubleshooting_tips)
            raise
    
    def start(self) -> None:
        """Start the client and begin receiving events."""
        try:
            # Log startup banner
            log_startup_banner("InputFlow Client")
            
            # Load configuration
            self.load_configuration()
            
            # Initialize components
            self.initialize_components()
            
            # Set running flag
            self.running = True
            
            # Display startup information
            self._display_startup_info()
            
            logger.info("InputFlow client started successfully")
            logger.info("Press Ctrl+C to stop the client")
            
        except Exception as e:
            troubleshooting_tips = [
                "Check if server is running and accessible",
                "Verify network connectivity to server",
                "Ensure configuration file is valid",
                "Check system permissions"
            ]
            log_error_with_troubleshooting(str(e), "Client Startup Error", troubleshooting_tips)
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the client and cleanup resources."""
        logger.info("Stopping InputFlow client...")
        self.running = False
        self.connected = False
        
        # Close network client
        if self.network_client:
            try:
                self.network_client.close()
                logger.info("Network client closed")
            except Exception as e:
                logger.error(f"Error closing network client: {e}")
        
        # Display final statistics
        self._display_statistics()
        
        logger.info("InputFlow client stopped")
    
    def run(self) -> None:
        """Run the client main loop with connection management."""
        try:
            self.start()
            
            # Main loop with connection management
            while self.running:
                try:
                    if not self.connected:
                        self._attempt_connection()
                    
                    if self.connected:
                        # Check connection health
                        if not self.network_client.is_connected():
                            logger.warning("Lost connection to server")
                            self.connected = False
                            self.connection_retry_count = 0
                            continue
                        
                        # Connection is healthy, just wait
                        time.sleep(1.0)
                    else:
                        # Not connected, wait before retry
                        time.sleep(self.retry_delay)
                
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(1.0)
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.stop()
    
    def _attempt_connection(self) -> None:
        """Attempt to connect to the server with retry logic."""
        if self.connection_retry_count >= self.max_retry_attempts:
            logger.error(f"Maximum retry attempts ({self.max_retry_attempts}) reached")
            log_connection_status("failed", "Maximum retry attempts exceeded")
            self.running = False
            return
        
        try:
            log_connection_status("connecting", 
                f"{self.server_ip}:{self.server_port} (attempt {self.connection_retry_count + 1}/{self.max_retry_attempts})")
            
            self.stats['connection_attempts'] += 1
            
            # Connect to server
            self.network_client.connect(self.server_ip, self.server_port)
            
            # Wait a moment to see if connection is established
            time.sleep(2.0)
            
            if self.network_client.is_connected():
                self.connected = True
                self.connection_retry_count = 0
                log_connection_status("connected", f"{self.server_ip}:{self.server_port}")
            else:
                raise ConnectionError("Connection not established")
        
        except Exception as e:
            log_connection_status("failed", f"{self.server_ip}:{self.server_port} - {str(e)}")
            self.stats['connection_failures'] += 1
            self.connection_retry_count += 1
            self.connected = False
            
            if self.network_client:
                try:
                    self.network_client.close()
                except:
                    pass
                
                # Recreate client for next attempt
                self.network_client = NetworkClient(self.server_ip, self.server_port)
                self.network_client.set_event_callback(self._handle_received_event)
    
    def _handle_received_event(self, event: InputEvent) -> None:
        """Handle received input events from the server."""
        try:
            self.stats['events_received'] += 1
            self.last_event_time = time.time()
            
            # Log received event
            event_details = self._get_event_details(event)
            log_input_event(event.event_type.value, f"received: {event_details}")
            
            # Simulate the event
            success = self._simulate_event(event)
            
            if success:
                self.stats['events_simulated'] += 1
                log_input_event(event.event_type.value, f"simulated: {event_details}")
            else:
                self.stats['simulation_errors'] += 1
        
        except Exception as e:
            logger.error(f"Error handling received event: {e}")
            self.stats['simulation_errors'] += 1
    
    def _get_event_details(self, event: InputEvent) -> str:
        """Get human-readable details for an input event."""
        if event.event_type == EventType.MOUSE_MOVE:
            return f"pos({event.data.normalized_x:.3f}, {event.data.normalized_y:.3f})"
        elif event.event_type == EventType.MOUSE_CLICK:
            action = "press" if event.data.pressed else "release"
            return f"{event.data.button.value} {action}"
        elif event.event_type == EventType.MOUSE_SCROLL:
            return f"scroll({event.data.delta_x}, {event.data.delta_y})"
        elif event.event_type == EventType.KEYBOARD:
            action = "press" if event.data.pressed else "release"
            return f"key {event.data.key_code} {action}"
        else:
            return "unknown"
    
    def _simulate_event(self, event: InputEvent) -> bool:
        """Simulate an input event on the local system."""
        try:
            if event.event_type == EventType.MOUSE_MOVE:
                return self._simulate_mouse_move(event)
            elif event.event_type == EventType.MOUSE_CLICK:
                return self._simulate_mouse_click(event)
            elif event.event_type == EventType.MOUSE_SCROLL:
                return self._simulate_mouse_scroll(event)
            elif event.event_type == EventType.KEYBOARD:
                return self._simulate_keyboard(event)
            else:
                logger.warning(f"Unknown event type: {event.event_type}")
                return False
        
        except Exception as e:
            logger.error(f"Error simulating {event.event_type.value} event: {e}")
            return False
    
    def _simulate_mouse_move(self, event: InputEvent) -> bool:
        """Simulate mouse movement event."""
        data = event.data
        
        # Convert normalized coordinates to absolute coordinates
        abs_x, abs_y = self.coordinate_transformer.denormalize_coordinates(
            data.normalized_x, data.normalized_y, *self.screen_dimensions
        )
        
        # Simulate mouse movement
        self.input_simulation.move_mouse(abs_x, abs_y)
        logger.debug(f"Simulated mouse move to ({abs_x}, {abs_y})")
        return True
    
    def _simulate_mouse_click(self, event: InputEvent) -> bool:
        """Simulate mouse click event."""
        data = event.data
        
        # Convert normalized coordinates to absolute coordinates
        abs_x, abs_y = self.coordinate_transformer.denormalize_coordinates(
            data.normalized_x, data.normalized_y, *self.screen_dimensions
        )
        
        # Simulate mouse click
        self.input_simulation.click_mouse(data.button.value, data.pressed, abs_x, abs_y)
        action = "pressed" if data.pressed else "released"
        logger.debug(f"Simulated {data.button.value} mouse button {action} at ({abs_x}, {abs_y})")
        return True
    
    def _simulate_mouse_scroll(self, event: InputEvent) -> bool:
        """Simulate mouse scroll event."""
        data = event.data
        
        # Simulate mouse scroll
        self.input_simulation.scroll_mouse(data.delta_x, data.delta_y)
        logger.debug(f"Simulated mouse scroll ({data.delta_x}, {data.delta_y})")
        return True
    
    def _simulate_keyboard(self, event: InputEvent) -> bool:
        """Simulate keyboard event."""
        data = event.data
        
        # Simulate key press/release
        self.input_simulation.press_key(data.key_code, data.pressed)
        action = "pressed" if data.pressed else "released"
        logger.debug(f"Simulated key {data.key_code} {action}")
        return True
    
    def _display_startup_info(self) -> None:
        """Display startup information and configuration status."""
        logger.info("=" * 60)
        logger.info("InputFlow Client - Startup Information")
        logger.info("=" * 60)
        
        # Network configuration
        logger.info(f"Server: {self.server_ip}:{self.server_port}")
        logger.info(f"Platform: {self.platform_factory.platform.value}")
        logger.info(f"Screen: {self.screen_dimensions[0]}x{self.screen_dimensions[1]}")
        
        # Connection settings
        logger.info(f"Max retry attempts: {self.max_retry_attempts}")
        logger.info(f"Retry delay: {self.retry_delay}s")
        
        logger.info("=" * 60)
    
    def _display_statistics(self) -> None:
        """Display final statistics."""
        # Prepare statistics for logging
        stats = dict(self.stats)
        
        # Calculate success rates
        if self.stats['events_received'] > 0:
            simulation_rate = (self.stats['events_simulated'] / self.stats['events_received'])
            stats['simulation_success_rate'] = simulation_rate
        
        if self.stats['connection_attempts'] > 0:
            connection_rate = ((self.stats['connection_attempts'] - self.stats['connection_failures']) / 
                             self.stats['connection_attempts'])
            stats['connection_success_rate'] = connection_rate
        
        log_performance_stats(stats)


def setup_signal_handlers(client: InputFlowClient) -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        client.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main(config_path: Optional[str] = None, server_ip: Optional[str] = None, 
         server_port: Optional[int] = None, verbose: bool = False, log_file: Optional[str] = None):
    """Main entry point for the client application."""
    # Configure logging if not already configured
    if not logger._core.handlers:
        setup_logging(
            level="DEBUG" if verbose else "INFO",
            log_file=log_file,
            verbose=verbose
        )
    
    # Create and run client
    try:
        client = InputFlowClient(config_path)
        
        # Override server settings from command line if provided
        if server_ip:
            client.server_ip = server_ip
        if server_port:
            client.server_port = server_port
        
        setup_signal_handlers(client)
        client.run()
    
    except Exception as e:
        logger.error(f"Client startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()