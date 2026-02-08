"""Main entry point for the microsandbox portal server."""

import argparse
import asyncio
import logging
import signal
import sys

import uvicorn

from microsandbox_portal.portal.command import CommandHandle
from microsandbox_portal.portal.repl.engine import start_engines
from microsandbox_portal.route import create_app
from microsandbox_portal.state import SharedState
from microsandbox_utils.defaults import DEFAULT_PORTAL_GUEST_PORT

logger = logging.getLogger(__name__)


async def run_portal(port: int = DEFAULT_PORTAL_GUEST_PORT) -> None:
    """Run the portal server."""
    # Initialize state
    state = SharedState()

    # Start REPL engines
    logger.info("Starting REPL engines...")
    engine_handle = await start_engines(enable_python=True, enable_nodejs=True)
    state.engine_handle = engine_handle

    # Initialize command handle
    state.command_handle = CommandHandle()

    # Create FastAPI app
    app = create_app(state)

    # Configure uvicorn
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    logger.info(f"Portal server starting on port {port}")
    await server.serve()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Microsandbox Portal Server")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORTAL_GUEST_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORTAL_GUEST_PORT})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        asyncio.run(run_portal(port=args.port))
    except KeyboardInterrupt:
        logger.info("Portal server shutting down")


if __name__ == "__main__":
    main()
