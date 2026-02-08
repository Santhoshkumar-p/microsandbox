"""Request handlers for the microsandbox server.

Implements JSON-RPC handlers for sandbox operations and health check.
"""

import logging
import re
from typing import Any, Optional

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

from microsandbox_server.error import ErrorCode, ServerError
from microsandbox_server.payload import (
    SandboxMetricsGetParams,
    SandboxRunCodeParams,
    SandboxRunCommandParams,
    SandboxStartParams,
    SandboxStopParams,
    make_error_response,
    make_success_response,
)
from microsandbox_server.state import AppState

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Validation
# -------------------------------------------------------------------------

# Pattern for valid sandbox names
SANDBOX_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
NAMESPACE_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def validate_sandbox_name(name: str) -> None:
    """Validate a sandbox name."""
    if not SANDBOX_NAME_PATTERN.match(name):
        raise ServerError.validation_error(
            f"Invalid sandbox name: '{name}'. Must start with a letter and contain only "
            "alphanumeric characters, hyphens, and underscores."
        )


def validate_namespace(namespace: str) -> None:
    """Validate a namespace name."""
    if not NAMESPACE_PATTERN.match(namespace):
        raise ServerError.validation_error(
            f"Invalid namespace: '{namespace}'. Must start with a letter and contain only "
            "alphanumeric characters, hyphens, and underscores."
        )


# -------------------------------------------------------------------------
# REST Endpoints
# -------------------------------------------------------------------------


async def health(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})


# -------------------------------------------------------------------------
# JSON-RPC Handler
# -------------------------------------------------------------------------


async def json_rpc_handler(request: Request) -> JSONResponse:
    """Handle JSON-RPC 2.0 requests for sandbox operations.

    Supported methods:
    - sandbox.start: Start a new sandbox
    - sandbox.stop: Stop a running sandbox
    - sandbox.run.code: Execute code in a sandbox
    - sandbox.run.command: Run a command in a sandbox
    - sandbox.get.metrics: Get sandbox metrics
    """
    state: AppState = request.app.state.app_state

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            content=make_error_response(ErrorCode.PARSE_ERROR, "Parse error"),
            status_code=200,
        )

    if body.get("jsonrpc") != "2.0":
        return JSONResponse(
            content=make_error_response(
                ErrorCode.INVALID_REQUEST, "Invalid Request: missing jsonrpc field"
            ),
            status_code=200,
        )

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    if not method:
        return JSONResponse(
            content=make_error_response(
                ErrorCode.INVALID_REQUEST, "Invalid Request: missing method", request_id
            ),
            status_code=200,
        )

    logger.info(f"Handling JSON-RPC method: {method}")

    try:
        if method == "sandbox.start":
            result = await handle_sandbox_start(state, params)
        elif method == "sandbox.stop":
            result = await handle_sandbox_stop(state, params)
        elif method == "sandbox.run.code":
            result = await handle_sandbox_run_code(state, params)
        elif method == "sandbox.run.command":
            result = await handle_sandbox_run_command(state, params)
        elif method == "sandbox.get.metrics":
            result = await handle_sandbox_get_metrics(state, params)
        else:
            return JSONResponse(
                content=make_error_response(
                    ErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}", request_id
                ),
                status_code=200,
            )

        return JSONResponse(
            content=make_success_response(result, request_id),
            status_code=200,
        )

    except ServerError as e:
        return JSONResponse(
            content=e.to_json_rpc_error(request_id),
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error handling {method}: {e}")
        return JSONResponse(
            content=make_error_response(
                ErrorCode.INTERNAL_ERROR, str(e), request_id
            ),
            status_code=200,
        )


# -------------------------------------------------------------------------
# Sandbox Operations
# -------------------------------------------------------------------------


async def handle_sandbox_start(state: AppState, params: dict[str, Any]) -> dict:
    """Handle sandbox.start method."""
    p = SandboxStartParams(**params)
    validate_sandbox_name(p.sandbox)
    validate_namespace(p.namespace)

    # Create namespace directory
    ns_dir = state.config.namespace_dir / p.namespace
    ns_dir.mkdir(parents=True, exist_ok=True)

    # Assign a portal port
    key = f"{p.namespace}/{p.sandbox}"
    portal_port = state.port_manager.assign_port(key)

    # Build sandbox config
    from microsandbox_core.config.microsandbox_config import SandboxConfig

    config_data = {}
    if p.config:
        config_data = {
            "image": p.config.image,
            "memory": p.config.memory,
            "cpus": p.config.cpus,
            "volumes": p.config.volumes,
            "ports": p.config.ports,
            "envs": p.config.envs,
        }

    sandbox_config = SandboxConfig(**{k: v for k, v in config_data.items() if v is not None})

    # Start sandbox
    from microsandbox_core.management.sandbox import SandboxManager

    await SandboxManager.run(
        name=p.sandbox,
        config=sandbox_config,
        namespace=p.namespace,
        portal_host_port=portal_port,
        detach=True,
    )

    # Save port assignments
    state.port_manager.save(p.namespace)

    return {
        "status": "started",
        "sandbox": p.sandbox,
        "namespace": p.namespace,
        "portal_port": portal_port,
    }


async def handle_sandbox_stop(state: AppState, params: dict[str, Any]) -> dict:
    """Handle sandbox.stop method."""
    p = SandboxStopParams(**params)
    validate_sandbox_name(p.sandbox)
    validate_namespace(p.namespace)

    key = f"{p.namespace}/{p.sandbox}"

    # Release port
    state.port_manager.release_port(key)

    # Stop sandbox
    from microsandbox_core.management.sandbox import SandboxManager

    await SandboxManager.stop(name=p.sandbox, namespace=p.namespace)

    return {
        "status": "stopped",
        "sandbox": p.sandbox,
        "namespace": p.namespace,
    }


async def handle_sandbox_run_code(state: AppState, params: dict[str, Any]) -> dict:
    """Handle sandbox.run.code method.

    Forwards the code execution request to the sandbox's portal.
    """
    p = SandboxRunCodeParams(**params)
    validate_sandbox_name(p.sandbox)
    validate_namespace(p.namespace)

    portal_url = await state.get_portal_url_for_sandbox(p.namespace, p.sandbox)

    # Forward to portal
    async with httpx.AsyncClient(timeout=max(p.timeout or 30, 5) + 5) as client:
        response = await client.post(
            f"{portal_url}/api/v1/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "sandbox.repl.run",
                "params": {
                    "code": p.code,
                    "language": p.language,
                    "timeout": p.timeout,
                },
                "id": 1,
            },
        )

        result = response.json()
        if "error" in result and result["error"]:
            raise ServerError(
                ErrorCode.INTERNAL_ERROR,
                result["error"].get("message", "Unknown portal error"),
            )

        return result.get("result", {})


