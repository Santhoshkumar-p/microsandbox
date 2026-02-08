"""Type definitions for the REPL evaluation system."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    NODEJS = "javascript"


class Stream(str, Enum):
    """Output stream type."""
    STDOUT = "stdout"
    STDERR = "stderr"


@dataclass
class Line:
    """A single line of output from a REPL engine."""
    stream: Stream
    content: str


@dataclass
class EvalResult:
    """Result of evaluating code in a REPL engine."""
    stdout: str = ""
    stderr: str = ""
    status: str = "ok"


class EngineError(Exception):
    """Error from a REPL engine."""

    def __init__(self, message: str):
        super().__init__(message)


class Engine(ABC):
    """Abstract interface for a language REPL engine."""

    @abstractmethod
    async def start(self) -> None:
        """Start the engine process."""
        ...

    @abstractmethod
    async def eval(self, code: str, timeout: Optional[int] = 30) -> EvalResult:
        """Evaluate code in the engine.

        Args:
            code: The code to evaluate.
            timeout: Timeout in seconds.

        Returns:
            The evaluation result.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the engine process."""
        ...

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the engine process is running."""
        ...


class EngineHandle:
    """Client interface for interacting with REPL engines."""

    def __init__(self):
        self._engines: dict[str, Engine] = {}

    def register(self, language: str, engine: Engine) -> None:
        """Register an engine for a language."""
        self._engines[language] = engine

    async def eval(
        self, code: str, language: str = "python", timeout: Optional[int] = 30
    ) -> dict[str, Any]:
        """Evaluate code in the specified language engine.

        Args:
            code: The code to evaluate.
            language: The target language.
            timeout: Timeout in seconds.

        Returns:
            Dict with stdout, stderr, and status.
        """
        engine = self._engines.get(language)
        if not engine:
            raise EngineError(f"No engine registered for language: {language}")

        if not engine.is_running():
            await engine.start()

        result = await engine.eval(code, timeout)

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "status": result.status,
        }

    async def stop_all(self) -> None:
        """Stop all registered engines."""
        for engine in self._engines.values():
            try:
                await engine.stop()
            except Exception:
                pass
