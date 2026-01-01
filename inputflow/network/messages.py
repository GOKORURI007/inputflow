"""Network message data structures for InputFlow."""

import json
import struct
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from inputflow.core.events import EventType, InputEvent, MouseButton


class MessageType(Enum):
    """Types of network messages."""
    INPUT_EVENT = "input_event"
    HEARTBEAT = "heartbeat"
    HANDSHAKE = "handshake"
    ERROR = "error"


@dataclass
class NetworkMessage:
    """Base network message structure."""
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: float
    source_ip: Optional[str] = None
    
    def to_bytes(self, use_binary: bool = True) -> bytes:
        """Serialize message to bytes for network transmission.
        
        Args:
            use_binary: If True, use binary format for input events, otherwise use JSON
            
        Returns:
            Serialized message bytes
        """
        if use_binary and self.message_type == MessageType.INPUT_EVENT:
            return self._to_binary_bytes()
        else:
            return self._to_json_bytes()
    
    def _to_binary_bytes(self) -> bytes:
        """Serialize input event message to efficient binary format.
        
        Binary format:
        - Header (12 bytes): magic(2) + version(1) + event_type(1) + timestamp(8)
        - Payload: varies by event type
        """
        if self.message_type != MessageType.INPUT_EVENT:
            raise ValueError("Binary format only supported for input events")
        
        # Magic number and version
        header = struct.pack('>HB', 0x494E, 1)  # 'IN' + version 1
        
        # Event type mapping
        event_type_map = {
            EventType.MOUSE_MOVE: 1,
            EventType.MOUSE_CLICK: 2,
            EventType.MOUSE_SCROLL: 3,
            EventType.KEYBOARD: 4
        }
        
        event_type_byte = event_type_map.get(EventType(self.payload["event_type"]), 0)
        header += struct.pack('B', event_type_byte)
        
        # Timestamp (8 bytes, microseconds since epoch as 64-bit integer)
        timestamp_us = int(self.timestamp * 1_000_000)
        header += struct.pack('>Q', timestamp_us)
        
        # Event-specific payload
        payload_bytes = self._serialize_event_payload()
        
        return header + payload_bytes
    
    def _serialize_event_payload(self) -> bytes:
        """Serialize event-specific payload to binary format."""
        event_type = EventType(self.payload["event_type"])
        
        if event_type == EventType.MOUSE_MOVE:
            # Mouse move: normalized_x(4) + normalized_y(4)
            x = max(0.0, min(1.0, self.payload["normalized_x"]))
            y = max(0.0, min(1.0, self.payload["normalized_y"]))
            return struct.pack('>ff', x, y)
        
        elif event_type == EventType.MOUSE_CLICK:
            # Mouse click: button(1) + pressed(1) + normalized_x(4) + normalized_y(4)
            button_map = {
                MouseButton.LEFT: 1,
                MouseButton.RIGHT: 2,
                MouseButton.MIDDLE: 3,
                MouseButton.X1: 4,
                MouseButton.X2: 5
            }
            button_byte = button_map.get(MouseButton(self.payload["button"]), 1)
            pressed_byte = 1 if self.payload["pressed"] else 0
            x = max(0.0, min(1.0, self.payload["normalized_x"]))
            y = max(0.0, min(1.0, self.payload["normalized_y"]))
            return struct.pack('>BBff', button_byte, pressed_byte, x, y)
        
        elif event_type == EventType.MOUSE_SCROLL:
            # Mouse scroll: delta_x(2) + delta_y(2)
            dx = max(-32768, min(32767, self.payload["delta_x"]))
            dy = max(-32768, min(32767, self.payload["delta_y"]))
            return struct.pack('>hh', dx, dy)
        
        elif event_type == EventType.KEYBOARD:
            # Keyboard: key_code(4) + pressed(1)
            key_code = self.payload["key_code"] & 0xFFFFFFFF
            pressed_byte = 1 if self.payload["pressed"] else 0
            return struct.pack('>IB', key_code, pressed_byte)
        
        return b''
    
    def _to_json_bytes(self) -> bytes:
        """Serialize message to JSON format (fallback for non-input events)."""
        # Create message dictionary
        message_dict = {
            "type": self.message_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source_ip": self.source_ip
        }
        
        # Convert to JSON and encode
        json_data = json.dumps(message_dict, separators=(',', ':')).encode('utf-8')
        
        # Prepend length header (4 bytes, big-endian)
        length = len(json_data)
        return struct.pack('>I', length) + json_data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'NetworkMessage':
        """Deserialize message from bytes.
        
        Args:
            data: Serialized message bytes
            
        Returns:
            Deserialized NetworkMessage
        """
        if len(data) < 4:
            raise ValueError("Invalid message: too short")
        
        # Check if this is binary format (starts with magic number)
        if len(data) >= 12 and data[:2] == b'\x49\x4E':  # 'IN' magic
            return cls._from_binary_bytes(data)
        else:
            return cls._from_json_bytes(data)
    
    @classmethod
    def _from_binary_bytes(cls, data: bytes) -> 'NetworkMessage':
        """Deserialize binary format message."""
        if len(data) < 12:
            raise ValueError("Invalid binary message: too short")
        
        # Parse header
        magic, version, event_type_byte, timestamp_us = struct.unpack('>HBBQ', data[:12])
        
        if magic != 0x494E:
            raise ValueError("Invalid binary message: bad magic number")
        
        if version != 1:
            raise ValueError(f"Unsupported binary message version: {version}")
        
        # Map event type
        event_type_map = {
            1: EventType.MOUSE_MOVE,
            2: EventType.MOUSE_CLICK,
            3: EventType.MOUSE_SCROLL,
            4: EventType.KEYBOARD
        }
        
        event_type = event_type_map.get(event_type_byte)
        if not event_type:
            raise ValueError(f"Unknown event type: {event_type_byte}")
        
        # Parse payload
        payload_data = data[12:]
        payload = cls._deserialize_event_payload(event_type, payload_data)
        
        # Convert timestamp back to seconds
        timestamp = timestamp_us / 1_000_000.0
        
        return cls(
            message_type=MessageType.INPUT_EVENT,
            payload=payload,
            timestamp=timestamp
        )
    
    @classmethod
    def _deserialize_event_payload(cls, event_type: EventType, data: bytes) -> Dict[str, Any]:
        """Deserialize event-specific payload from binary format."""
        payload = {"event_type": event_type.value}
        
        if event_type == EventType.MOUSE_MOVE:
            if len(data) < 8:
                raise ValueError("Invalid mouse move payload")
            x, y = struct.unpack('>ff', data[:8])
            payload.update({
                "normalized_x": x,
                "normalized_y": y
            })
        
        elif event_type == EventType.MOUSE_CLICK:
            if len(data) < 10:
                raise ValueError("Invalid mouse click payload")
            button_byte, pressed_byte, x, y = struct.unpack('>BBff', data[:10])
            
            button_map = {
                1: MouseButton.LEFT,
                2: MouseButton.RIGHT,
                3: MouseButton.MIDDLE,
                4: MouseButton.X1,
                5: MouseButton.X2
            }
            button = button_map.get(button_byte, MouseButton.LEFT)
            
            payload.update({
                "button": button.value,
                "pressed": pressed_byte == 1,
                "normalized_x": x,
                "normalized_y": y
            })
        
        elif event_type == EventType.MOUSE_SCROLL:
            if len(data) < 4:
                raise ValueError("Invalid mouse scroll payload")
            dx, dy = struct.unpack('>hh', data[:4])
            payload.update({
                "delta_x": dx,
                "delta_y": dy
            })
        
        elif event_type == EventType.KEYBOARD:
            if len(data) < 5:
                raise ValueError("Invalid keyboard payload")
            key_code, pressed_byte = struct.unpack('>IB', data[:5])
            payload.update({
                "key_code": key_code,
                "pressed": pressed_byte == 1
            })
        
        return payload
    
    @classmethod
    def _from_json_bytes(cls, data: bytes) -> 'NetworkMessage':
        """Deserialize JSON format message (fallback)."""
        if len(data) < 4:
            raise ValueError("Invalid message: too short")
        
        # Extract length header
        length = struct.unpack('>I', data[:4])[0]
        
        if len(data) < 4 + length:
            raise ValueError("Invalid message: incomplete data")
        
        # Extract and decode JSON data
        json_data = data[4:4+length].decode('utf-8')
        message_dict = json.loads(json_data)
        
        return cls(
            message_type=MessageType(message_dict["type"]),
            payload=message_dict["payload"],
            timestamp=message_dict["timestamp"],
            source_ip=message_dict.get("source_ip")
        )


