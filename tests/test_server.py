"""Tests for the microsandbox server."""

import pytest

from microsandbox_server.config import Config
from microsandbox_server.error import ErrorCode, ServerError, MicrosandboxServerError
from microsandbox_server.payload import (
    SandboxStartParams,
    SandboxStopParams,
    SandboxRunCodeParams,
    SandboxRunCommandParams,
    make_error_response,
    make_success_response,
)
from microsandbox_server.port import PortManager


class TestConfig:
    """Tests for server configuration."""

    def test_dev_mode_no_key(self):
        config = Config(dev_mode=True)
        assert config.dev_mode is True
        assert config.key is None

    def test_non_dev_requires_key(self):
        with pytest.raises(MicrosandboxServerError):
            Config(dev_mode=False)

    def test_with_key(self):
        config = Config(key="test-secret", dev_mode=False)
        assert config.key == "test-secret"
        assert config.dev_mode is False

    def test_default_host_port(self):
        config = Config(dev_mode=True)
        assert config.host == "127.0.0.1"
        assert config.port == 5555

    def test_custom_host_port(self):
        config = Config(host="0.0.0.0", port=8080, dev_mode=True)
        assert config.host == "0.0.0.0"
        assert config.port == 8080

    def test_addr(self):
        config = Config(host="0.0.0.0", port=8080, dev_mode=True)
        assert config.addr == "0.0.0.0:8080"


class TestPayload:
    """Tests for payload types."""

    def test_sandbox_start_params(self):
        params = SandboxStartParams(sandbox="test", namespace="default")
        assert params.sandbox == "test"
        assert params.namespace == "default"

    def test_sandbox_stop_params(self):
        params = SandboxStopParams(sandbox="test")
        assert params.sandbox == "test"

    def test_sandbox_run_code_params(self):
        params = SandboxRunCodeParams(sandbox="test", code="print('hello')")
        assert params.sandbox == "test"
        assert params.code == "print('hello')"
        assert params.language == "python"
        assert params.timeout == 30

    def test_sandbox_run_command_params(self):
        params = SandboxRunCommandParams(sandbox="test", command="ls", args=["-la"])
        assert params.command == "ls"
        assert params.args == ["-la"]

    def test_make_success_response(self):
        resp = make_success_response({"status": "ok"}, 1)
        assert resp["jsonrpc"] == "2.0"
        assert resp["result"] == {"status": "ok"}
        assert resp["id"] == 1

    def test_make_error_response(self):
        resp = make_error_response(-32600, "Invalid request", 1)
        assert resp["jsonrpc"] == "2.0"
        assert resp["error"]["code"] == -32600
        assert resp["error"]["message"] == "Invalid request"
        assert resp["id"] == 1


class TestServerError:
    """Tests for server error types."""

    def test_authentication_error(self):
        err = ServerError.authentication_error()
        assert err.code == ErrorCode.AUTHENTICATION_ERROR

    def test_validation_error(self):
        err = ServerError.validation_error("bad input")
        assert err.code == ErrorCode.VALIDATION_ERROR
        assert "bad input" in err.message

    def test_to_json_rpc_error(self):
        err = ServerError.internal_error("something broke")
        result = err.to_json_rpc_error(request_id=42)
        assert result["error"]["code"] == int(ErrorCode.INTERNAL_ERROR)
        assert result["id"] == 42


class TestPortManager:
    """Tests for port management."""

    def test_assign_and_get(self):
        pm = PortManager()
        port = pm.assign_port("default/test", 12345)
        assert port == 12345
        assert pm.get_port("default/test") == 12345

    def test_release_port(self):
        pm = PortManager()
        pm.assign_port("default/test", 12345)
        released = pm.release_port("default/test")
        assert released == 12345
        assert pm.get_port("default/test") is None

    def test_list_ports(self):
        pm = PortManager()
        pm.assign_port("ns1/sb1", 10001)
        pm.assign_port("ns1/sb2", 10002)
        ports = pm.list_ports()
        assert len(ports) == 2

    def test_auto_assign_port(self):
        pm = PortManager()
        port = pm.assign_port("default/test")
        assert port > 0

    def test_release_nonexistent(self):
        pm = PortManager()
        assert pm.release_port("nonexistent") is None
