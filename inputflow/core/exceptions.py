"""Base exception classes for InputFlow error handling."""


class InputFlowError(Exception):
    """Base exception class for all InputFlow errors."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ConfigurationError(InputFlowError):
    """Raised when there are configuration-related errors."""
    pass


class NetworkError(InputFlowError):
    """Raised when there are network communication errors."""
    pass


class InputCaptureError(InputFlowError):
    """Raised when there are input capture errors."""
    pass


class InputSimulationError(InputFlowError):
    """Raised when there are input simulation errors."""
    pass


class PlatformError(InputFlowError):
    """Raised when there are platform-specific errors."""
    pass


class PermissionError(InputFlowError):
    """Raised when there are permission-related errors."""
    pass


class TopologyError(InputFlowError):
    """Raised when there are topology configuration errors."""
    pass


class CoordinateTransformError(InputFlowError):
    """Raised when there are coordinate transformation errors."""
    pass


class HotkeyError(InputFlowError):
    """Raised when there are hotkey registration or handling errors."""
    pass