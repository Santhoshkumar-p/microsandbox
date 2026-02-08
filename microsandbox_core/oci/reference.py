"""OCI-compliant image reference parsing.

Handles parsing of Docker/OCI image references like:
- ubuntu
- ubuntu:22.04
- library/ubuntu:latest
- docker.io/library/ubuntu:latest
- ghcr.io/user/image:tag
- registry.example.com/namespace/image@sha256:...
"""

import re
from dataclasses import dataclass
from typing import Optional

from microsandbox_utils.defaults import (
    DEFAULT_OCI_REFERENCE_REPO_NAMESPACE,
    DEFAULT_OCI_REFERENCE_TAG,
    DEFAULT_OCI_REGISTRY,
)


@dataclass
class Reference:
    """An OCI-compliant image reference.

    Attributes:
        registry: The registry domain (e.g., "docker.io").
        repository: The full repository path (e.g., "library/ubuntu").
        tag: The image tag (e.g., "latest").
        digest: Optional digest (e.g., "sha256:abc123...").
    """
    registry: str
    repository: str
    tag: str
    digest: Optional[str] = None

    @classmethod
    def parse(cls, reference: str) -> "Reference":
        """Parse an image reference string.

        Examples:
            "ubuntu" -> Reference("docker.io", "library/ubuntu", "latest")
            "ubuntu:22.04" -> Reference("docker.io", "library/ubuntu", "22.04")
            "myuser/myimage:v1" -> Reference("docker.io", "myuser/myimage", "v1")
            "ghcr.io/user/image:tag" -> Reference("ghcr.io", "user/image", "tag")
        """
        reference = reference.strip()
        digest = None
        tag = DEFAULT_OCI_REFERENCE_TAG

        # Check for digest
        if "@" in reference:
            reference, digest = reference.rsplit("@", 1)

        # Check for tag
        # Need to be careful: registry.example.com:5000/image should not split on port
        parts = reference.split("/")
        if len(parts) > 0:
            last_part = parts[-1]
            if ":" in last_part:
                parts[-1], tag = last_part.rsplit(":", 1)
                reference = "/".join(parts)

        # Determine registry and repository
        if "/" not in reference:
            # Simple image name like "ubuntu"
            registry = DEFAULT_OCI_REGISTRY
            repository = f"{DEFAULT_OCI_REFERENCE_REPO_NAMESPACE}/{reference}"
        elif _looks_like_registry(parts[0]):
            # Has explicit registry
            registry = parts[0]
            repository = "/".join(parts[1:])
        else:
            # Namespace/image format like "myuser/myimage"
            registry = DEFAULT_OCI_REGISTRY
            repository = reference

        return cls(
            registry=registry,
            repository=repository,
            tag=tag,
            digest=digest,
        )

    @property
    def full_reference(self) -> str:
        """Get the full reference string."""
        ref = f"{self.registry}/{self.repository}:{self.tag}"
        if self.digest:
            ref += f"@{self.digest}"
        return ref

    @property
    def image_name(self) -> str:
        """Get just the image name (last part of repository)."""
        return self.repository.rsplit("/", 1)[-1]

    def __str__(self) -> str:
        return self.full_reference


def _looks_like_registry(s: str) -> bool:
    """Check if a string looks like a registry domain."""
    return (
        "." in s
        or ":" in s
        or s == "localhost"
    )
