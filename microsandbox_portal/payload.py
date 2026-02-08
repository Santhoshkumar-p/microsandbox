"""Request/response payload types for microsandbox-portal."""

from typing import Any, Optional

from pydantic import BaseModel


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[dict[str, Any]] = None
    id: Optional[int | str] = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None
    id: Optional[int | str] = None


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 error."""
    code: int
    message: str
    data: Optional[Any] = None


class SandboxReplRunParams(BaseModel):
    """Parameters for sandbox.repl.run."""
    code: str
    language: str = "python"
    timeout: Optional[int] = 30


class SandboxCommandRunParams(BaseModel):
    """Parameters for sandbox.command.run."""
    command: str
    args: list[str] = []
    timeout: Optional[int] = 30


def make_success_response(result: Any, request_id: Optional[int | str] = None) -> dict:
    """Create a successful JSON-RPC response."""
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id,
    }


def make_error_response(
    code: int, message: str, request_id: Optional[int | str] = None, data: Any = None
) -> dict:
    """Create an error JSON-RPC response."""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {
        "jsonrpc": "2.0",
        "error": error,
        "id": request_id,
    }
