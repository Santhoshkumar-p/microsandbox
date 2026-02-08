"""Image layer operations for the microsandbox project."""

import logging
from pathlib import Path
from typing import Optional

from microsandbox_utils.path import LAYERS_SUBDIR, EXTRACTED_LAYER_SUFFIX
from microsandbox_utils.env import get_microsandbox_home_path

logger = logging.getLogger(__name__)


class ImageLayerOps:
    """Operations for managing container image layers."""

    @staticmethod
    def get_layers_dir() -> Path:
        """Get the global layers directory."""
        layers_dir = get_microsandbox_home_path() / LAYERS_SUBDIR
        layers_dir.mkdir(parents=True, exist_ok=True)
        return layers_dir

    @staticmethod
    def get_extracted_layer_path(digest: str) -> Path:
        """Get the path for an extracted layer.

        Args:
            digest: The layer digest (e.g., "sha256:abc123...").

        Returns:
            Path to the extracted layer directory.
        """
        safe_name = digest.replace(":", "_")
        return ImageLayerOps.get_layers_dir() / f"{safe_name}.{EXTRACTED_LAYER_SUFFIX}"

    @staticmethod
    def is_layer_cached(digest: str) -> bool:
        """Check if a layer is already cached.

        Args:
            digest: The layer digest.

        Returns:
            True if the layer exists in the cache.
        """
        return ImageLayerOps.get_extracted_layer_path(digest).exists()

    @staticmethod
    def get_layer_paths(digests: list[str]) -> list[str]:
        """Get the paths for a list of layer digests.

        Args:
            digests: List of layer digests.

        Returns:
            List of paths to extracted layer directories.
        """
        return [
            str(ImageLayerOps.get_extracted_layer_path(d))
            for d in digests
        ]
