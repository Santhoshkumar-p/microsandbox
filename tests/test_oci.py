"""Tests for OCI image reference parsing."""

import pytest

from microsandbox_core.oci.reference import Reference


class TestReference:
    """Tests for OCI image reference parsing."""

    def test_simple_image(self):
        ref = Reference.parse("ubuntu")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.tag == "latest"

    def test_image_with_tag(self):
        ref = Reference.parse("ubuntu:22.04")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.tag == "22.04"

    def test_namespaced_image(self):
        ref = Reference.parse("myuser/myimage:v1")
        assert ref.registry == "docker.io"
        assert ref.repository == "myuser/myimage"
        assert ref.tag == "v1"

    def test_custom_registry(self):
        ref = Reference.parse("ghcr.io/user/image:tag")
        assert ref.registry == "ghcr.io"
        assert ref.repository == "user/image"
        assert ref.tag == "tag"

    def test_custom_registry_with_port(self):
        ref = Reference.parse("registry.example.com:5000/image:tag")
        assert ref.registry == "registry.example.com:5000"
        assert ref.repository == "image"
        assert ref.tag == "tag"

    def test_image_with_digest(self):
        ref = Reference.parse("ubuntu@sha256:abc123")
        assert ref.registry == "docker.io"
        assert ref.repository == "library/ubuntu"
        assert ref.digest == "sha256:abc123"

    def test_full_reference(self):
        ref = Reference.parse("ghcr.io/org/image:v2")
        assert ref.full_reference == "ghcr.io/org/image:v2"

    def test_image_name(self):
        ref = Reference.parse("myuser/myimage:v1")
        assert ref.image_name == "myimage"

    def test_str(self):
        ref = Reference.parse("ubuntu:22.04")
        assert "ubuntu" in str(ref)
        assert "22.04" in str(ref)

    def test_microsandbox_images(self):
        ref = Reference.parse("microsandbox/python")
        assert ref.registry == "docker.io"
        assert ref.repository == "microsandbox/python"
        assert ref.tag == "latest"

    def test_default_tag(self):
        ref = Reference.parse("nginx")
        assert ref.tag == "latest"
