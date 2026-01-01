#!/usr/bin/env python3
"""
InputFlow main entry point.

Allows running InputFlow as a module: python -m inputflow [server|client]
Provides a command-line interface without graphical components.
"""

import argparse
import sys
from pathlib import Path

from inputflow.core.logging import setup_logging


def main():
    """Main entry point for InputFlow module."""
    parser = argparse.ArgumentParser(
        description="InputFlow - Cross-platform keyboard and mouse sharing tool",
        prog="python -m inputflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m inputflow server                    # Run server with default config
  python -m inputflow server -c my_config.toml # Run server with custom config
  python -m inputflow client -s 192.168.1.100  # Run client connecting to server
  python -m inputflow client -v                # Run client with verbose logging
        """
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="InputFlow 0.1.0"
    )
    
    subparsers = parser.add_subparsers(
        dest="mode", 
        help="Operation mode",
        metavar="{server,client}"
    )
    
    # Server subcommand
    server_parser = subparsers.add_parser(
        "server", 
        help="Run as input capture server",
        description="Start InputFlow server to capture and share input events"
    )
    server_parser.add_argument(
        "--config", "-c",
        type=str,
        metavar="PATH",
        help="Path to configuration file (default: config.toml in current directory)"
    )
    server_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging with detailed debug information"
    )
    server_parser.add_argument(
        "--log-file",
        type=str,
        metavar="PATH",
        help="Write logs to specified file in addition to console output"
    )
    
    # Client subcommand
    client_parser = subparsers.add_parser(
        "client", 
        help="Run as input simulation client",
        description="Start InputFlow client to receive and simulate input events"
    )
    client_parser.add_argument(
        "--config", "-c",
        type=str,
        metavar="PATH",
        help="Path to configuration file (default: config.toml in current directory)"
    )
    client_parser.add_argument(
        "--server", "-s",
        type=str,
        metavar="IP",
        help="Server IP address (overrides config file setting)"
    )
    client_parser.add_argument(
        "--port", "-p",
        type=int,
        metavar="PORT",
        help="Server port number (overrides config file setting)"
    )
    client_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging with detailed debug information"
    )
    client_parser.add_argument(
        "--log-file",
        type=str,
        metavar="PATH",
        help="Write logs to specified file in addition to console output"
    )
    
    args = parser.parse_args()
    
    # Show help if no mode specified
    if not args.mode:
        parser.print_help()
        print("\nError: Must specify either 'server' or 'client' mode", file=sys.stderr)
        sys.exit(1)
    
    # Setup logging based on arguments
    setup_logging(
        level="DEBUG" if args.verbose else "INFO",
        log_file=getattr(args, 'log_file', None),
        verbose=args.verbose
    )
    
    # Validate configuration file path if provided
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        if not config_path.is_file():
            print(f"Error: Configuration path is not a file: {args.config}", file=sys.stderr)
            sys.exit(1)
    
    # Run the appropriate mode
    try:
        if args.mode == "server":
            from inputflow.server import main as server_main
            # Pass arguments directly to server
            server_main(
                config_path=args.config,
                verbose=args.verbose,
                log_file=getattr(args, 'log_file', None)
            )
        
        elif args.mode == "client":
            from inputflow.client import main as client_main
            # Pass arguments directly to client
            client_main(
                config_path=args.config,
                server_ip=args.server,
                server_port=args.port,
                verbose=args.verbose,
                log_file=getattr(args, 'log_file', None)
            )
    
    except KeyboardInterrupt:
        print("\nShutdown requested by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()