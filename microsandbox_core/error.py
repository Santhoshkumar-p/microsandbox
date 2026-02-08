"""Error types for microsandbox-core."""


class MicrosandboxCoreError(Exception):
    """Base error for microsandbox-core operations."""
    pass


class ConfigError(MicrosandboxCoreError):
    """An error that occurred during configuration."""

    def __init__(self, message: str):
        super().__init__(f"config error: {message}")
        self.detail = message


class VmError(MicrosandboxCoreError):
    """An error that occurred during VM operations."""

    def __init__(self, message: str):
        super().__init__(f"vm error: {message}")
        self.detail = message


class OciError(MicrosandboxCoreError):
    """An error that occurred during OCI operations."""

    def __init__(self, message: str):
        super().__init__(f"oci error: {message}")
        self.detail = message


class ManagementError(MicrosandboxCoreError):
    """An error that occurred during management operations."""

    def __init__(self, message: str):
        super().__init__(f"management error: {message}")
        self.detail = message


class DatabaseError(MicrosandboxCoreError):
    """An error that occurred during database operations."""

    def __init__(self, message: str):
        super().__init__(f"database error: {message}")
        self.detail = message
