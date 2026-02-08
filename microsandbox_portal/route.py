"""Router configuration for microsandbox-portal."""

from fastapi import FastAPI

from microsandbox_portal.handler import json_rpc_handler
from microsandbox_portal.state import SharedState


def create_app(state: SharedState | None = None) -> FastAPI:
    """Create the FastAPI application for the portal.

    Args:
        state: Optional shared state. Creates default if not provided.

    Returns:
        The configured FastAPI application.
    """
    app = FastAPI(
        title="Microsandbox Portal",
        description="Sidecar for code execution inside sandboxes",
        version="0.2.6",
    )

    # Set shared state
    app.state.shared_state = state or SharedState()

    # Register routes
    app.post("/api/v1/rpc")(json_rpc_handler)

    return app
