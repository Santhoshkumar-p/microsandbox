"""Model Context Protocol (MCP) implementation for the microsandbox server.

Implements MCP protocol handlers for AI tool integration.
"""

import logging
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from microsandbox_server.error import ErrorCode
from microsandbox_server.payload import make_error_response, make_success_response
from microsandbox_server.state import AppState

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# MCP Tool Definitions
# -------------------------------------------------------------------------

MCP_TOOLS = [
    {
        "name": "sandbox_start",
        "description": "Start a new sandbox environment for executing code. "
                       "Creates an isolated microVM with the specified configuration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sandbox": {
                    "type": "string",
                    "description": "Name for the sandbox instance",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace for the sandbox (default: 'default')",
                    "default": "default",
                },
                "image": {
                    "type": "string",
                    "description": "Container image to use (e.g., 'microsandbox/python')",
                },
                "memory": {
                    "type": "integer",
                    "description": "Memory in MiB (default: 1024)",
                },
                "cpus": {
                    "type": "integer",
                    "description": "Number of vCPUs (default: 1)",
                },
            },
            "required": ["sandbox", "image"],
        },
    },
    {
        "name": "sandbox_stop",
        "description": "Stop a running sandbox environment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sandbox": {
                    "type": "string",
                    "description": "Name of the sandbox to stop",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the sandbox",
                    "default": "default",
                },
            },
            "required": ["sandbox"],
        },
    },
    {
        "name": "sandbox_run_code",
        "description": "Execute code in a running sandbox. Supports Python and JavaScript.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sandbox": {
                    "type": "string",
                    "description": "Name of the sandbox",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the sandbox",
                    "default": "default",
                },
                "code": {
                    "type": "string",
                    "description": "Code to execute",
                },
                "language": {
                    "type": "string",
                    "description": "Programming language (python or javascript)",
                    "default": "python",
                    "enum": ["python", "javascript"],
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 30,
                },
            },
            "required": ["sandbox", "code"],
        },
    },
    {
        "name": "sandbox_run_command",
        "description": "Run a shell command in a sandbox.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sandbox": {
                    "type": "string",
                    "description": "Name of the sandbox",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the sandbox",
                    "default": "default",
                },
                "command": {
                    "type": "string",
                    "description": "Command to execute",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command arguments",
                    "default": [],
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds",
                    "default": 30,
                },
            },
            "required": ["sandbox", "command"],
        },
    },
    {
        "name": "sandbox_get_metrics",
        "description": "Get resource usage metrics for a running sandbox.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sandbox": {
                    "type": "string",
                    "description": "Name of the sandbox",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the sandbox",
                    "default": "default",
                },
            },
            "required": ["sandbox"],
        },
    },
]

# -------------------------------------------------------------------------
# MCP Prompt Templates
# -------------------------------------------------------------------------

MCP_PROMPTS = [
    {
        "name": "python_sandbox",
        "description": "Template for setting up a Python sandbox environment",
        "arguments": [
            {
                "name": "task",
                "description": "What you want the sandbox to do",
                "required": True,
            },
        ],
    },
    {
        "name": "node_sandbox",
        "description": "Template for setting up a Node.js sandbox environment",
        "arguments": [
            {
                "name": "task",
                "description": "What you want the sandbox to do",
                "required": True,
            },
        ],
    },
]


# -------------------------------------------------------------------------
# MCP Handler
# -------------------------------------------------------------------------


async def mcp_handler(request: Request) -> JSONResponse:
    """Handle MCP protocol requests.

    Supports:
    - initialize: Protocol handshake
    - initialized / notifications/initialized: Notification acknowledgment
    - tools/list: List available tools
    - tools/call: Execute a tool
    - prompts/list: List available prompts
    """
    state: AppState = request.app.state.app_state

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            content=make_error_response(ErrorCode.PARSE_ERROR, "Parse error"),
            status_code=200,
        )

    method = body.get("method", "")
    params = body.get("params", {})
    request_id = body.get("id")

    logger.info(f"MCP method: {method}")

    try:
        if method == "initialize":
            result = handle_mcp_initialize(params)
        elif method in ("initialized", "notifications/initialized"):
            # Notification, no response needed
            return JSONResponse(content={}, status_code=200)
        elif method == "tools/list":
            result = handle_mcp_list_tools()
        elif method == "tools/call":
            result = await handle_mcp_tool_call(state, params)
        elif method == "prompts/list":
            result = handle_mcp_list_prompts()
        else:
            return JSONResponse(
                content=make_error_response(
                    ErrorCode.METHOD_NOT_FOUND, f"MCP method not found: {method}", request_id
                ),
                status_code=200,
            )

        return JSONResponse(
            content=make_success_response(result, request_id),
            status_code=200,
        )

    except Exception as e:
        logger.error(f"MCP error: {e}")
        return JSONResponse(
            content=make_error_response(ErrorCode.INTERNAL_ERROR, str(e), request_id),
            status_code=200,
        )


