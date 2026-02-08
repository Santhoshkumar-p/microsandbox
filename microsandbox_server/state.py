"""Application state management for the microsandbox server."""

import asyncio
from typing import Optional

from microsandbox_server.config import Config
from microsandbox_server.error import ServerError
from microsandbox_server.port import PortManager, LOCALHOST_IP


class AppState:
    """Application state structure."""

    def __init__(self, config: Config, port_manager: PortManager):
        self._config = config
        self._port_manager = port_manager
        self._lock = asyncio.Lock()

    @property
    def config(self) -> Config:
        """The application configuration."""
        return self._config

    @property
    def port_manager(self) -> PortManager:
        """The port manager for handling sandbox port assignments."""
        return self._port_manager

    async def get_portal_url_for_sandbox(
        self, namespace: str, sandbox_name: str
    ) -> str:
        """Get a sandbox's portal URL.

        Returns an error if no port is assigned for the given sandbox.
        """
        key = f"{namespace}/{sandbox_name}"
        port = self._port_manager.get_port(key)

        if port is None:
            raise ServerError.InternalError(
                f"No portal port assigned for sandbox {key}"
            )

        return f"http://{LOCALHOST_IP}:{port}"
