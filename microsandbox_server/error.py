"""Error handling for the microsandbox server."""

from enum import IntEnum
from typing import Any, Optional

from fastapi.responses import JSONResponse


class ErrorCode(IntEnum):
    """Numeric error codes for the server."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Custom error codes
    AUTHENTICATION_ERROR = -32001
    AUTHORIZATION_ERROR = -32002
    VALIDATION_ERROR = -32003
    NOT_FOUND = -32004
    CONFLICT = -32005
    TIMEOUT = -32006


class MicrosandboxServerError(Exception):
    """Base error for microsandbox-server operations."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ServerError(Exception):
    """Server-specific errors that can be converted to JSON-RPC responses."""

    def __init__(self, code: ErrorCode, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_json_rpc_error(self, request_id: Optional[int | str] = None) -> dict:
        """Convert to a JSON-RPC error response."""
        error = {"code": int(self.code), "message": self.message}
        if self.data is not None:
            error["data"] = self.data
        return {
            "jsonrpc": "2.0",
            "error": error,
            "id": request_id,
        }

    @classmethod
    def authentication_error(cls, message: str = "Authentication failed") -> "ServerError":
        """Create an authentication error."""
        return cls(ErrorCode.AUTHENTICATION_ERROR, message)

    @classmethod
    def authorization_error(cls, message: str = "Authorization failed") -> "ServerError":
        """Create an authorization error."""
        return cls(ErrorCode.AUTHORIZATION_ERROR, message)

    @classmethod
    def validation_error(cls, message: str) -> "ServerError":
        """Create a validation error."""
        return cls(ErrorCode.VALIDATION_ERROR, message)

    @classmethod
    def not_found(cls, message: str) -> "ServerError":
        """Create a not-found error."""
        return cls(ErrorCode.NOT_FOUND, message)

    @classmethod
    def internal_error(cls, message: str) -> "ServerError":
        """Create an internal error."""
        return cls(ErrorCode.INTERNAL_ERROR, message)

    @classmethod
    def InternalError(cls, message: str) -> "ServerError":
        """Create an internal error (alias)."""
        return cls(ErrorCode.INTERNAL_ERROR, message)


class AuthenticationError(ServerError):
    """Authentication-specific error."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(ErrorCode.AUTHENTICATION_ERROR, message)


class AuthorizationError(ServerError):
    """Authorization-specific error."""

    def __init__(self, message: str = "Authorization failed"):
        super().__init__(ErrorCode.AUTHORIZATION_ERROR, message)


class ValidationError(ServerError):
    """Validation-specific error."""

    def __init__(self, message: str):
        super().__init__(ErrorCode.VALIDATION_ERROR, message)
