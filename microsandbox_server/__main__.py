"""Main entry point for the microsandbox server."""

import argparse
import asyncio
import logging
import os
import sys

import uvicorn

from microsandbox_server.config import Config
from microsandbox_server.management import (
    generate_random_key,
    load_server_key,
    save_pid_file,
    save_server_key,
)
from microsandbox_server.port import PortManager
from microsandbox_server.route import create_app
from microsandbox_utils.defaults import DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT


def main():
    """Main entry point for the server binary."""
    parser = argparse.ArgumentParser(description="Microsandbox Server")
    parser.add_argument(
        "--host",
        default=DEFAULT_SERVER_HOST,
        help=f"Host address to listen on (default: {DEFAULT_SERVER_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_SERVER_PORT,
        help=f"Port to listen on (default: {DEFAULT_SERVER_PORT})",
    )
    parser.add_argument(
        "--key",
        default=None,
        help="JWT secret key (required in non-dev mode)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode (no auth required)",
    )
    parser.add_argument(
        "--namespace-dir",
        default=None,
        help="Directory for storing namespaces",
    )
    parser.add_argument(
        "--reset-key",
        action="store_true",
        help="Generate a new server key",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Handle key management
    key = args.key
    if not key and not args.dev:
        key = load_server_key()
        if not key or args.reset_key:
            key = generate_random_key()
            save_server_key(key)
            logging.info("Generated new server key")

    # Create configuration
    from pathlib import Path

    namespace_dir = Path(args.namespace_dir) if args.namespace_dir else None
    config = Config(
        key=key,
        host=args.host,
        port=args.port,
        namespace_dir=namespace_dir,
        dev_mode=args.dev,
    )

    # Create port manager
    port_manager = PortManager(namespace_dir=config.namespace_dir)

    # Create app
    app = create_app(config, port_manager)

    # Save PID file
    save_pid_file(os.getpid())

    logging.info(f"Starting microsandbox server on {config.addr}")
    if config.dev_mode:
        logging.info("Running in development mode (authentication disabled)")

    # Run server
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
