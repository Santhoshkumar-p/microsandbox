"""Log rotation implementation for the Microsandbox runtime.

This module provides a rotating log implementation that automatically rotates log files
when they reach a specified size. The rotation process involves:
1. Renaming the current log file to .old extension
2. Creating a new empty log file
3. Continuing writing to the new file
"""

import asyncio
import logging
import os
from pathlib import Path

import aiofiles
import aiofiles.os

from microsandbox_utils.defaults import DEFAULT_LOG_MAX_SIZE

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class RotatingLog:
    """A rotating log file that automatically rotates when reaching a maximum size.

    The log rotation process preserves the last full log file with a ".old" extension
    while continuing to write to a new log file with the original name.
    """

    def __init__(self, path: Path, max_size: int = DEFAULT_LOG_MAX_SIZE):
        self._path = path
        self._max_size = max_size
        self._current_size = 0
        self._file = None
        self._lock = asyncio.Lock()

    async def open(self) -> "RotatingLog":
        """Open the log file for writing."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = await aiofiles.open(self._path, mode="a")
        try:
            stat = os.stat(self._path)
            self._current_size = stat.st_size
        except OSError:
            self._current_size = 0
        return self

    async def write(self, data: str | bytes) -> None:
        """Write data to the log file, rotating if necessary."""
        if self._file is None:
            await self.open()

        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        async with self._lock:
            data_len = len(data_bytes)

            if self._current_size + data_len > self._max_size:
                await self._rotate()

            await self._file.write(data if isinstance(data, str) else data.decode("utf-8", errors="replace"))
            await self._file.flush()
            self._current_size += data_len

    async def _rotate(self) -> None:
        """Perform log rotation."""
        try:
            if self._file:
                await self._file.close()

            backup_path = self._path.with_suffix(".old")
            if backup_path.exists():
                await aiofiles.os.remove(backup_path)

            if self._path.exists():
                os.rename(self._path, backup_path)

            self._file = await aiofiles.open(self._path, mode="a")
            self._current_size = 0
        except Exception as e:
            logger.error(f"failed to rotate log file: {e}")
            # Reopen the original file if rotation failed
            self._file = await aiofiles.open(self._path, mode="a")

    async def close(self) -> None:
        """Close the log file."""
        if self._file:
            await self._file.close()
            self._file = None

    def get_sync_writer(self) -> "SyncLogWriter":
        """Get a synchronous writer for this log."""
        return SyncLogWriter(self._path, self._max_size)


class SyncLogWriter:
    """A synchronous writer that writes to a log file."""

    def __init__(self, path: Path, max_size: int = DEFAULT_LOG_MAX_SIZE):
        self._path = path
        self._max_size = max_size
        self._file = None
        self._current_size = 0

    def open(self) -> "SyncLogWriter":
        """Open the log file for writing."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._path, "a")
        try:
            self._current_size = os.path.getsize(self._path)
        except OSError:
            self._current_size = 0
        return self

    def write(self, data: str) -> int:
        """Write data to the log file."""
        if self._file is None:
            self.open()

        data_len = len(data.encode("utf-8"))

        if self._current_size + data_len > self._max_size:
            self._rotate()

        self._file.write(data)
        self._file.flush()
        self._current_size += data_len
        return data_len

    def _rotate(self) -> None:
        """Perform synchronous log rotation."""
        try:
            if self._file:
                self._file.close()

            backup_path = self._path.with_suffix(".old")
            if backup_path.exists():
                os.remove(backup_path)

            if self._path.exists():
                os.rename(self._path, backup_path)

            self._file = open(self._path, "a")
            self._current_size = 0
        except Exception as e:
            logger.error(f"failed to rotate log file: {e}")
            self._file = open(self._path, "a")

    def flush(self) -> None:
        """Flush the log file."""
        if self._file:
            self._file.flush()

    def close(self) -> None:
        """Close the log file."""
        if self._file:
            self._file.close()
            self._file = None
