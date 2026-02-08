"""Error types for microsandbox-portal."""

from fastapi.responses import JSONResponse


class PortalError(Exception):
    """Base error for microsandbox-portal operations."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def to_response(self) -> JSONResponse:
        """Convert to a JSON response."""
        return JSONResponse(
            status_code=self.status_code,
            content={"error": self.message},
        )


class EngineNotFoundError(PortalError):
    """The requested engine is not available."""

    def __init__(self, language: str):
        super().__init__(f"Engine not available for language: {language}", 400)


class ExecutionError(PortalError):
    """An error occurred during code execution."""

    def __init__(self, message: str):
        super().__init__(f"Execution error: {message}", 500)


class TimeoutError_(PortalError):
    """Execution timed out."""

    def __init__(self, timeout: int):
        super().__init__(f"Execution timed out after {timeout} seconds", 408)
