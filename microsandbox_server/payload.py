"""Request/response payload types for the microsandbox server."""

from typing import Any, Optional

from pydantic import BaseModel


# -------------------------------------------------------------------------
# JSON-RPC Types
# -------------------------------------------------------------------------


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


class JsonRpcNotification(BaseModel):
    """JSON-RPC 2.0 notification (no id)."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[dict[str, Any]] = None


# -------------------------------------------------------------------------
# Sandbox Operation Parameters
# -------------------------------------------------------------------------


class SandboxStartConfig(BaseModel):
    """Configuration for starting a sandbox."""
    image: str
    memory: Optional[int] = None
    cpus: Optional[int] = None
    volumes: list[str] = []
    ports: list[str] = []
    envs: list[str] = []


class SandboxStartParams(BaseModel):
    """Parameters for sandbox.start."""
    sandbox: str
    namespace: str = "default"
    config: Optional[SandboxStartConfig] = None


class SandboxStopParams(BaseModel):
    """Parameters for sandbox.stop."""
    sandbox: str
    namespace: str = "default"


class SandboxRunCodeParams(BaseModel):
    """Parameters for sandbox.run.code."""
    sandbox: str
    namespace: str = "default"
    language: str = "python"
    code: str
    timeout: Optional[int] = 30


class SandboxRunCommandParams(BaseModel):
    """Parameters for sandbox.run.command."""
    sandbox: str
    namespace: str = "default"
    command: str
    args: list[str] = []
    timeout: Optional[int] = 30


class SandboxMetricsGetParams(BaseModel):
    """Parameters for sandbox.get.metrics."""
    sandbox: str
    namespace: str = "default"


# -------------------------------------------------------------------------
# Response Helpers
# -------------------------------------------------------------------------


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
