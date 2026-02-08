"""Server lifecycle management.

Handles server start/stop, PID file management, API key generation,
and signal handling for graceful shutdown.
"""

import asyncio
import logging
import os
import secrets
import signal
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt

from microsandbox_utils.env import get_microsandbox_home_path
from microsandbox_utils.path import SERVER_KEY_FILE, SERVER_PID_FILE

logger = logging.getLogger(__name__)


def generate_random_key(length: int = 64) -> str:
    """Generate a cryptographically secure random key.

    Args:
        length: The number of random bytes (key will be hex-encoded).

    Returns:
        A hex-encoded random key string.
    """
    return secrets.token_hex(length)


def generate_api_key(
    secret: str,
    namespace: str = "default",
    expire_days: int = 30,
) -> str:
    """Generate a JWT API key.

    Args:
        secret: The JWT signing secret.
        namespace: The namespace for the key.
        expire_days: Number of days until expiration.

    Returns:
        The JWT token string.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "namespace": namespace,
        "iat": now,
        "exp": now + timedelta(days=expire_days),
    }

    return jwt.encode(payload, secret, algorithm="HS256")


def save_server_key(key: str) -> Path:
    """Save the server key to disk.

    Args:
        key: The key to save.

    Returns:
        Path to the key file.
    """
    key_path = get_microsandbox_home_path() / SERVER_KEY_FILE
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(key)
    key_path.chmod(0o600)
    return key_path


def load_server_key() -> Optional[str]:
    """Load the server key from disk.

    Returns:
        The key string, or None if not found.
    """
    key_path = get_microsandbox_home_path() / SERVER_KEY_FILE
    if key_path.exists():
        return key_path.read_text().strip()
    return None


def save_pid_file(pid: int) -> Path:
    """Save the server PID to a file.

    Args:
        pid: The process ID.

    Returns:
        Path to the PID file.
    """
    pid_path = get_microsandbox_home_path() / SERVER_PID_FILE
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(pid))
    return pid_path


def load_pid_file() -> Optional[int]:
    """Load the server PID from a file.

    Returns:
        The PID, or None if not found.
    """
    pid_path = get_microsandbox_home_path() / SERVER_PID_FILE
    if pid_path.exists():
        try:
            return int(pid_path.read_text().strip())
        except ValueError:
            return None
    return None


def remove_pid_file() -> None:
    """Remove the server PID file."""
    pid_path = get_microsandbox_home_path() / SERVER_PID_FILE
    if pid_path.exists():
        pid_path.unlink()


def is_server_running() -> bool:
    """Check if the server is currently running.

    Returns:
        True if the server process is running.
    """
    pid = load_pid_file()
    if pid is None:
        return False

    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        remove_pid_file()
        return False


def stop_server() -> bool:
    """Stop the running server.

    Returns:
        True if the server was stopped successfully.
    """
    pid = load_pid_file()
    if pid is None:
        return False

    try:
        os.kill(pid, signal.SIGTERM)
        logger.info(f"Sent SIGTERM to server (PID: {pid})")
        remove_pid_file()
        return True
    except (OSError, ProcessLookupError):
        logger.warning(f"Server process {pid} not found")
        remove_pid_file()
        return False
