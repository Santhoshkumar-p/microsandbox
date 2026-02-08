"""Image pulling and layer extraction functionality."""

import logging
from pathlib import Path
from typing import Any, Optional, Callable

from microsandbox_core.error import OciError
from microsandbox_core.oci.layer import ImageLayerOps
from microsandbox_core.oci.reference import Reference
from microsandbox_core.oci.registry import Registry
from microsandbox_core.management.db import DatabaseManager

logger = logging.getLogger(__name__)


class ImageManager:
    """Manages container image operations including pulling and caching."""

    @staticmethod
    async def pull_image(
        image_ref: str,
        layer_path: Optional[Path] = None,
        on_progress: Optional[Callable[[str, int, int], None]] = None,
    ) -> dict[str, Any]:
        """Pull a container image from an OCI registry.

        Args:
            image_ref: The image reference string (e.g., "ubuntu:22.04").
            layer_path: Optional custom path for layer storage.
            on_progress: Optional progress callback(layer_digest, downloaded, total).

        Returns:
            Dict with image manifest and config.
        """
        reference = Reference.parse(image_ref)
        registry = Registry(reference)

        try:
            # Authenticate
            await registry.authenticate()

            # Get manifest
            manifest = await registry.get_manifest()

            # Get config
            config = await registry.get_config(manifest)

            # Determine layer storage path
            dest_dir = layer_path or ImageLayerOps.get_layers_dir()
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Pull layers
            layers = manifest.get("layers", [])
            for i, layer in enumerate(layers):
                digest = layer["digest"]
                layer_size = layer.get("size", 0)

                if ImageLayerOps.is_layer_cached(digest):
                    logger.info(f"Layer {i + 1}/{len(layers)} already cached: {digest[:20]}...")
                    if on_progress:
                        on_progress(digest, layer_size, layer_size)
                    continue

                logger.info(f"Pulling layer {i + 1}/{len(layers)}: {digest[:20]}...")

                def progress_wrapper(bytes_downloaded: int, _digest=digest, _total=layer_size):
                    if on_progress:
                        on_progress(_digest, bytes_downloaded, _total)

                await registry.pull_layer(
                    digest,
                    dest_dir,
                    on_progress=progress_wrapper,
                )

            # Cache image metadata in OCI database
            oci_db_path = await DatabaseManager.get_oci_db_path()
            await DatabaseManager.init_oci_db(oci_db_path)
            await DatabaseManager.cache_image(
                oci_db_path,
                reference.full_reference,
                manifest,
                config,
                layers,
            )

            return {
                "reference": reference.full_reference,
                "manifest": manifest,
                "config": config,
                "layers": layers,
            }

        finally:
            await registry.close()

    @staticmethod
    async def get_image_layer_paths(image_ref: str) -> list[str]:
        """Get the extracted layer paths for a cached image.

        Args:
            image_ref: The image reference string.

        Returns:
            List of paths to extracted layer directories.
        """
        reference = Reference.parse(image_ref)
        oci_db_path = await DatabaseManager.get_oci_db_path()

        cached = await DatabaseManager.get_cached_image(
            oci_db_path, reference.full_reference
        )

        if not cached:
            raise OciError(f"Image not found in cache: {image_ref}")

        layers = cached["manifest"].get("layers", [])
        digests = [layer["digest"] for layer in layers]

        return ImageLayerOps.get_layer_paths(digests)
