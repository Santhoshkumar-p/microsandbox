"""Tests for configuration parsing and management."""

import pytest
import tempfile
from pathlib import Path

from microsandbox_core.config.env_pair import EnvPair
from microsandbox_core.config.path_pair import PathPair
from microsandbox_core.config.port_pair import PortPair
from microsandbox_core.config.microsandbox_config import (
    Microsandbox,
    MicrosandboxConfig,
    SandboxConfig,
)


class TestPortPair:
    """Tests for PortPair parsing."""

    def test_parse_same_port(self):
        pair = PortPair.parse("8080")
        assert pair.host == 8080
        assert pair.guest == 8080

    def test_parse_distinct_ports(self):
        pair = PortPair.parse("8080:80")
        assert pair.host == 8080
        assert pair.guest == 80

    def test_str_same(self):
        pair = PortPair.same(8080)
        assert str(pair) == "8080"

    def test_str_distinct(self):
        pair = PortPair.distinct(8080, 80)
        assert str(pair) == "8080:80"


class TestEnvPair:
    """Tests for EnvPair parsing."""

    def test_parse_simple(self):
        pair = EnvPair.parse("KEY=VALUE")
        assert pair.key == "KEY"
        assert pair.value == "VALUE"

    def test_parse_with_equals_in_value(self):
        pair = EnvPair.parse("KEY=VAL=UE")
        assert pair.key == "KEY"
        assert pair.value == "VAL=UE"

    def test_parse_empty_value(self):
        pair = EnvPair.parse("KEY=")
        assert pair.key == "KEY"
        assert pair.value == ""

    def test_parse_no_equals_raises(self):
        with pytest.raises(ValueError):
            EnvPair.parse("INVALID")

    def test_str(self):
        pair = EnvPair(key="FOO", value="BAR")
        assert str(pair) == "FOO=BAR"


class TestPathPair:
    """Tests for PathPair parsing."""

    def test_parse_same_path(self):
        pair = PathPair.parse("/data")
        assert pair.host == "/data"
        assert pair.guest == "/data"

    def test_parse_distinct_paths(self):
        pair = PathPair.parse("./app:/container/app")
        assert pair.host == "./app"
        assert pair.guest == "/container/app"

    def test_str_same(self):
        pair = PathPair.same("/data")
        assert str(pair) == "/data"

    def test_str_distinct(self):
        pair = PathPair.distinct("./app", "/container/app")
        assert str(pair) == "./app:/container/app"


class TestMicrosandboxConfig:
    """Tests for Microsandbox configuration parsing."""

    def test_parse_empty_yaml(self):
        msb = Microsandbox.from_yaml("")
        assert msb.sandboxes == {}

    def test_parse_simple_sandbox(self):
        yaml_content = """
sandboxes:
  api:
    image: python:3.11
    memory: 1024
    cpus: 2
"""
        msb = Microsandbox.from_yaml(yaml_content)
        assert "api" in msb.sandboxes
        assert msb.sandboxes["api"].image == "python:3.11"
        assert msb.sandboxes["api"].memory == 1024
        assert msb.sandboxes["api"].cpus == 2

    def test_parse_sandbox_with_volumes_ports_envs(self):
        yaml_content = """
sandboxes:
  web:
    image: node:18
    volumes:
      - "./src:/app/src"
    ports:
      - "3000:3000"
    envs:
      - "NODE_ENV=production"
"""
        msb = Microsandbox.from_yaml(yaml_content)
        web = msb.sandboxes["web"]
        assert web.volumes == ["./src:/app/src"]
        assert web.ports == ["3000:3000"]
        assert web.envs == ["NODE_ENV=production"]

    def test_parse_sandbox_with_scripts(self):
        yaml_content = """
sandboxes:
  api:
    image: python:3.11
    scripts:
      start: "python main.py"
      test: "pytest tests/"
"""
        msb = Microsandbox.from_yaml(yaml_content)
        api = msb.sandboxes["api"]
        assert api.scripts["start"] == "python main.py"
        assert api.scripts["test"] == "pytest tests/"

    def test_parse_sandbox_with_depends_on(self):
        yaml_content = """
sandboxes:
  api:
    image: python:3.11
    depends_on:
      - database
  database:
    image: postgres:15
"""
        msb = Microsandbox.from_yaml(yaml_content)
        assert msb.sandboxes["api"].depends_on == ["database"]
        assert "database" in msb.sandboxes

    def test_parse_with_meta(self):
        yaml_content = """
meta:
  authors:
    - "Test Author"
  description: "Test project"
sandboxes:
  api:
    image: python:3.11
"""
        msb = Microsandbox.from_yaml(yaml_content)
        assert msb.meta is not None
        assert msb.meta.authors == ["Test Author"]
        assert msb.meta.description == "Test project"

    def test_get_sandbox(self):
        yaml_content = """
sandboxes:
  api:
    image: python:3.11
"""
        msb = Microsandbox.from_yaml(yaml_content)
        assert msb.get_sandbox("api") is not None
        assert msb.get_sandbox("nonexistent") is None

    def test_to_yaml(self):
        yaml_content = """
sandboxes:
  api:
    image: python:3.11
    memory: 1024
"""
        msb = Microsandbox.from_yaml(yaml_content)
        output = msb.to_yaml()
        assert "api" in output
        assert "python:3.11" in output

    def test_sandbox_config_get_port_pairs(self):
        config = SandboxConfig(ports=["8080:80", "3000"])
        pairs = config.get_port_pairs()
        assert len(pairs) == 2
        assert pairs[0].host == 8080
        assert pairs[0].guest == 80
        assert pairs[1].host == 3000
        assert pairs[1].guest == 3000

    def test_sandbox_config_get_env_pairs(self):
        config = SandboxConfig(envs=["KEY=VALUE", "FOO=BAR"])
        pairs = config.get_env_pairs()
        assert len(pairs) == 2
        assert pairs[0].key == "KEY"
        assert pairs[1].key == "FOO"

    def test_from_file(self):
        yaml_content = """
sandboxes:
  api:
    image: python:3.11
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            msb = Microsandbox.from_file(f.name)
            assert "api" in msb.sandboxes
