import sys
import time
from typing import Optional

import click

from inputflow.config.manager import ConfigManager
from inputflow.core.events import InputEvent
from inputflow.core.logging import get_logger
from inputflow.input.capture import get_input_capture
from inputflow.input.simulation import get_input_simulation
from inputflow.network.client import NetworkClient
from inputflow.network.server import NetworkServer


@click.group()
@click.option(
    "--config",
    "config_path",
    default="config.toml.example",
    help="Path to the configuration file.",
)
@click.pass_context
def cli(ctx, config_path):
    """InputFlow: Cross-platform input sharing tool."""
    logger = get_logger("inputflow")
    config_manager = ConfigManager()

    try:
        config = config_manager.load_config(config_path)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    ctx.ensure_object(dict)
    ctx.obj["logger"] = logger
    ctx.obj["config"] = config


@cli.command()
@click.option(
    "--ip", default=None, help="IP address to bind the server to (overrides config)."
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="Port to bind the server to (overrides config).",
)
@click.pass_context
def server(ctx, ip: Optional[str], port: Optional[int]):
    """Runs InputFlow in server mode, capturing and sending input events."""
    logger = ctx.obj["logger"]
    config = ctx.obj["config"]

    # Override config with CLI arguments if provided
    if ip:
        config.network.bind_ip = ip
    if port:
        config.network.port = port

    server_instance = NetworkServer(logger=logger)

    # Event handler for captured input
    def event_handler(event: InputEvent):
        server_instance.send_event(event)

    try:
        server_instance.bind(config.network.bind_ip, config.network.port)

        input_capture = get_input_capture(
            logger=logger, config=config, event_callback=event_handler
        )
        input_capture.start_monitoring()

        logger.info("InputFlow server started. Press Ctrl+C to stop.")

        # Keep the main thread alive while input capture runs in its own threads
        # You might need a more sophisticated way to keep alive and handle shutdown
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"InputFlow server error: {e}")
    finally:
        # Check if input_capture was successfully initialized and started
        if (
            "input_capture" in locals()
            and hasattr(input_capture, "_monitoring")
            and input_capture._monitoring
        ):
            input_capture.stop_monitoring()
        server_instance.close()


@cli.command()
@click.option(
    "--server-ip",
    "ip",
    default=None,
    help="IP address of the InputFlow server (overrides config).",
)
@click.option(
    "--server-port",
    "port",
    type=int,
    default=None,
    help="Port of the InputFlow server (overrides config).",
)
@click.pass_context
def client(ctx, ip: Optional[str], port: Optional[int]):
    """Runs InputFlow in client mode, receiving and simulating input events."""
    logger = ctx.obj["logger"]
    config = ctx.obj["config"]

    # Override config with CLI arguments if provided
    if ip:
        config.network.server_ip = ip
    if port:
        config.network.port = port

    # Final check for server_ip
    target_server_ip = config.network.server_ip
    if not target_server_ip:
        if config.network.role == "client" and config.topology:
            # Attempt to find a server IP from topology if client role and topology is defined
            # This is a simplification; a full topology manager would be more complex.
            for entry in config.topology:
                if (
                    entry.self_ip == config.network.bind_ip
                ):  # Assuming bind_ip is client's IP
                    if entry.left:  # Try left neighbor
                        target_server_ip = entry.left
                        logger.info(
                            f"Using server IP from topology (left): {target_server_ip}"
                        )
                        break
                    elif entry.right:  # Try right neighbor
                        target_server_ip = entry.right
                        logger.info(
                            f"Using server IP from topology (right): {target_server_ip}"
                        )
                        break
            if not target_server_ip:
                logger.warning(
                    "No explicit server IP and no suitable topology entry found. Defaulting to localhost."
                )
                target_server_ip = "127.0.0.1"
        else:
            logger.warning(
                "No explicit server IP specified in config or CLI. Defaulting to localhost."
            )
            target_server_ip = "127.0.0.1"

    client_instance = NetworkClient(logger=logger)
    simulator_instance = get_input_simulation(logger=logger, config=config)

    try:
        client_instance.connect(target_server_ip, config.network.port)

        logger.info(
            f"InputFlow client connected to {target_server_ip}:{config.network.port}. Replicating events."
        )

        # Receive and replay events
        for event in client_instance.receive_events():
            simulator_instance.replay_event(event)

    except KeyboardInterrupt:
        logger.info("Client stopped by user.")
    except Exception as e:
        logger.error(f"InputFlow client error: {e}")
    finally:
        # Ensure virtual device is closed and client is closed
        if "simulator_instance" in locals() and hasattr(simulator_instance, "__del__"):
            simulator_instance.__del__()  # Calls the __del__ which closes the uinput device
        client_instance.close()


if __name__ == "__main__":
    cli(obj={})