async def handle_sandbox_run_command(state: AppState, params: dict[str, Any]) -> dict:
    """Handle sandbox.run.command method.

    Forwards the command execution request to the sandbox's portal.
    """
    p = SandboxRunCommandParams(**params)
    validate_sandbox_name(p.sandbox)
    validate_namespace(p.namespace)

    portal_url = await state.get_portal_url_for_sandbox(p.namespace, p.sandbox)

    # Forward to portal
    async with httpx.AsyncClient(timeout=max(p.timeout or 30, 5) + 5) as client:
        response = await client.post(
            f"{portal_url}/api/v1/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "sandbox.command.run",
                "params": {
                    "command": p.command,
                    "args": p.args,
                    "timeout": p.timeout,
                },
                "id": 1,
            },
        )

        result = response.json()
        if "error" in result and result["error"]:
            raise ServerError(
                ErrorCode.INTERNAL_ERROR,
                result["error"].get("message", "Unknown portal error"),
            )

        return result.get("result", {})


async def handle_sandbox_get_metrics(state: AppState, params: dict[str, Any]) -> dict:
    """Handle sandbox.get.metrics method.

    Returns resource usage metrics for a running sandbox.
    """
    import psutil

    p = SandboxMetricsGetParams(**params)
    validate_sandbox_name(p.sandbox)
    validate_namespace(p.namespace)

    # Get basic system metrics (placeholder - in production this would
    # query the actual sandbox's metrics)
    return {
        "sandbox": p.sandbox,
        "namespace": p.namespace,
        "cpu_percent": 0.0,
        "memory_mib": 0,
        "disk_bytes": 0,
        "is_running": True,
    }
