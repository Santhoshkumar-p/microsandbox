"""OCI registry client for pulling container images.

Implements the Docker Registry HTTP API v2 for pulling images from
OCI-compliant registries.
"""

import gzip
import hashlib
import json
import logging
import os
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import httpx

from microsandbox_core.error import OciError
from microsandbox_core.oci.reference import Reference
from microsandbox_utils.env import get_oci_registry

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

DOCKER_MANIFEST_V2 = "application/vnd.docker.distribution.manifest.v2+json"
DOCKER_MANIFEST_LIST_V2 = "application/vnd.docker.distribution.manifest.list.v2+json"
OCI_MANIFEST_V1 = "application/vnd.oci.image.manifest.v1+json"
OCI_INDEX_V1 = "application/vnd.oci.image.index.v1+json"


# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class Registry:
    """OCI registry client for pulling container images."""

    def __init__(self, reference: Reference):
        self._reference = reference
        self._token: Optional[str] = None
        self._client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    @property
    def reference(self) -> Reference:
        """Get the image reference."""
        return self._reference

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def authenticate(self) -> None:
        """Authenticate with the registry using token-based auth."""
        registry = self._reference.registry

        # Determine auth URL based on registry
        if registry in ("docker.io", "registry-1.docker.io"):
            auth_url = (
                f"https://auth.docker.io/token"
                f"?service=registry.docker.io"
                f"&scope=repository:{self._reference.repository}:pull"
            )
        else:
            # Try to get auth info from the registry's /v2/ endpoint
            try:
                resp = await self._client.get(f"https://{registry}/v2/")
                if resp.status_code == 401:
                    www_auth = resp.headers.get("www-authenticate", "")
                    auth_url = _parse_www_authenticate(
                        www_auth, self._reference.repository
                    )
                else:
                    return  # No auth needed
            except Exception:
                return

        if not auth_url:
            return

        resp = await self._client.get(auth_url)
        resp.raise_for_status()
        data = resp.json()
        self._token = data.get("token") or data.get("access_token")

    def _auth_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_manifest(self) -> dict[str, Any]:
        """Fetch the image manifest.

        Returns:
            The parsed manifest JSON.
        """
        registry = self._reference.registry
        if registry == "docker.io":
            registry = "registry-1.docker.io"

        url = f"https://{registry}/v2/{self._reference.repository}/manifests/{self._reference.tag}"

        headers = self._auth_headers()
        headers["Accept"] = ", ".join([
            DOCKER_MANIFEST_V2,
            OCI_MANIFEST_V1,
            DOCKER_MANIFEST_LIST_V2,
            OCI_INDEX_V1,
        ])

        resp = await self._client.get(url, headers=headers)
        resp.raise_for_status()

        manifest = resp.json()

        # Handle manifest list / OCI index
        media_type = manifest.get("mediaType", "")
        if media_type in (DOCKER_MANIFEST_LIST_V2, OCI_INDEX_V1):
            # Select the appropriate platform manifest
            manifest = await self._select_platform_manifest(manifest, registry)

        return manifest

    async def _select_platform_manifest(
        self, index: dict, registry: str
    ) -> dict[str, Any]:
        """Select the appropriate platform manifest from an index."""
        import platform

        arch = platform.machine()
        arch_map = {
            "x86_64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }
        target_arch = arch_map.get(arch, arch)

        for entry in index.get("manifests", []):
            p = entry.get("platform", {})
            if p.get("architecture") == target_arch and p.get("os") == "linux":
                digest = entry["digest"]
                url = f"https://{registry}/v2/{self._reference.repository}/manifests/{digest}"
                headers = self._auth_headers()
                headers["Accept"] = f"{DOCKER_MANIFEST_V2}, {OCI_MANIFEST_V1}"
                resp = await self._client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.json()

        raise OciError(f"No manifest found for platform linux/{target_arch}")

    async def get_config(self, manifest: dict) -> dict[str, Any]:
        """Fetch the image configuration.

        Args:
            manifest: The image manifest.

        Returns:
            The parsed config JSON.
        """
        config_digest = manifest["config"]["digest"]
        return await self._get_blob_json(config_digest)

    async def _get_blob_json(self, digest: str) -> dict[str, Any]:
        """Fetch a blob and parse as JSON."""
        registry = self._reference.registry
        if registry == "docker.io":
            registry = "registry-1.docker.io"

        url = f"https://{registry}/v2/{self._reference.repository}/blobs/{digest}"
        headers = self._auth_headers()

        resp = await self._client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def pull_layer(
        self,
        digest: str,
        dest_dir: Path,
        on_progress: Any = None,
    ) -> Path:
        """Pull and extract a layer blob.

        Args:
            digest: The layer digest.
            dest_dir: Destination directory for extraction.
            on_progress: Optional callback for progress reporting.

        Returns:
            Path to the extracted layer directory.
        """
        registry = self._reference.registry
        if registry == "docker.io":
            registry = "registry-1.docker.io"

        url = f"https://{registry}/v2/{self._reference.repository}/blobs/{digest}"
        headers = self._auth_headers()

        # Create a safe directory name from the digest
        safe_name = digest.replace(":", "_")
        extract_dir = dest_dir / f"{safe_name}.extracted"

        if extract_dir.exists():
            logger.debug(f"Layer already extracted: {digest}")
            return extract_dir

        extract_dir.mkdir(parents=True, exist_ok=True)

        # Download the layer
        async with self._client.stream("GET", url, headers=headers) as resp:
            resp.raise_for_status()
            data = BytesIO()
            async for chunk in resp.aiter_bytes(chunk_size=8192):
                data.write(chunk)
                if on_progress:
                    on_progress(len(chunk))

        data.seek(0)

        # Try to extract as gzipped tar
        try:
            decompressed = gzip.decompress(data.read())
            tar_data = BytesIO(decompressed)
        except gzip.BadGzipFile:
            data.seek(0)
            tar_data = data

        try:
            with tarfile.open(fileobj=tar_data, mode="r:") as tar:
                tar.extractall(path=extract_dir, filter="data")
        except tarfile.TarError:
            # Not a tar file, just save the raw blob
            data.seek(0)
            blob_path = extract_dir / "blob"
            blob_path.write_bytes(data.read())

        return extract_dir


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------


def _parse_www_authenticate(header: str, repository: str) -> Optional[str]:
    """Parse WWW-Authenticate header to build auth URL."""
    if not header.startswith("Bearer "):
        return None

    params = {}
    for part in header[7:].split(","):
        key, _, value = part.strip().partition("=")
        params[key.strip()] = value.strip('"')

    realm = params.get("realm")
    if not realm:
        return None

    service = params.get("service", "")
    scope = f"repository:{repository}:pull"
    return f"{realm}?service={service}&scope={scope}"
