"""Logging configuration for InputFlow using loguru."""

import sys
from typing import Optional

from loguru import logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    verbose: bool = False
) -> None:
    """
    Configure logging for InputFlow.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
        verbose: Enable verbose logging with more detailed format
    """
    # Remove default logger
    logger.remove()
    
    # Determine log level
    if verbose:
        level = "DEBUG"
    
    # Configure console logging format
    if verbose:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    else:
        format_string = (
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        )
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=format_string,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler if specified
    if log_file:
        logger.add(
            log_file,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
            level=level,
            rotation="10 MB",
            retention="7 days",
            compression="gz",
            backtrace=True,
            diagnose=True
        )
    
    logger.info(f"Logging initialized with level: {level}")
    if log_file:
        logger.info(f"Log file: {log_file}")


def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logger.bind(name=name)


def log_startup_banner(app_name: str, version: str = "0.1.0") -> None:
    """Log application startup banner with version information."""
    logger.info("=" * 60)
    logger.info(f"{app_name} v{version}")
    logger.info("Cross-platform keyboard and mouse sharing tool")
    logger.info("=" * 60)


def log_configuration_status(config_data: dict, config_path: Optional[str] = None) -> None:
    """Log configuration status and key settings."""
    logger.info("Configuration Status:")
    logger.info("-" * 30)
    
    if config_path:
        logger.info(f"Config file: {config_path}")
    else:
        logger.info("Config file: config.toml (default)")
    
    # Log network configuration
    if 'network' in config_data:
        network = config_data['network']
        logger.info(f"Network role: {network.get('role', 'unknown')}")
        logger.info(f"Bind address: {network.get('bind_ip', 'unknown')}:{network.get('port', 'unknown')}")
        logger.info(f"TCP no-delay: {network.get('tcp_nodelay', False)}")
    
    # Log topology information
    if 'topology' in config_data and config_data['topology']:
        topology_count = len(config_data['topology'])
        logger.info(f"Topology entries: {topology_count}")
        for i, entry in enumerate(config_data['topology']):
            logger.info(f"  Entry {i+1}: {entry.get('self_ip', 'unknown')}")
    else:
        logger.warning("No topology configuration found")
    
    # Log hotkey configuration
    if 'shortcuts' in config_data:
        shortcuts = config_data['shortcuts']
        logger.info(f"Lock toggle hotkey: {shortcuts.get('switch_lock', 'unknown')}")
        logger.info(f"Screen cycle hotkey: {shortcuts.get('switch_loop_between_screens', 'unknown')}")
    
    logger.info("-" * 30)


def log_network_binding_info(bind_ip: str, port: int, role: str) -> None:
    """Log network binding information."""
    logger.info("Network Binding Information:")
    logger.info("-" * 30)
    logger.info(f"Role: {role.upper()}")
    logger.info(f"Binding to: {bind_ip}:{port}")
    
    if role == "server":
        logger.info("Waiting for client connections...")
        logger.info("Clients can connect using this server address")
    else:
        logger.info(f"Will connect to server at: {bind_ip}:{port}")
    
    logger.info("-" * 30)


def log_platform_info(platform: str, permissions_ok: bool, screen_dimensions: tuple) -> None:
    """Log platform and system information."""
    logger.info("Platform Information:")
    logger.info("-" * 30)
    logger.info(f"Operating system: {platform}")
    logger.info(f"Screen resolution: {screen_dimensions[0]}x{screen_dimensions[1]}")
    
    if permissions_ok:
        logger.info("System permissions: OK")
    else:
        logger.warning("System permissions: INSUFFICIENT")
        logger.warning("Some features may not work properly")
    
    logger.info("-" * 30)


def log_input_event(event_type: str, details: str, transmitted: bool = False) -> None:
    """Log input event processing with details."""
    if transmitted:
        logger.debug(f"Event transmitted: {event_type} - {details}")
    else:
        logger.debug(f"Event captured: {event_type} - {details}")


def log_error_with_troubleshooting(error_msg: str, error_type: str, troubleshooting_tips: list) -> None:
    """Log error with troubleshooting guidance."""
    logger.error("=" * 60)
    logger.error(f"ERROR: {error_type}")
    logger.error("=" * 60)
    logger.error(f"Details: {error_msg}")
    logger.error("")
    logger.error("Troubleshooting Tips:")
    for i, tip in enumerate(troubleshooting_tips, 1):
        logger.error(f"  {i}. {tip}")
    logger.error("=" * 60)


def log_connection_status(status: str, details: str = "") -> None:
    """Log connection status changes."""
    if status == "connected":
        logger.info(f"✓ Connection established: {details}")
    elif status == "disconnected":
        logger.warning(f"✗ Connection lost: {details}")
    elif status == "connecting":
        logger.info(f"⟳ Connecting: {details}")
    elif status == "failed":
        logger.error(f"✗ Connection failed: {details}")
    else:
        logger.info(f"Connection status: {status} - {details}")


def log_performance_stats(stats: dict) -> None:
    """Log performance statistics."""
    logger.info("Performance Statistics:")
    logger.info("-" * 30)
    for key, value in stats.items():
        formatted_key = key.replace('_', ' ').title()
        if isinstance(value, float) and 0 < value < 1:
            logger.info(f"{formatted_key}: {value:.2%}")
        else:
            logger.info(f"{formatted_key}: {value}")
    logger.info("-" * 30)


# Create module-level loggers for different components
network_logger = get_logger("network")
input_logger = get_logger("input")
config_logger = get_logger("config")
core_logger = get_logger("core")