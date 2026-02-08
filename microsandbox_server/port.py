"""Port assignment and management for the microsandbox server.

Handles dynamic port allocation for sandbox portal connections,
with persistence to disk.
"""

import json
import logging
import socket
from pathlib import Path
from typing import Optional

from microsandbox_utils.env import get_microsandbox_home_path
from microsandbox_utils.path import NAMESPACES_SUBDIR, PORTAL_PORTS_FILE

logger = logging.getLogger(__name__)

#: Localhost IP address
LOCALHOST_IP: str = "127.0.0.1"


class PortManager:
    """Manages port assignments for sandboxes."""

    def __init__(self, namespace_dir: Optional[Path] = None):
        self._ports: dict[str, int] = {}
        self._namespace_dir = namespace_dir or (
            get_microsandbox_home_path() / NAMESPACES_SUBDIR
        )

    def get_port(self, key: str) -> Optional[int]:
        """Get the port assigned to a sandbox.

        Args:
            key: The sandbox key (namespace/sandbox_name).

        Returns:
            The assigned port, or None if not assigned.
        """
        return self._ports.get(key)

    def assign_port(self, key: str, port: Optional[int] = None) -> int:
        """Assign a port to a sandbox.

        Args:
            key: The sandbox key (namespace/sandbox_name).
            port: Optional specific port. If None, assigns a free port.

        Returns:
            The assigned port number.
        """
        if port is None:
            port = self._find_free_port()

        self._ports[key] = port
        logger.info(f"Assigned port {port} to {key}")
        return port

    def release_port(self, key: str) -> Optional[int]:
        """Release a port assignment.

        Args:
            key: The sandbox key.

        Returns:
            The released port, or None if not assigned.
        """
        port = self._ports.pop(key, None)
        if port:
            logger.info(f"Released port {port} from {key}")
        return port

    def list_ports(self) -> dict[str, int]:
        """List all port assignments.

        Returns:
            Dict mapping sandbox keys to ports.
        """
        return dict(self._ports)

    def save(self, namespace: str) -> None:
        """Save port assignments to disk.

        Args:
            namespace: The namespace to save ports for.
        """
        ports_file = self._namespace_dir / namespace / PORTAL_PORTS_FILE
        ports_file.parent.mkdir(parents=True, exist_ok=True)

        # Filter ports for this namespace
        ns_ports = {
            k: v for k, v in self._ports.items()
            if k.startswith(f"{namespace}/")
        }

        ports_file.write_text(json.dumps(ns_ports, indent=2))

    def load(self, namespace: str) -> None:
        """Load port assignments from disk.

        Args:
            namespace: The namespace to load ports for.
        """
        ports_file = self._namespace_dir / namespace / PORTAL_PORTS_FILE

        if ports_file.exists():
            data = json.loads(ports_file.read_text())
            self._ports.update(data)
            logger.info(f"Loaded {len(data)} port assignments for namespace {namespace}")

    @staticmethod
    def _find_free_port() -> int:
        """Find a free port on the system.

        Returns:
            A free port number.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    @staticmethod
    def is_port_available(port: int) -> bool:
        """Check if a port is available.

        Args:
            port: The port number to check.

        Returns:
            True if the port is available.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return True
            except OSError:
                return False
