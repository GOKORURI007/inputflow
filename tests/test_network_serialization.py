"""Tests for network message serialization and deserialization."""

import time

from inputflow.core.events import EventType, InputEvent, MouseButton
from inputflow.network.messages import MessageType, NetworkMessage, NetworkMessageFactory


class TestNetworkSerialization:
    """Test network message serialization and deserialization."""
    
    def test_mouse_move_binary_serialization(self):
        """Test binary serialization of mouse move events."""
        # Create mouse move event
        event = InputEvent.mouse_move(0.5, 0.75)
        
        # Create network message
        message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
        
        # Serialize to binary
        binary_data = message.to_bytes(use_binary=True)
        
        # Deserialize
        deserialized = NetworkMessage.from_bytes(binary_data)
        
        # Verify
        assert deserialized.message_type == MessageType.INPUT_EVENT
        assert deserialized.payload["event_type"] == EventType.MOUSE_MOVE.value
        assert abs(deserialized.payload["normalized_x"] - 0.5) < 0.001
        assert abs(deserialized.payload["normalized_y"] - 0.75) < 0.001
    
    def test_mouse_click_binary_serialization(self):
        """Test binary serialization of mouse click events."""
        # Create mouse click event
        event = InputEvent.mouse_click(MouseButton.RIGHT, True, 0.25, 0.8)
        
        # Create network message
        message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
        
        # Serialize to binary
        binary_data = message.to_bytes(use_binary=True)
        
        # Deserialize
        deserialized = NetworkMessage.from_bytes(binary_data)
        
        # Verify
        assert deserialized.message_type == MessageType.INPUT_EVENT
        assert deserialized.payload["event_type"] == EventType.MOUSE_CLICK.value
        assert deserialized.payload["button"] == MouseButton.RIGHT.value
        assert deserialized.payload["pressed"] is True
        assert abs(deserialized.payload["normalized_x"] - 0.25) < 0.001
        assert abs(deserialized.payload["normalized_y"] - 0.8) < 0.001
    
    def test_mouse_scroll_binary_serialization(self):
        """Test binary serialization of mouse scroll events."""
        # Create mouse scroll event
        event = InputEvent.mouse_scroll(-5, 3)
        
        # Create network message
        message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
        
        # Serialize to binary
        binary_data = message.to_bytes(use_binary=True)
        
        # Deserialize
        deserialized = NetworkMessage.from_bytes(binary_data)
        
        # Verify
        assert deserialized.message_type == MessageType.INPUT_EVENT
        assert deserialized.payload["event_type"] == EventType.MOUSE_SCROLL.value
        assert deserialized.payload["delta_x"] == -5
        assert deserialized.payload["delta_y"] == 3
    
    def test_keyboard_binary_serialization(self):
        """Test binary serialization of keyboard events."""
        # Create keyboard event
        event = InputEvent.keyboard(65, True)  # 'A' key pressed
        
        # Create network message
        message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
        
        # Serialize to binary
        binary_data = message.to_bytes(use_binary=True)
        
        # Deserialize
        deserialized = NetworkMessage.from_bytes(binary_data)
        
        # Verify
        assert deserialized.message_type == MessageType.INPUT_EVENT
        assert deserialized.payload["event_type"] == EventType.KEYBOARD.value
        assert deserialized.payload["key_code"] == 65
        assert deserialized.payload["pressed"] is True
    
    def test_coordinate_normalization_bounds(self):
        """Test that coordinates are properly bounded to [0.0, 1.0] range."""
        # Create event with out-of-bounds coordinates
        event = InputEvent.mouse_move(-0.5, 1.5)
        
        # Create network message
        message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
        
        # Verify coordinates are clamped
        assert message.payload["normalized_x"] == 0.0
        assert message.payload["normalized_y"] == 1.0
    
    def test_json_fallback_serialization(self):
        """Test JSON serialization for non-input events."""
        # Create heartbeat message
        message = NetworkMessageFactory.create_heartbeat_message("127.0.0.1")
        
        # Serialize to JSON
        json_data = message.to_bytes(use_binary=False)
        
        # Deserialize
        deserialized = NetworkMessage.from_bytes(json_data)
        
        # Verify
        assert deserialized.message_type == MessageType.HEARTBEAT
        assert deserialized.payload["status"] == "alive"
        assert deserialized.source_ip == "127.0.0.1"
    
    def test_message_factory_round_trip(self):
        """Test converting InputEvent to NetworkMessage and back."""
        # Create original event
        original_event = InputEvent.mouse_click(MouseButton.LEFT, False, 0.3, 0.7)
        
        # Convert to network message
        message = NetworkMessageFactory.create_input_event_message(original_event, "127.0.0.1")
        
        # Convert back to input event
        recovered_event = NetworkMessageFactory.message_to_input_event(message)
        
        # Verify
        assert recovered_event is not None
        assert recovered_event.event_type == original_event.event_type
        assert recovered_event.data.button == original_event.data.button
        assert recovered_event.data.pressed == original_event.data.pressed
        assert abs(recovered_event.data.normalized_x - original_event.data.normalized_x) < 0.001
        assert abs(recovered_event.data.normalized_y - original_event.data.normalized_y) < 0.001
    
    def test_timestamp_handling(self):
        """Test that timestamps are properly handled in serialization."""
        # Create event
        event = InputEvent.mouse_move(0.5, 0.5)
        
        # Create message
        message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
        
        # Verify timestamp is set
        assert message.timestamp > 0
        assert abs(message.timestamp - time.time()) < 1.0  # Within 1 second
        
        # Serialize and deserialize
        binary_data = message.to_bytes(use_binary=True)
        deserialized = NetworkMessage.from_bytes(binary_data)
        
        # Verify timestamp is preserved (with some precision loss due to binary format)
        assert abs(deserialized.timestamp - message.timestamp) < 0.01