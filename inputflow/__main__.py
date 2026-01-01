#!/usr/bin/env python3
"""
InputFlow main entry point.

Allows running InputFlow as a module: python -m inputflow [server|client]
Provides a command-line interface without graphical components.
"""

import sys
from pathlib import Path

import click

from inputflow.core.logging import setup_logging


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """InputFlow - Cross-platform keyboard and mouse sharing tool"""
    pass


@cli.command()
@click.option("--config", "-c", type=click.Path(),
              help="Path to configuration file (default: config.toml in current directory)")
@click.option("--verbose", "-v", is_flag=True,
              help="Enable verbose logging with detailed debug information")
@click.option("--log-file", type=click.Path(),
              help="Write logs to specified file in addition to console output")
def server(config, verbose, log_file):
    """Run as input capture server"""
    # Setup logging based on arguments
    setup_logging(
        level="DEBUG" if verbose else "INFO",
        log_file=log_file,
        verbose=verbose
    )

    # Validate configuration file path if provided
    if config:
        config_path = Path(config)
        if not config_path.exists():
            click.echo(f"Error: Configuration file not found: {config}", err=True)
            sys.exit(1)
        if not config_path.is_file():
            click.echo(f"Error: Configuration path is not a file: {config}", err=True)
            sys.exit(1)

    # Run the server
    try:
        from inputflow.server import main as server_main
        server_main(
            config_path=config,
            verbose=verbose,
            log_file=log_file
        )
    except KeyboardInterrupt:
        click.echo("\nShutdown requested by user", err=True)
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", type=click.Path(),
              help="Path to configuration file (default: config.toml in current directory)")
@click.option("--server", "-s", type=str,
              help="Server IP address (overrides config file setting)")
@click.option("--port", "-p", type=int,
              help="Server port number (overrides config file setting)")
@click.option("--verbose", "-v", is_flag=True,
              help="Enable verbose logging with detailed debug information")
@click.option("--log-file", type=click.Path(),
              help="Write logs to specified file in addition to console output")
def client(config, server, port, verbose, log_file):
    """Run as input simulation client"""
    # Setup logging based on arguments
    setup_logging(
        level="DEBUG" if verbose else "INFO",
        log_file=log_file,
        verbose=verbose
    )

    # Validate configuration file path if provided
    if config:
        config_path = Path(config)
        if not config_path.exists():
            click.echo(f"Error: Configuration file not found: {config}", err=True)
            sys.exit(1)
        if not config_path.is_file():
            click.echo(f"Error: Configuration path is not a file: {config}", err=True)
            sys.exit(1)

    # Run the client
    try:
        from inputflow.client import main as client_main
        client_main(
            config_path=config,
            server_ip=server,
            server_port=port,
            verbose=verbose,
            log_file=log_file
        )
    except KeyboardInterrupt:
        click.echo("\nShutdown requested by user", err=True)
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point for InputFlow module."""
    cli(prog_name="python -m inputflow")


if __name__ == "__main__":
    main()
