"""Error utilities for the microsandbox project."""


class MicrosandboxUtilsError(Exception):
    """Base error for microsandbox-utils operations."""
    pass


class PathValidationError(MicrosandboxUtilsError):
    """An error that occurred when validating paths."""

    def __init__(self, message: str):
        super().__init__(f"path validation error: {message}")
        self.detail = message


class FileNotFoundError_(MicrosandboxUtilsError):
    """An error that occurred when resolving a file."""

    def __init__(self, path: str, source: str):
        super().__init__(f"file not found at: {path}\nSource: {source}")
        self.path = path
        self.source = source


class RuntimeError_(MicrosandboxUtilsError):
    """An error that occurred during a runtime operation."""

    def __init__(self, message: str):
        super().__init__(f"runtime error: {message}")
        self.detail = message
