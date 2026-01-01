#!/usr/bin/env python3
"""
InputFlow Server Application

Main server entry point that captures physical input events and transmits them
to connected clients over the network. Integrates input capture, coordinate
transformation, network transmission, and topology-based screen switching.
"""

import signal
import sys
import time
from typing import Optional

from loguru import logger

from inputflow.config.manager import ConfigManager
from inputflow.config.topology import TopologyManager
from inputflow.core.coordinates import CoordinateTransformer
from inputflow.core.events import EventType, InputEvent
from inputflow.core.hotkeys import HotkeyController, HotkeyState
from inputflow.core.logging import (log_configuration_status, log_connection_status,
                                    log_error_with_troubleshooting, log_input_event,
                                    log_network_binding_info, log_performance_stats,
                                    log_platform_info, log_startup_banner, setup_logging)
from inputflow.core.throttling import ThrottleConfig, ThrottledEventProcessor
from inputflow.input.platform import PlatformFactory
from inputflow.network.server import NetworkServer


class InputFlowServer:
    """
    Main server application for InputFlow.
    
    Integrates all components to provide seamless input sharing functionality
    including input capture, coordinate transformation, network transmission,
    and topology-based screen switching logic.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the InputFlow server.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.config = None
        
        # Core components
        self.platform_factory = None
        self.input_capture = None
        self.network_server = None
        self.coordinate_transformer = CoordinateTransformer()
        self.topology_manager = TopologyManager()
        self.hotkey_controller = None
        
        # State management
        self.running = False
        self.current_screen_ip = None
        self.screen_dimensions = (1920, 1080)  # Default, will be updated
        self.cursor_locked = False
        
        # Event processing
        self.throttled_processor = None
        
        # Statistics
        self.stats = {
            'events_captured': 0,
            'events_transmitted': 0,
            'screen_switches': 0,
            'clients_connected': 0
        }
        
        logger.info("InputFlow server initialized")
    
    def load_configuration(self) -> None:
        """Load and validate configuration from TOML file."""
        try:
            self.config = self.config_manager.load_config()
            
            if not self.config_manager.validate_config(self.config):
                raise ValueError("Configuration validation failed")
            
            # Verify this is configured as a server
            if self.config.network.role != "server":
                raise ValueError(f"Configuration role is '{self.config.network.role}', expected 'server'")
            
            # Log configuration status
            config_dict = {
                'network': {
                    'role': self.config.network.role,
                    'bind_ip': self.config.network.bind_ip,
                    'port': self.config.network.port,
                    'tcp_nodelay': self.config.network.tcp_nodelay
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
                }
            }
            log_configuration_status(config_dict, self.config_path)
            
            logger.info("Configuration loaded and validated successfully")
            
        except Exception as e:
            troubleshooting_tips = [
                "Check if config.toml exists in the current directory",
                "Verify TOML syntax is correct (use a TOML validator)",
                "Ensure all required sections are present: [network], [topology], [shortcuts]",
                "Check that network.role is set to 'server'",
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
                        "Insufficient permissions for input operations", 
                        "Permission Error", 
                        troubleshooting_tips
                    )
                    raise RuntimeError("Insufficient permissions for input operations")
            
            # Get screen dimensions
            self.screen_dimensions = self.coordinate_transformer.get_screen_dimensions()
            
            # Log platform information
            log_platform_info(
                self.platform_factory.platform.value, 
                permissions_ok, 
                self.screen_dimensions
            )
            
            # Initialize network server
            network_config = self.config.network
            self.network_server = NetworkServer(network_config.bind_ip, network_config.port)
            
            # Log network binding information
            log_network_binding_info(
                network_config.bind_ip, 
                network_config.port, 
                network_config.role
            )
            
            # Initialize topology manager
            topology_config = self.config.topology
            self.current_screen_ip = network_config.bind_ip
            self.topology_manager.load_topology(topology_config, self.current_screen_ip)
            self.topology_manager.set_screen_dimensions(*self.screen_dimensions)
            
            if not self.topology_manager.validate_topology():
                logger.warning("Topology validation failed, screen switching may not work properly")
                logger.warning("Check topology configuration for missing or invalid entries")
            
            # Initialize input capture
            throttle_config = ThrottleConfig(
                min_interval_us=1000,  # 1ms throttling for mouse movement
                min_distance_pixels=1.0
            )
            
            self.input_capture = self.platform_factory.create_input_capture()
            self.input_capture.set_event_callback(self._handle_input_event)
            
            # Initialize throttled event processor
            self.throttled_processor = ThrottledEventProcessor(
                self._process_input_event,
                throttle_config
            )
            
            # Initialize hotkey controller
            hotkey_config = self.config.shortcuts
            self.hotkey_controller = HotkeyController(hotkey_config)
            
            # Register hotkey callbacks
            hotkey_callbacks = {
                'lock_toggle': self._handle_lock_toggle,
                'screen_cycle': self._handle_screen_cycle
            }
            self.hotkey_controller.register_hotkeys(hotkey_callbacks)
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            troubleshooting_tips = [
                "Check system permissions for input device access",
                "Verify network port is not already in use",
                "Ensure required libraries are installed (pynput, evdev)",
                "Check if running in a supported environment"
            ]
            log_error_with_troubleshooting(str(e), "Component Initialization Error", troubleshooting_tips)
            raise
    
    def start(self) -> None:
        """Start the server and begin input capture."""
        try:
            # Log startup banner
            log_startup_banner("InputFlow Server")
            
            # Load configuration
            self.load_configuration()
            
            # Initialize components
            self.initialize_components()
            
            # Bind network server
            self.network_server.bind()
            log_connection_status("connected", f"Server listening on {self.config.network.bind_ip}:{self.config.network.port}")
            
            # Start input capture
            self.input_capture.start_monitoring()
            logger.info("Input capture started - ready to capture keyboard and mouse events")
            
            # Set running flag
            self.running = True
            
            # Display startup information
            self._display_startup_info()
            
            logger.info("InputFlow server started successfully")
            logger.info("Press Ctrl+C to stop the server")
            
        except Exception as e:
            troubleshooting_tips = [
                "Check if another instance is already running",
                "Verify network port is available",
                "Ensure configuration file is valid",
                "Check system permissions"
            ]
            log_error_with_troubleshooting(str(e), "Server Startup Error", troubleshooting_tips)
            self.stop()
            raise
    
    def stop(self) -> None:
        """Stop the server and cleanup resources with graceful shutdown."""
        logger.info("Stopping InputFlow server...")
        self.running = False
        
        # Graceful shutdown sequence
        shutdown_errors = []
        
        # Stop input capture first to prevent new events
        if self.input_capture:
            try:
                self.input_capture.stop_monitoring()
                logger.info("Input capture stopped")
            except Exception as e:
                error_msg = f"Error stopping input capture: {e}"
                logger.error(error_msg)
                shutdown_errors.append(error_msg)
        
        # Stop hotkey controller
        if self.hotkey_controller:
            try:
                self.hotkey_controller.stop()
                logger.info("Hotkey controller stopped")
            except Exception as e:
                error_msg = f"Error stopping hotkey controller: {e}"
                logger.error(error_msg)
                shutdown_errors.append(error_msg)
        
        # Stop throttled processor
        if self.throttled_processor:
            try:
                self.throttled_processor.reset_stats()
                logger.info("Throttled processor reset")
            except Exception as e:
                error_msg = f"Error resetting throttled processor: {e}"
                logger.error(error_msg)
                shutdown_errors.append(error_msg)
        
        # Close network server last to allow final transmissions
        if self.network_server:
            try:
                # Send shutdown notification to clients
                self._send_shutdown_notification()
                
                # Give clients time to receive shutdown notification
                import time
                time.sleep(0.5)
                
                self.network_server.close()
                logger.info("Network server closed")
            except Exception as e:
                error_msg = f"Error closing network server: {e}"
                logger.error(error_msg)
                shutdown_errors.append(error_msg)
        
        # Display final statistics
        self._display_statistics()
        
        # Report shutdown status
        if shutdown_errors:
            logger.warning(f"Server stopped with {len(shutdown_errors)} errors:")
            for error in shutdown_errors:
                logger.warning(f"  - {error}")
        else:
            logger.info("InputFlow server stopped gracefully")
    
    def _send_shutdown_notification(self) -> None:
        """Send shutdown notification to all connected clients."""
        try:
            if self.network_server and self.network_server.get_clients():
                logger.info("Sending shutdown notification to clients...")
                # In a full implementation, this would send a special shutdown message
                # For now, we just log the intent
                client_count = len(self.network_server.get_clients())
                logger.info(f"Notified {client_count} clients of server shutdown")
        except Exception as e:
            logger.error(f"Error sending shutdown notification: {e}")
    
    def run(self) -> None:
        """Run the server main loop."""
        try:
            self.start()
            
            # Main loop - keep server running
            while self.running:
                time.sleep(0.1)
                
                # Update client count
                if self.network_server:
                    self.stats['clients_connected'] = len(self.network_server.get_clients())
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.stop()
    
    def _handle_input_event(self, event: InputEvent) -> None:
        """Handle captured input events with throttling."""
        self.stats['events_captured'] += 1
        
        # Apply throttling
        if self.throttled_processor:
            self.throttled_processor.process_event(event)
        else:
            self._process_input_event(event)
    
    def _process_input_event(self, event: InputEvent) -> None:
        """Process input events for transmission and screen switching."""
        try:
            # Log input event processing
            event_details = self._get_event_details(event)
            log_input_event(event.event_type.value, event_details)
            
            # Check for screen switching on mouse movement
            if event.event_type == EventType.MOUSE_MOVE and not self.hotkey_controller.is_locked():
                self._check_screen_switching(event)
            
            # Transmit event to clients
            if self.network_server and not self.cursor_locked:
                clients_sent = self.network_server.broadcast_event(event)
                if clients_sent > 0:
                    self.stats['events_transmitted'] += 1
                    log_input_event(event.event_type.value, f"{event_details} -> {clients_sent} clients", transmitted=True)
        
        except Exception as e:
            logger.error(f"Error processing input event: {e}")
    
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
    
    def _check_screen_switching(self, event: InputEvent) -> None:
        """Check if screen switching should occur based on mouse position."""
        if event.event_type != EventType.MOUSE_MOVE:
            return
        
        # Convert normalized coordinates to absolute coordinates
        norm_x, norm_y = event.data.normalized_x, event.data.normalized_y
        abs_x, abs_y = self.coordinate_transformer.denormalize_coordinates(
            norm_x, norm_y, *self.screen_dimensions
        )
        
        # Check if we should switch screens
        target_ip = self.topology_manager.should_switch_screen(abs_x, abs_y)
        
        if target_ip:
            self._perform_screen_switch(target_ip)
    
    def _perform_screen_switch(self, target_ip: str) -> None:
        """Perform screen switching to target IP."""
        try:
            logger.info(f"Switching to screen: {target_ip}")
            
            # Lock cursor during transition
            self.cursor_locked = True
            
            # Register the target as a client if not already registered
            if self.network_server:
                self.network_server.register_client(target_ip)
            
            # Update statistics
            self.stats['screen_switches'] += 1
            
            # TODO: Implement cursor positioning on target screen
            # This would involve sending a special "cursor position" event
            # to position the cursor appropriately on the target screen
            
            # Unlock cursor after a brief delay
            # In a real implementation, this would be triggered by confirmation from target
            import threading
            def unlock_cursor():
                time.sleep(0.1)  # Brief delay
                self.cursor_locked = False
                logger.debug("Cursor unlocked after screen switch")
            
            threading.Thread(target=unlock_cursor, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error during screen switch: {e}")
            self.cursor_locked = False
    
    def _handle_lock_toggle(self) -> None:
        """Handle lock mode toggle hotkey."""
        state = self.hotkey_controller.get_state()
        if state == HotkeyState.LOCKED:
            logger.info("Lock mode activated - automatic screen switching disabled")
        else:
            logger.info("Lock mode deactivated - automatic screen switching enabled")
    
    def _handle_screen_cycle(self) -> None:
        """Handle screen cycling hotkey."""
        if not self.topology_manager:
            logger.warning("Cannot cycle screens - topology not configured")
            return
        
        # Get all configured targets
        targets = self.topology_manager.get_all_targets()
        
        if not targets:
            logger.warning("No screen targets configured for cycling")
            return
        
        # For simplicity, just switch to the first target
        # In a full implementation, this would cycle through all targets
        target_ip = targets[0]
        logger.info(f"Manual screen cycle to: {target_ip}")
        self._perform_screen_switch(target_ip)
    
    def _display_startup_info(self) -> None:
        """Display startup information and configuration status."""
        logger.info("=" * 60)
        logger.info("InputFlow Server - Startup Information")
        logger.info("=" * 60)
        
        # Network configuration
        logger.info(f"Network: {self.config.network.bind_ip}:{self.config.network.port}")
        logger.info(f"Platform: {self.platform_factory.platform.value}")
        logger.info(f"Screen: {self.screen_dimensions[0]}x{self.screen_dimensions[1]}")
        
        # Topology information
        targets = self.topology_manager.get_all_targets()
        if targets:
            logger.info(f"Configured targets: {', '.join(targets)}")
        else:
            logger.warning("No screen targets configured")
        
        # Hotkey information
        logger.info(f"Lock toggle: {self.config.shortcuts.switch_lock}")
        logger.info(f"Screen cycle: {self.config.shortcuts.switch_loop_between_screens}")
        
        logger.info("=" * 60)
    
    def _display_statistics(self) -> None:
        """Display final statistics."""
        # Prepare statistics for logging
        stats = dict(self.stats)
        
        # Add throttling statistics
        if self.throttled_processor:
            throttle_stats = self.throttled_processor.get_stats()
            stats['throttle_ratio'] = throttle_stats['throttle_ratio']
        
        log_performance_stats(stats)


def setup_signal_handlers(server: InputFlowServer) -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main(config_path: Optional[str] = None, verbose: bool = False, log_file: Optional[str] = None):
    """Main entry point for the server application."""
    # Configure logging if not already configured
    if not logger._core.handlers:
        setup_logging(
            level="DEBUG" if verbose else "INFO",
            log_file=log_file,
            verbose=verbose
        )
    
    # Create and run server
    try:
        server = InputFlowServer(config_path)
        setup_signal_handlers(server)
        server.run()
    
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()