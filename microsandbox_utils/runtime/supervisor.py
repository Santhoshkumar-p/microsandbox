"""Process supervisor for the microsandbox project."""

import asyncio
import logging
import os
import signal
import subprocess
from pathlib import Path
from typing import Optional

from microsandbox_utils.log.rotating import RotatingLog
from microsandbox_utils.path import SUPERVISOR_LOG_FILENAME
from microsandbox_utils.runtime.monitor import ProcessMonitor, ChildIo
from microsandbox_utils.term import is_interactive_terminal

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class Supervisor:
    """A supervisor that manages a child process and its logging."""

    def __init__(
        self,
        child_exe: str | Path,
        child_args: list[str] | None = None,
        child_envs: dict[str, str] | None = None,
        log_dir: str | Path = ".",
        process_monitor: ProcessMonitor | None = None,
    ):
        self._child_exe = Path(child_exe)
        self._child_args = child_args or []
        self._child_envs = child_envs or {}
        self._child_pid: Optional[int] = None
        self._log_dir = Path(log_dir)
        self._process_monitor = process_monitor

    async def start(self) -> None:
        """Starts the supervisor and the child process.

        This method:
        1. Creates the log directory if it doesn't exist
        2. Starts the child process with appropriate IO (TTY or pipes)
        3. Passes the IO to the process monitor
        """
        # Create log directory if it doesn't exist
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Setup supervisor's rotating log
        supervisor_log = RotatingLog(self._log_dir / SUPERVISOR_LOG_FILENAME)
        await supervisor_log.open()

        # Prepare environment
        env = os.environ.copy()
        env.update(self._child_envs)

        if is_interactive_terminal():
            logger.info("running in an interactive terminal")
            # Use PTY for interactive terminal
            import pty

            master_fd, slave_fd = pty.openpty()

            # Set master to non-blocking
            import fcntl
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            process = subprocess.Popen(
                [str(self._child_exe)] + self._child_args,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env,
                preexec_fn=os.setsid,
            )
            os.close(slave_fd)

            child_io = ChildIo.tty_io(
                master_read=os.fdopen(os.dup(master_fd), "rb", 0),
                master_write=os.fdopen(master_fd, "wb", 0),
            )
        else:
            logger.info("running in a non-interactive terminal")
            process = subprocess.Popen(
                [str(self._child_exe)] + self._child_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

            child_io = ChildIo.piped_io(
                stdin=process.stdin,
                stdout=process.stdout,
                stderr=process.stderr,
            )

        self._child_pid = process.pid

        # Start monitoring
        if self._process_monitor:
            await self._process_monitor.start(self._child_pid, child_io)

        # Setup signal handlers
        loop = asyncio.get_event_loop()

        shutdown_event = asyncio.Event()

        def handle_signal(signum):
            logger.info(f"received signal {signal.Signals(signum).name}")
            shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, handle_signal, sig)

        # Wait for either child process to exit or signal to be received
        try:
            while not shutdown_event.is_set():
                retcode = process.poll()
                if retcode is not None:
                    if self._process_monitor:
                        await self._process_monitor.stop()
                    logger.info(f"child process {self._child_pid} exited with code {retcode}")
                    break
                await asyncio.sleep(0.1)
            else:
                # Signal received - terminate child
                if self._process_monitor:
                    await self._process_monitor.stop()

                if self._child_pid:
                    try:
                        os.kill(self._child_pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass

                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
        finally:
            self._child_pid = None
            await supervisor_log.close()
