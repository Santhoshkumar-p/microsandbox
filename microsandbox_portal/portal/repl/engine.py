"""Core REPL engine management.

Manages the lifecycle of language-specific REPL engines using a reactor pattern.
"""

import logging
from typing import Optional

from microsandbox_portal.portal.repl.types import EngineHandle

logger = logging.getLogger(__name__)


class Engines:
    """Collection of REPL engines."""

    def __init__(self):
        self._handle = EngineHandle()
        self._initialized = False

    @property
    def handle(self) -> EngineHandle:
        """Get the engine handle for evaluation."""
        return self._handle

    async def initialize(self, enable_python: bool = True, enable_nodejs: bool = True) -> None:
        """Initialize all enabled language engines.

        Args:
            enable_python: Whether to enable the Python engine.
            enable_nodejs: Whether to enable the Node.js engine.
        """
        if self._initialized:
            return

        if enable_python:
            try:
                from microsandbox_portal.portal.repl.python_engine import PythonEngine
                engine = PythonEngine()
                await engine.start()
                self._handle.register("python", engine)
                logger.info("Python REPL engine initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Python engine: {e}")

        if enable_nodejs:
            try:
                from microsandbox_portal.portal.repl.nodejs_engine import NodeJsEngine
                engine = NodeJsEngine()
                await engine.start()
                self._handle.register("javascript", engine)
                self._handle.register("nodejs", engine)
                logger.info("Node.js REPL engine initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Node.js engine: {e}")

        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown all engines."""
        await self._handle.stop_all()
        self._initialized = False


async def start_engines(
    enable_python: bool = True,
    enable_nodejs: bool = True,
) -> EngineHandle:
    """Initialize and start REPL engines.

    Args:
        enable_python: Whether to enable the Python engine.
        enable_nodejs: Whether to enable the Node.js engine.

    Returns:
        The engine handle for code evaluation.
    """
    engines = Engines()
    await engines.initialize(enable_python, enable_nodejs)
    return engines.handle
