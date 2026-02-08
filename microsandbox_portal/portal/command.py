"""Command execution for the portal.

Handles executing shell commands inside the sandbox environment
with timeout support and output streaming.
"""

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CommandHandle:
    """Handle for executing commands in the sandbox."""

    async def execute(
        self,
        command: str,
        args: Optional[list[str]] = None,
        timeout: Optional[int] = 30,
    ) -> dict[str, Any]:
        """Execute a command in the sandbox.

        Args:
            command: The command to execute.
            args: Optional arguments for the command.
            timeout: Timeout in seconds.

        Returns:
            Dict with stdout, stderr, and exit_code.
        """
        args = args or []
        full_cmd = [command] + args

        logger.info(f"Executing command: {' '.join(full_cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "stdout": "",
                    "stderr": f"Command timed out after {timeout} seconds",
                    "exit_code": -1,
                }

            return {
                "stdout": stdout_bytes.decode("utf-8", errors="replace"),
                "stderr": stderr_bytes.decode("utf-8", errors="replace"),
                "exit_code": process.returncode or 0,
            }

        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": f"Command not found: {command}",
                "exit_code": 127,
            }
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
            }