class NetworkMessageFactory:
    """Factory for creating network messages from input events."""
    
    @staticmethod
    def create_input_event_message(event: InputEvent, source_ip: str) -> NetworkMessage:
        """Create a network message from an input event.
        
        Args:
            event: Input event to serialize
            source_ip: Source IP address
            
        Returns:
            NetworkMessage containing the input event
        """
        # Use event timestamp or current time
        timestamp = event.data.timestamp if hasattr(event.data, 'timestamp') else time.time()
        
        # Convert event data to serializable format
        payload = {
            "event_type": event.event_type.value,
            "timestamp": timestamp
        }
        
        if event.event_type == EventType.MOUSE_MOVE:
            # Ensure normalized coordinates are within valid range
            norm_x = max(0.0, min(1.0, event.data.normalized_x))
            norm_y = max(0.0, min(1.0, event.data.normalized_y))
            payload.update({
                "normalized_x": norm_x,
                "normalized_y": norm_y
            })
        elif event.event_type == EventType.MOUSE_CLICK:
            # Ensure normalized coordinates are within valid range
            norm_x = max(0.0, min(1.0, event.data.normalized_x))
            norm_y = max(0.0, min(1.0, event.data.normalized_y))
            payload.update({
                "button": event.data.button.value,
                "pressed": event.data.pressed,
                "normalized_x": norm_x,
                "normalized_y": norm_y
            })
        elif event.event_type == EventType.MOUSE_SCROLL:
            payload.update({
                "delta_x": event.data.delta_x,
                "delta_y": event.data.delta_y
            })
        elif event.event_type == EventType.KEYBOARD:
            payload.update({
                "key_code": event.data.key_code,
                "pressed": event.data.pressed
            })
        
        return NetworkMessage(
            message_type=MessageType.INPUT_EVENT,
            payload=payload,
            timestamp=timestamp,
            source_ip=source_ip
        )
    
    @staticmethod
    def create_heartbeat_message(source_ip: str) -> NetworkMessage:
        """Create a heartbeat message.
        
        Args:
            source_ip: Source IP address
            
        Returns:
            NetworkMessage containing heartbeat
        """
        return NetworkMessage(
            message_type=MessageType.HEARTBEAT,
            payload={"status": "alive"},
            timestamp=time.time(),
            source_ip=source_ip
        )
    
    @staticmethod
    def create_handshake_message(source_ip: str, client_info: Optional[str] = None) -> NetworkMessage:
        """Create a handshake message.
        
        Args:
            source_ip: Source IP address
            client_info: Optional client information
            
        Returns:
            NetworkMessage containing handshake
        """
        payload = {"client_info": client_info or "InputFlow client"}
        return NetworkMessage(
            message_type=MessageType.HANDSHAKE,
            payload=payload,
            timestamp=time.time(),
            source_ip=source_ip
        )
    
    @staticmethod
    def create_error_message(error_msg: str, source_ip: str) -> NetworkMessage:
        """Create an error message.
        
        Args:
            error_msg: Error message text
            source_ip: Source IP address
            
        Returns:
            NetworkMessage containing error
        """
        return NetworkMessage(
            message_type=MessageType.ERROR,
            payload={"error": error_msg},
            timestamp=time.time(),
            source_ip=source_ip
        )
    
    @staticmethod
    def message_to_input_event(message: NetworkMessage) -> Optional[InputEvent]:
        """Convert network message back to InputEvent.
        
        Args:
            message: Network message containing input event
            
        Returns:
            InputEvent if conversion successful, None otherwise
        """
        if message.message_type != MessageType.INPUT_EVENT:
            return None
        
        try:
            payload = message.payload
            event_type = EventType(payload["event_type"])
            
            if event_type == EventType.MOUSE_MOVE:
                return InputEvent.mouse_move(
                    normalized_x=payload["normalized_x"],
                    normalized_y=payload["normalized_y"]
                )
            elif event_type == EventType.MOUSE_CLICK:
                return InputEvent.mouse_click(
                    button=MouseButton(payload["button"]),
                    pressed=payload["pressed"],
                    normalized_x=payload["normalized_x"],
                    normalized_y=payload["normalized_y"]
                )
            elif event_type == EventType.MOUSE_SCROLL:
                return InputEvent.mouse_scroll(
                    delta_x=payload["delta_x"],
                    delta_y=payload["delta_y"]
                )
            elif event_type == EventType.KEYBOARD:
                return InputEvent.keyboard(
                    key_code=payload["key_code"],
                    pressed=payload["pressed"]
                )
                
        except Exception as e:
            # Log error but don't raise to avoid breaking the network loop
            return None
        
        return None