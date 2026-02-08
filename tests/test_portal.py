"""Tests for the microsandbox portal."""

import pytest

from microsandbox_portal.payload import (
    JsonRpcRequest,
    SandboxCommandRunParams,
    SandboxReplRunParams,
    make_error_response,
    make_success_response,
)
from microsandbox_portal.state import SharedState
from microsandbox_portal.portal.repl.types import Language, Stream, Line, EvalResult


class TestPayload:
    """Tests for portal payload types."""

    def test_json_rpc_request(self):
        req = JsonRpcRequest(method="sandbox.repl.run", params={"code": "1+1"}, id=1)
        assert req.method == "sandbox.repl.run"
        assert req.params == {"code": "1+1"}

    def test_repl_run_params(self):
        params = SandboxReplRunParams(code="print('hello')")
        assert params.code == "print('hello')"
        assert params.language == "python"
        assert params.timeout == 30

    def test_command_run_params(self):
        params = SandboxCommandRunParams(command="ls", args=["-la"])
        assert params.command == "ls"
        assert params.args == ["-la"]

    def test_make_success_response(self):
        resp = make_success_response({"stdout": "hello"}, 1)
        assert resp["jsonrpc"] == "2.0"
        assert resp["result"]["stdout"] == "hello"

    def test_make_error_response(self):
        resp = make_error_response(-32601, "Method not found", 1)
        assert resp["error"]["code"] == -32601


class TestTypes:
    """Tests for REPL types."""

    def test_language_enum(self):
        assert Language.PYTHON == "python"
        assert Language.NODEJS == "javascript"

    def test_stream_enum(self):
        assert Stream.STDOUT == "stdout"
        assert Stream.STDERR == "stderr"

    def test_line(self):
        line = Line(stream=Stream.STDOUT, content="hello")
        assert line.stream == Stream.STDOUT
        assert line.content == "hello"

    def test_eval_result(self):
        result = EvalResult(stdout="42", stderr="", status="ok")
        assert result.stdout == "42"
        assert result.status == "ok"


class TestSharedState:
    """Tests for portal shared state."""

    def test_initial_state(self):
        state = SharedState()
        assert state.engine_handle is None
        assert state.command_handle is None
