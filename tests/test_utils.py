"""Tests for microsandbox_utils package."""

import pytest
from pathlib import Path

from microsandbox_utils.path import normalize_path, SupportedPathType
from microsandbox_utils.error import PathValidationError
from microsandbox_utils.defaults import (
    DEFAULT_MEMORY_MIB,
    DEFAULT_NUM_VCPUS,
    DEFAULT_OCI_REGISTRY,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    DEFAULT_PORTAL_GUEST_PORT,
)


class TestNormalizePath:
    """Tests for path normalization."""

    def test_absolute_simple(self):
        assert normalize_path("/foo/bar") == "/foo/bar"

    def test_absolute_with_dots(self):
        assert normalize_path("/foo/./bar") == "/foo/bar"

    def test_absolute_with_parent(self):
        assert normalize_path("/foo/bar/../baz") == "/foo/baz"

    def test_absolute_root(self):
        assert normalize_path("/") == "/"

    def test_relative_simple(self):
        assert normalize_path("foo/bar") == "foo/bar"

    def test_relative_with_dots(self):
        assert normalize_path("foo/./bar") == "foo/bar"

    def test_empty_raises(self):
        with pytest.raises(PathValidationError):
            normalize_path("")

    def test_escape_root_raises(self):
        with pytest.raises(PathValidationError):
            normalize_path("/..")

    def test_type_absolute_required(self):
        assert normalize_path("/foo", SupportedPathType.ABSOLUTE) == "/foo"

    def test_type_absolute_fails_for_relative(self):
        with pytest.raises(PathValidationError):
            normalize_path("foo", SupportedPathType.ABSOLUTE)

    def test_type_relative_required(self):
        assert normalize_path("foo", SupportedPathType.RELATIVE) == "foo"

    def test_type_relative_fails_for_absolute(self):
        with pytest.raises(PathValidationError):
            normalize_path("/foo", SupportedPathType.RELATIVE)

    def test_redundant_separators(self):
        assert normalize_path("/foo//bar") == "/foo/bar"


class TestDefaults:
    """Tests for default values."""

    def test_defaults_exist(self):
        assert DEFAULT_MEMORY_MIB == 1024
        assert DEFAULT_NUM_VCPUS == 1
        assert DEFAULT_OCI_REGISTRY == "docker.io"
        assert DEFAULT_SERVER_HOST == "127.0.0.1"
        assert DEFAULT_SERVER_PORT == 5555
        assert DEFAULT_PORTAL_GUEST_PORT == 4444
