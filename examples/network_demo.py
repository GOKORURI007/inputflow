#!/usr/bin/env python3
"""
Network communication demonstration for InputFlow.

This script demonstrates the basic network communication functionality
between server and client components.
"""

import time

from inputflow.core.events import InputEvent, MouseClickEvent
from inputflow.network.client import NetworkClient
from inputflow.network.server import NetworkServer


def demo_server_client():
    """Demonstrate basic server-client communication."""
    print("=== InputFlow Network Communication Demo ===\n")
    
    # Create and start server
    print("1. Starting server on 127.0.0.1:9999...")
    server = NetworkServer("127.0.0.1", 9999)
    server.bind()
    print("   Server started successfully!")
    
    # Create and connect client
    print("\n2. Connecting client to server...")
    client = NetworkClient("127.0.0.1", 9999)
    client.connect()
    print("   Client connected successfully!")
    
    # Set up event callback
    received_events = []
    def event_callback(event):
        received_events.append(event)
        print(f"   Received: {event.event_type.value}")
        if hasattr(event.data, 'normalized_x'):
            print(f"     Position: ({event.data.normalized_x:.3f}, {event.data.normalized_y:.3f})")
        if hasattr(event.data, 'button'):
            print(f"     Button: {event.data.button.value}, Pressed: {event.data.pressed}")
        if hasattr(event.data, 'delta_x'):
            print(f"     Scroll: ({event.data.delta_x}, {event.data.delta_y})")
        if hasattr(event.data, 'key_code'):
            print(f"     Key: {event.data.key_code}, Pressed: {event.data.pressed}")
    
    client.set_event_callback(event_callback)
    
    # Register client with server
    print("\n3. Registering client with server...")
    server.register_client("127.0.0.1")
    print("   Client registered!")
    
    # Send test events
    print("\n4. Sending test events...")
    test_events = [
        ("Mouse Move", InputEvent.mouse_move(0.5, 0.3)),
        ("Mouse Click", InputEvent.mouse_click(MouseButton.LEFT, True, 0.7, 0.8)),
        ("Mouse Release", InputEvent.mouse_click(MouseButton.LEFT, False, 0.7, 0.8)),
        ("Mouse Scroll", InputEvent.mouse_scroll(0, -3)),
        ("Key Press", InputEvent.keyboard(65, True)),  # 'A' key
        ("Key Release", InputEvent.keyboard(65, False)),
    ]
    
    for event_name, event in test_events:
        print(f"   Sending: {event_name}")
        success = server.send_event(event, "127.0.0.1", 9999)
        if success:
            print("     ✓ Sent successfully")
        else:
            print("     ✗ Failed to send")
        time.sleep(0.1)  # Small delay between events
    
    # Wait for events to be received
    print("\n5. Waiting for events to be received...")
    time.sleep(0.5)
    
    # Show results
    print("\n6. Results:")
    print(f"   Events sent: {len(test_events)}")
    print(f"   Events received: {len(received_events)}")
    
    if len(received_events) == len(test_events):
        print("   ✓ All events received successfully!")
    else:
        print("   ⚠ Some events may have been lost")
    
    # Cleanup
    print("\n7. Cleaning up...")
    client.close()
    server.close()
    print("   Cleanup complete!")
    
    print("\n=== Demo Complete ===")


def demo_binary_vs_json():
    """Demonstrate binary vs JSON serialization performance."""
    print("\n=== Binary vs JSON Serialization Demo ===\n")
    
    from inputflow.network.messages import NetworkMessageFactory
    
    # Create test event
    event = InputEvent.mouse_move(0.123456789, 0.987654321)
    message = NetworkMessageFactory.create_input_event_message(event, "127.0.0.1")
    
    # Test binary serialization
    print("1. Binary serialization:")
    binary_data = message.to_bytes(use_binary=True)
    print(f"   Size: {len(binary_data)} bytes")
    print(f"   Data: {binary_data.hex()}")
    
    # Test JSON serialization
    print("\n2. JSON serialization:")
    json_data = message.to_bytes(use_binary=False)
    print(f"   Size: {len(json_data)} bytes")
    print(f"   Data: {json_data[:100]}..." if len(json_data) > 100 else f"   Data: {json_data}")
    
    # Show size difference
    size_reduction = (len(json_data) - len(binary_data)) / len(json_data) * 100
    print("\n3. Comparison:")
    print(f"   Binary format is {size_reduction:.1f}% smaller")
    print(f"   Space saved: {len(json_data) - len(binary_data)} bytes")
    
    # Test round-trip accuracy
    print("\n4. Round-trip accuracy test:")
    
    # Binary round-trip
    binary_recovered = message.from_bytes(binary_data)
    binary_event = NetworkMessageFactory.message_to_input_event(binary_recovered)
    
    # JSON round-trip
    json_recovered = message.from_bytes(json_data)
    json_event = NetworkMessageFactory.message_to_input_event(json_recovered)
    
    print(f"   Original:  x={event.data.normalized_x:.9f}, y={event.data.normalized_y:.9f}")
    print(f"   Binary:    x={binary_event.data.normalized_x:.9f}, y={binary_event.data.normalized_y:.9f}")
    print(f"   JSON:      x={json_event.data.normalized_x:.9f}, y={json_event.data.normalized_y:.9f}")
    
    # Check precision
    binary_error_x = abs(binary_event.data.normalized_x - event.data.normalized_x)
    binary_error_y = abs(binary_event.data.normalized_y - event.data.normalized_y)
    json_error_x = abs(json_event.data.normalized_x - event.data.normalized_x)
    json_error_y = abs(json_event.data.normalized_y - event.data.normalized_y)
    
    print("\n5. Precision comparison:")
    print(f"   Binary error: x={binary_error_x:.2e}, y={binary_error_y:.2e}")
    print(f"   JSON error:   x={json_error_x:.2e}, y={json_error_y:.2e}")
    
    if binary_error_x < 0.001 and binary_error_y < 0.001:
        print("   ✓ Binary format maintains sufficient precision")
    else:
        print("   ⚠ Binary format may have precision issues")


if __name__ == "__main__":
    try:
        demo_server_client()
        demo_binary_vs_json()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()