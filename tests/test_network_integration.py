"""Integration tests for network server and client communication."""

from inputflow.core.events import InputEvent, MouseButton
from inputflow.network import NetworkClient, NetworkServer


class TestNetworkIntegration:
    """Test network server and client integration."""
    
    def test_server_client_basic_functionality(self):
        """Test that server and client can be created and configured properly."""
        # Test server creation and binding
        server = NetworkServer("127.0.0.1", 9998)
        server.bind()
        
        # Test client creation and connection
        client = NetworkClient("127.0.0.1", 9998)
        client.connect()
        
        try:
            # Test that server can register clients
            server.register_client("127.0.0.1")
            clients = server.get_clients()
            assert "127.0.0.1" in clients
            
            # Test that client reports not connected initially (no heartbeat)
            assert not client.is_connected()
            
        finally:
            client.close()
            server.close()
    
    def test_message_serialization_integration(self):
        """Test that messages can be serialized and deserialized properly."""
        from inputflow.network.messages import NetworkMessageFactory
        
        # Test different event types
        test_events = [
            InputEvent.mouse_move(0.5, 0.5),
            InputEvent.mouse_click(MouseButton.LEFT, True, 0.3, 0.7),
            InputEvent.mouse_scroll(1, -2),
            InputEvent.keyboard(65, True)
        ]
        
        for event in test_events:
            # Create network message
            message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
            
            # Serialize to binary
            binary_data = message.to_bytes(use_binary=True)
            
            # Deserialize
            deserialized = message.from_bytes(binary_data)
            
            # Convert back to input event
            recovered_event = NetworkMessageFactory.message_to_input_event(deserialized)
            
            # Verify event type matches
            assert recovered_event.event_type == event.event_type
            
            # Verify event-specific data
            if event.event_type.value == "mouse_move":
                assert abs(recovered_event.data.normalized_x - event.data.normalized_x) < 0.001
                assert abs(recovered_event.data.normalized_y - event.data.normalized_y) < 0.001
            elif event.event_type.value == "mouse_click":
                assert recovered_event.data.button == event.data.button
                assert recovered_event.data.pressed == event.data.pressed
                assert abs(recovered_event.data.normalized_x - event.data.normalized_x) < 0.001
                assert abs(recovered_event.data.normalized_y - event.data.normalized_y) < 0.001
            elif event.event_type.value == "mouse_scroll":
                assert recovered_event.data.delta_x == event.data.delta_x
                assert recovered_event.data.delta_y == event.data.delta_y
            elif event.event_type.value == "keyboard":
                assert recovered_event.data.key_code == event.data.key_code
                assert recovered_event.data.pressed == event.data.pressed
    
    def test_coordinate_normalization_in_network(self):
        """Test that coordinates are properly normalized in network messages."""
        from inputflow.network.messages import NetworkMessageFactory
        
        # Test with out-of-bounds coordinates
        event = InputEvent.mouse_move(-0.5, 1.5)
        message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
        
        # Verify coordinates are clamped to [0.0, 1.0]
        assert message.payload["normalized_x"] == 0.0
        assert message.payload["normalized_y"] == 1.0
        
        # Test serialization preserves clamping
        binary_data = message.to_bytes(use_binary=True)
        deserialized = message.from_bytes(binary_data)
        
        assert deserialized.payload["normalized_x"] == 0.0
        assert deserialized.payload["normalized_y"] == 1.0