def handle_mcp_initialize(params: dict) -> dict:
    """Handle MCP initialize request."""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {"listChanged": False},
            "prompts": {"listChanged": False},
        },
        "serverInfo": {
            "name": "microsandbox",
            "version": "0.2.6",
        },
    }


def handle_mcp_list_tools() -> dict:
    """Handle MCP tools/list request."""
    return {"tools": MCP_TOOLS}


def handle_mcp_list_prompts() -> dict:
    """Handle MCP prompts/list request."""
    return {"prompts": MCP_PROMPTS}


async def handle_mcp_tool_call(state: AppState, params: dict) -> dict:
    """Handle MCP tools/call request.

    Converts MCP tool calls to internal JSON-RPC calls.
    """
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    # Map MCP tool names to JSON-RPC methods
    from microsandbox_server.handler import (
        handle_sandbox_start,
        handle_sandbox_stop,
        handle_sandbox_run_code,
        handle_sandbox_run_command,
        handle_sandbox_get_metrics,
    )

    tool_map = {
        "sandbox_start": ("sandbox.start", _mcp_to_start_params),
        "sandbox_stop": ("sandbox.stop", _mcp_to_stop_params),
        "sandbox_run_code": ("sandbox.run.code", _mcp_to_run_code_params),
        "sandbox_run_command": ("sandbox.run.command", _mcp_to_run_command_params),
        "sandbox_get_metrics": ("sandbox.get.metrics", _mcp_to_metrics_params),
    }

    handler_map = {
        "sandbox_start": handle_sandbox_start,
        "sandbox_stop": handle_sandbox_stop,
        "sandbox_run_code": handle_sandbox_run_code,
        "sandbox_run_command": handle_sandbox_run_command,
        "sandbox_get_metrics": handle_sandbox_get_metrics,
    }

    if tool_name not in tool_map:
        raise ValueError(f"Unknown MCP tool: {tool_name}")

    _, param_converter = tool_map[tool_name]
    handler = handler_map[tool_name]
    rpc_params = param_converter(arguments)

    result = await handler(state, rpc_params)

    return {
        "content": [
            {
                "type": "text",
                "text": str(result),
            }
        ],
    }


def _mcp_to_start_params(args: dict) -> dict:
    """Convert MCP sandbox_start args to sandbox.start params."""
    params: dict = {
        "sandbox": args["sandbox"],
        "namespace": args.get("namespace", "default"),
    }
    config = {"image": args["image"]}
    if "memory" in args:
        config["memory"] = args["memory"]
    if "cpus" in args:
        config["cpus"] = args["cpus"]
    params["config"] = config
    return params


def _mcp_to_stop_params(args: dict) -> dict:
    """Convert MCP sandbox_stop args to sandbox.stop params."""
    return {
        "sandbox": args["sandbox"],
        "namespace": args.get("namespace", "default"),
    }


def _mcp_to_run_code_params(args: dict) -> dict:
    """Convert MCP sandbox_run_code args to sandbox.run.code params."""
    return {
        "sandbox": args["sandbox"],
        "namespace": args.get("namespace", "default"),
        "code": args["code"],
        "language": args.get("language", "python"),
        "timeout": args.get("timeout", 30),
    }


def _mcp_to_run_command_params(args: dict) -> dict:
    """Convert MCP sandbox_run_command args to sandbox.run.command params."""
    return {
        "sandbox": args["sandbox"],
        "namespace": args.get("namespace", "default"),
        "command": args["command"],
        "args": args.get("args", []),
        "timeout": args.get("timeout", 30),
    }


def _mcp_to_metrics_params(args: dict) -> dict:
    """Convert MCP sandbox_get_metrics args to sandbox.get.metrics params."""
    return {
        "sandbox": args["sandbox"],
        "namespace": args.get("namespace", "default"),
    }
