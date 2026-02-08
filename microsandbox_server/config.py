"""Configuration module for the microsandbox server.

Handles server configuration including settings, JWT tokens,
namespace management, and development/production mode.
"""

import ipaddress
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from microsandbox_server.error import MicrosandboxServerError
from microsandbox_utils.env import get_microsandbox_home_path
from microsandbox_utils.path import NAMESPACES_SUBDIR

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

#: The header name for the proxy authorization
PROXY_AUTH_HEADER: str = "Proxy-Authorization"


# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class Config:
    """Configuration structure that holds all the application settings."""

    def __init__(
        self,
        key: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 5555,
        namespace_dir: Optional[Path] = None,
        dev_mode: bool = False,
    ):
        # Check key requirement based on dev mode
        if key is None and not dev_mode:
            raise MicrosandboxServerError(
                "No key provided. A key is required when not in dev mode"
            )

        self._key = key
        self._dev_mode = dev_mode

        # Parse host string to IP address
        try:
            self._host = ipaddress.ip_address(host)
        except ValueError:
            raise MicrosandboxServerError(f"Invalid host address: {host}")

        self._port = port
        self._namespace_dir = namespace_dir or (
            get_microsandbox_home_path() / NAMESPACES_SUBDIR
        )

    @property
    def key(self) -> Optional[str]:
        """Secret key used for JWT token generation and validation."""
        return self._key

    @property
    def namespace_dir(self) -> Path:
        """Directory for storing namespaces."""
        return self._namespace_dir

    @property
    def dev_mode(self) -> bool:
        """Whether the server is in development mode."""
        return self._dev_mode

    @property
    def host(self) -> str:
        """Host address to listen on."""
        return str(self._host)

    @property
    def port(self) -> int:
        """Port number to listen on."""
        return self._port

    @property
    def addr(self) -> str:
        """Full address string (host:port)."""
        return f"{self._host}:{self._port}"
