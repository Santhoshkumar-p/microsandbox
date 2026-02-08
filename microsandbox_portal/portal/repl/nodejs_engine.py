"""Node.js REPL engine implementation.

Spawns a Node.js subprocess with a custom REPL configuration
for executing JavaScript code.
"""

import asyncio
import logging
import uuid
from typing import Optional

from microsandbox_portal.portal.repl.types import Engine, EvalResult

logger = logging.getLogger(__name__)

# End-of-execution marker for detecting completion
EOE_MARKER = "__MSB_EOE__"


class NodeJsEngine(Engine):
    """Node.js REPL engine using subprocess."""

    def __init__(self):
        self._process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the Node.js subprocess."""
        self._process = await asyncio.create_subprocess_exec(
            "node", "--interactive",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for initial prompt
        await asyncio.sleep(0.5)

        # Clear initial output
        if self._process.stdout:
            try:
                await asyncio.wait_for(
                    self._drain_stream(self._process.stdout), timeout=1.0
                )
            except asyncio.TimeoutError:
                pass

    async def eval(self, code: str, timeout: Optional[int] = 30) -> EvalResult:
        """Evaluate JavaScript code.

        Args:
            code: The JavaScript code to execute.
            timeout: Timeout in seconds.

        Returns:
            The evaluation result with stdout and stderr.
        """
        if not self._process or not self._process.stdin:
            raise RuntimeError("Node.js engine not started")

        async with self._lock:
            marker = f"{EOE_MARKER}_{uuid.uuid4().hex[:8]}"

            # Wrap code to print end-of-execution marker
            wrapped_code = (
                f"try {{ eval({json_escape(code)}) }} "
                f"catch(e) {{ process.stderr.write(e.toString() + '\\n') }} "
                f"finally {{ console.log('{marker}') }}\n"
            )

            # Send code to the process
            self._process.stdin.write(wrapped_code.encode("utf-8"))
            await self._process.stdin.drain()

            # Collect output until we see the marker
            stdout_lines: list[str] = []
            stderr_lines: list[str] = []

            try:
                stdout_lines, stderr_lines = await asyncio.wait_for(
                    self._collect_output(marker),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                return EvalResult(
                    stdout="",
                    stderr=f"Execution timed out after {timeout} seconds",
                    status="timeout",
                )

            return EvalResult(
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
                status="error" if stderr_lines else "ok",
            )

    async def _collect_output(self, marker: str) -> tuple[list[str], list[str]]:
        """Collect output until the end-of-execution marker is found."""
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        while True:
            # Read stdout
            if self._process.stdout:
                try:
                    line = await asyncio.wait_for(
                        self._process.stdout.readline(), timeout=0.5
                    )
                    if line:
                        decoded = line.decode("utf-8", errors="replace").rstrip()
                        if marker in decoded:
                            break
                        # Filter out Node.js REPL prompts
                        cleaned = decoded.lstrip("> ").lstrip(".. ")
                        if cleaned and cleaned != "undefined":
                            stdout_lines.append(cleaned)
                except asyncio.TimeoutError:
                    pass

            # Read stderr (non-blocking)
            if self._process.stderr:
                try:
                    line = await asyncio.wait_for(
                        self._process.stderr.readline(), timeout=0.1
                    )
                    if line:
                        decoded = line.decode("utf-8", errors="replace").rstrip()
                        stderr_lines.append(decoded)
                except asyncio.TimeoutError:
                    pass

        return stdout_lines, stderr_lines

    async def _drain_stream(self, stream) -> None:
        """Drain all available data from a stream."""
        while True:
            try:
                data = await asyncio.wait_for(stream.read(4096), timeout=0.1)
                if not data:
                    break
            except asyncio.TimeoutError:
                break

    async def stop(self) -> None:
        """Stop the Node.js subprocess."""
        if self._process:
            try:
                if self._process.stdin:
                    self._process.stdin.write(b".exit\n")
                    await self._process.stdin.drain()
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except (asyncio.TimeoutError, ProcessLookupError):
                self._process.kill()
            self._process = None

    def is_running(self) -> bool:
        """Check if the Node.js process is running."""
        return self._process is not None and self._process.returncode is None


def json_escape(s: str) -> str:
    """Escape a string for use in JavaScript JSON context."""
    import json
    return json.dumps(s)
