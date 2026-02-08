"""MicroVM process monitor implementation.

Implements the ProcessMonitor trait for monitoring MicroVM processes,
handling both TTY and piped I/O modes.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from microsandbox_utils.log.rotating import RotatingLog
from microsandbox_utils.runtime.monitor import ChildIo, ProcessMonitor

logger = logging.getLogger(__name__)


class MicroVmMonitor(ProcessMonitor):
    """Process monitor for MicroVM instances.

    Handles I/O forwarding between the host terminal and the VM,
    and logs output to rotating log files.
    """

    def __init__(self, log_dir: Path):
        self._log_dir = log_dir
        self._log: Optional[RotatingLog] = None
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self, pid: int, child_io: ChildIo) -> None:
        """Start monitoring the MicroVM process."""
        self._running = True
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Setup log file
        self._log = RotatingLog(self._log_dir / f"sandbox.log")
        await self._log.open()

        if child_io.io_type == "tty":
            # TTY mode: forward between host stdin/stdout and master PTY
            self._tasks.append(
                asyncio.create_task(self._forward_tty_output(child_io.tty.master_read))
            )
            self._tasks.append(
                asyncio.create_task(self._forward_tty_input(child_io.tty.master_write))
            )
        elif child_io.io_type == "piped":
            # Piped mode: forward stdout and stderr
            if child_io.piped.stdout:
                self._tasks.append(
                    asyncio.create_task(self._forward_pipe_output(child_io.piped.stdout, "stdout"))
                )
            if child_io.piped.stderr:
                self._tasks.append(
                    asyncio.create_task(self._forward_pipe_output(child_io.piped.stderr, "stderr"))
                )
            if child_io.piped.stdin:
                self._tasks.append(
                    asyncio.create_task(self._forward_pipe_input(child_io.piped.stdin))
                )

    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()

        if self._log:
            await self._log.close()

    async def _forward_tty_output(self, master_read) -> None:
        """Forward TTY output to stdout and log."""
        try:
            while self._running:
                try:
                    data = master_read.read(4096)
                    if data:
                        sys.stdout.buffer.write(data)
                        sys.stdout.buffer.flush()
                        if self._log:
                            await self._log.write(data.decode("utf-8", errors="replace"))
                    else:
                        await asyncio.sleep(0.01)
                except (BlockingIOError, OSError):
                    await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass

    async def _forward_tty_input(self, master_write) -> None:
        """Forward stdin to TTY input."""
        try:
            loop = asyncio.get_event_loop()
            while self._running:
                try:
                    data = await loop.run_in_executor(None, lambda: sys.stdin.buffer.read1(4096))
                    if data:
                        master_write.write(data)
                        master_write.flush()
                except (BlockingIOError, OSError):
                    await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass

    async def _forward_pipe_output(self, pipe, stream_name: str) -> None:
        """Forward pipe output to stdout/stderr and log."""
        try:
            output = sys.stdout if stream_name == "stdout" else sys.stderr
            while self._running:
                data = pipe.read(4096)
                if data:
                    output.buffer.write(data)
                    output.buffer.flush()
                    if self._log:
                        await self._log.write(data.decode("utf-8", errors="replace"))
                else:
                    break
        except asyncio.CancelledError:
            pass

    async def _forward_pipe_input(self, pipe) -> None:
        """Forward stdin to pipe input."""
        try:
            loop = asyncio.get_event_loop()
            while self._running:
                try:
                    data = await loop.run_in_executor(None, lambda: sys.stdin.buffer.read1(4096))
                    if data:
                        pipe.write(data)
                        pipe.flush()
                except (BlockingIOError, OSError):
                    await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass
