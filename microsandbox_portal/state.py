"""Application state for microsandbox-portal."""

import asyncio
from typing import Optional

from microsandbox_portal.portal.repl.types import EngineHandle
from microsandbox_portal.portal.command import CommandHandle


class SharedState:
    """Shared application state for the portal server."""

    def __init__(self):
        self._engine_handle: Optional[EngineHandle] = None
        self._command_handle: Optional[CommandHandle] = None
        self._lock = asyncio.Lock()

    @property
    def engine_handle(self) -> Optional[EngineHandle]:
        """Get the REPL engine handle."""
        return self._engine_handle

    @engine_handle.setter
    def engine_handle(self, handle: EngineHandle) -> None:
        """Set the REPL engine handle."""
        self._engine_handle = handle

    @property
    def command_handle(self) -> Optional[CommandHandle]:
        """Get the command execution handle."""
        return self._command_handle

    @command_handle.setter
    def command_handle(self, handle: CommandHandle) -> None:
        """Set the command execution handle."""
        self._command_handle = handle
