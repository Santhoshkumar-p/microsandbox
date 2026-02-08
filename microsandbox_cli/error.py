"""Error types for the microsandbox CLI."""


class MicrosandboxCliError(Exception):
    """Base error for microsandbox CLI operations."""
    pass


class InvalidArgumentError(MicrosandboxCliError):
    """An invalid argument was provided."""

    def __init__(self, message: str):
        super().__init__(f"invalid argument: {message}")


class NotFoundError(MicrosandboxCliError):
    """A resource was not found."""

    def __init__(self, message: str):
        super().__init__(f"not found: {message}")


class ConfigError(MicrosandboxCliError):
    """A configuration error occurred."""

    def __init__(self, message: str):
        super().__init__(f"configuration error: {message}")


class NamespaceError(MicrosandboxCliError):
    """A namespace operation error occurred."""

    def __init__(self, message: str):
        super().__init__(f"namespace error: {message}")
