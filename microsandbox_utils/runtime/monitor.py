"""Process monitoring utilities for the microsandbox project."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


@dataclass
class PipedIo:
    """Pipes for stdin, stdout, and stderr."""
    stdin: Optional[asyncio.StreamWriter] = None
    stdout: Optional[asyncio.StreamReader] = None
    stderr: Optional[asyncio.StreamReader] = None


@dataclass
class TtyIo:
    """A pseudo-TTY IO pair."""
    master_read: object = None  # File-like for reading
    master_write: object = None  # File-like for writing


class ChildIo:
    """The type of child IO to use."""

    def __init__(self, io_type: str, **kwargs):
        self.io_type = io_type
        if io_type == "tty":
            self.tty = TtyIo(**kwargs)
            self.piped = None
        elif io_type == "piped":
            self.tty = None
            self.piped = PipedIo(**kwargs)
        else:
            raise ValueError(f"Unknown IO type: {io_type}")

    @classmethod
    def tty_io(cls, master_read, master_write) -> "ChildIo":
        """Create a TTY child IO."""
        return cls("tty", master_read=master_read, master_write=master_write)

    @classmethod
    def piped_io(cls, stdin=None, stdout=None, stderr=None) -> "ChildIo":
        """Create a piped child IO."""
        return cls("piped", stdin=stdin, stdout=stdout, stderr=stderr)


# -------------------------------------------------------------------------
# Traits
# -------------------------------------------------------------------------


class ProcessMonitor(ABC):
    """A trait for monitoring processes."""

    @abstractmethod
    async def start(self, pid: int, child_io: ChildIo) -> None:
        """Start monitoring a process."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop monitoring."""
        ...
