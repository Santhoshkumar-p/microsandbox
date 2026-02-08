"""Middleware components for the microsandbox server.

Provides authentication, authorization, and logging middleware.
"""

import logging
import time
from typing import Callable, Optional

import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from microsandbox_server.config import Config, PROXY_AUTH_HEADER
from microsandbox_server.payload import make_error_response

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Authentication Middleware
# -------------------------------------------------------------------------


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""

    def __init__(self, app, config: Config):
        super().__init__(app)
        self._config = config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check authentication for protected routes."""
        # Skip auth in dev mode
        if self._config.dev_mode:
            return await call_next(request)

        # Extract token
        token = _extract_token(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content=make_error_response(-32001, "Authentication required"),
            )

        # Validate token
        try:
            claims = _validate_jwt(token, self._config.key)
            # Store claims in request state for later use
            request.state.claims = claims
            request.state.namespace = claims.get("namespace", "default")
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content=make_error_response(-32001, "Token expired"),
            )
        except jwt.InvalidTokenError as e:
            return JSONResponse(
                status_code=401,
                content=make_error_response(-32001, f"Invalid token: {e}"),
            )

        return await call_next(request)


class McpSmartAuthMiddleware(BaseHTTPMiddleware):
    """Smart authentication middleware for MCP endpoints.

    Allows protocol methods (initialize, list) without auth,
    but requires auth for tool execution methods.
    """

    def __init__(self, app, config: Config):
        super().__init__(app)
        self._config = config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Smart authentication for MCP routes."""
        # Skip auth in dev mode
        if self._config.dev_mode:
            return await call_next(request)

        # Try to parse the body to determine the method
        try:
            body = await request.json()
            method = body.get("method", "")

            # Protocol methods don't require auth
            protocol_methods = {"initialize", "initialized", "notifications/initialized",
                              "tools/list", "prompts/list", "resources/list"}
            if method in protocol_methods:
                return await call_next(request)
        except Exception:
            pass

        # For tool calls, require auth
        token = _extract_token(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content=make_error_response(-32001, "Authentication required for tool calls"),
            )

        try:
            claims = _validate_jwt(token, self._config.key)
            request.state.claims = claims
            request.state.namespace = claims.get("namespace", "default")
        except jwt.InvalidTokenError as e:
            return JSONResponse(
                status_code=401,
                content=make_error_response(-32001, f"Invalid token: {e}"),
            )

        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response information."""
        start_time = time.time()
        method = request.method
        url = str(request.url)

        logger.info(f"-> {method} {url}")

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"<- {method} {url} [{response.status_code}] {duration_ms:.1f}ms")

        return response


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------


def _extract_token(request: Request) -> Optional[str]:
    """Extract the JWT token from the request.

    Checks:
    1. Authorization header (Bearer token)
    2. Proxy-Authorization header
    3. Query parameter (api_key)
    """
    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Check Proxy-Authorization header
    proxy_header = request.headers.get(PROXY_AUTH_HEADER, "")
    if proxy_header.startswith("Bearer "):
        return proxy_header[7:]

    # Check query parameter
    api_key = request.query_params.get("api_key")
    if api_key:
        return api_key

    return None


def _validate_jwt(token: str, secret: Optional[str]) -> dict:
    """Validate a JWT token.

    Args:
        token: The JWT token string.
        secret: The signing secret.

    Returns:
        The decoded claims.

    Raises:
        jwt.InvalidTokenError: If the token is invalid.
    """
    if not secret:
        raise jwt.InvalidTokenError("No secret key configured")

    return jwt.decode(token, secret, algorithms=["HS256"])
