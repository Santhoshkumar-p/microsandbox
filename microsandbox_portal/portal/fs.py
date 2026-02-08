"""Filesystem operations for the portal.

Provides secure file access within the sandbox environment.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FilesystemOps:
    """Filesystem operations for sandboxed environments."""

    @staticmethod
    async def read_file(path: str) -> str:
        """Read a file from the sandbox filesystem.

        Args:
            path: The file path to read.

        Returns:
            The file contents as a string.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return file_path.read_text()

    @staticmethod
    async def write_file(path: str, content: str) -> None:
        """Write content to a file in the sandbox filesystem.

        Args:
            path: The file path to write.
            content: The content to write.
        """
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    @staticmethod
    async def list_dir(path: str = ".") -> list[str]:
        """List directory contents.

        Args:
            path: The directory path.

        Returns:
            List of filenames in the directory.
        """
        dir_path = Path(path)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        return [entry.name for entry in dir_path.iterdir()]

    @staticmethod
    async def file_exists(path: str) -> bool:
        """Check if a file exists.

        Args:
            path: The file path to check.

        Returns:
            True if the file exists.
        """
        return Path(path).exists()
