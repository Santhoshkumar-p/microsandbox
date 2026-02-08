"""Router configuration for the microsandbox server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from microsandbox_server.config import Config
from microsandbox_server.handler import health, json_rpc_handler
from microsandbox_server.mcp import mcp_handler
from microsandbox_server.middleware import AuthMiddleware, LoggingMiddleware, McpSmartAuthMiddleware
from microsandbox_server.port import PortManager
from microsandbox_server.state import AppState


def create_app(config: Config, port_manager: PortManager | None = None) -> FastAPI:
    """Create the FastAPI application for the server.

    Args:
        config: Server configuration.
        port_manager: Optional port manager instance.

    Returns:
        The configured FastAPI application.
    """
    app = FastAPI(
        title="Microsandbox Server",
        description="Server for managing sandboxes",
        version="0.2.6",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Logging middleware
    app.add_middleware(LoggingMiddleware)

    # Create app state
    pm = port_manager or PortManager(namespace_dir=config.namespace_dir)
    state = AppState(config=config, port_manager=pm)
    app.state.app_state = state

    # REST API routes
    app.get("/api/v1/health")(health)

    # JSON-RPC routes (with auth)
    rpc_app = FastAPI()
    rpc_app.add_middleware(AuthMiddleware, config=config)
    rpc_app.post("/")(json_rpc_handler)
    app.mount("/api/v1/rpc", rpc_app)

    # MCP routes (with smart auth)
    mcp_app = FastAPI()
    mcp_app.add_middleware(McpSmartAuthMiddleware, config=config)
    mcp_app.post("/")(mcp_handler)
    app.mount("/mcp", mcp_app)

    return app
