"""JSON-RPC request handlers for microsandbox-portal.

Implements the sandbox.repl.run and sandbox.command.run methods.
"""

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from microsandbox_portal.payload import (
    SandboxCommandRunParams,
    SandboxReplRunParams,
    make_error_response,
    make_success_response,
)
from microsandbox_portal.state import SharedState

logger = logging.getLogger(__name__)


async def json_rpc_handler(request: Request) -> JSONResponse:
    """Handle JSON-RPC 2.0 requests.

    Supported methods:
    - sandbox.repl.run: Execute code in a REPL environment
    - sandbox.command.run: Execute a shell command
    """
    state: SharedState = request.app.state.shared_state

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            content=make_error_response(-32700, "Parse error"),
            status_code=200,
        )

    # Validate JSON-RPC 2.0
    if body.get("jsonrpc") != "2.0":
        return JSONResponse(
            content=make_error_response(-32600, "Invalid Request: missing jsonrpc field"),
            status_code=200,
        )

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    if not method:
        return JSONResponse(
            content=make_error_response(-32600, "Invalid Request: missing method", request_id),
            status_code=200,
        )

    logger.info(f"Handling JSON-RPC method: {method}")

    try:
        if method == "sandbox.repl.run":
            result = await handle_repl_run(state, params)
        elif method == "sandbox.command.run":
            result = await handle_command_run(state, params)
        else:
            return JSONResponse(
                content=make_error_response(-32601, f"Method not found: {method}", request_id),
                status_code=200,
            )

        return JSONResponse(
            content=make_success_response(result, request_id),
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Error handling {method}: {e}")
        return JSONResponse(
            content=make_error_response(-32603, str(e), request_id),
            status_code=200,
        )


async def handle_repl_run(state: SharedState, params: dict[str, Any]) -> dict[str, Any]:
    """Handle sandbox.repl.run method.

    Executes code in the appropriate REPL engine and returns the output.
    """
    repl_params = SandboxReplRunParams(**params)

    if not state.engine_handle:
        raise RuntimeError("REPL engine not initialized")

    result = await state.engine_handle.eval(
        code=repl_params.code,
        language=repl_params.language,
        timeout=repl_params.timeout,
    )

    return {
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "status": result.get("status", "ok"),
    }


async def handle_command_run(state: SharedState, params: dict[str, Any]) -> dict[str, Any]:
    """Handle sandbox.command.run method.

    Executes a shell command and returns the output.
    """
    cmd_params = SandboxCommandRunParams(**params)

    if not state.command_handle:
        raise RuntimeError("Command handle not initialized")

    result = await state.command_handle.execute(
        command=cmd_params.command,
        args=cmd_params.args,
        timeout=cmd_params.timeout,
    )

    return {
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "exit_code": result.get("exit_code", -1),
    }
