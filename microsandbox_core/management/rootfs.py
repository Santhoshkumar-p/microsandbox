"""Root filesystem management with script patching and virtiofs mount setup.

Manages the preparation of root filesystems for sandboxes by combining
image layers with sandbox-specific configurations.
"""

import logging
import os
import stat
from pathlib import Path
from typing import Any, Optional

from microsandbox_core.config.microsandbox_config import SandboxConfig
from microsandbox_utils.defaults import DEFAULT_SHELL
from microsandbox_utils.path import (
    PATCH_SUBDIR,
    RW_SUBDIR,
    SANDBOX_DIR,
    SCRIPTS_DIR,
    SHELL_SCRIPT_NAME,
)

logger = logging.getLogger(__name__)


class RootfsManager:
    """Manages root filesystem preparation for sandboxes."""

    @staticmethod
    async def prepare_rootfs(
        name: str,
        layer_paths: list[str],
        work_dir: Path,
        config: SandboxConfig,
        script: Optional[str] = None,
        interactive: bool = False,
    ) -> dict[str, Any]:
        """Prepare the root filesystem for a sandbox.

        This creates the overlay filesystem structure:
        - lower_dirs: Read-only image layers
        - upper_dir: Read-write layer for changes
        - patch_dir: Patch layer for configuration

        Args:
            name: The sandbox name.
            layer_paths: Paths to extracted image layers.
            work_dir: The working directory for the sandbox.
            config: The sandbox configuration.
            script: Optional script name to set up.
            interactive: Whether this is an interactive session.

        Returns:
            Dict with rootfs information (lower_dirs, upper_dir, etc.).
        """
        # Create sandbox directories
        rw_dir = work_dir / RW_SUBDIR / name
        patch_dir = work_dir / PATCH_SUBDIR / name
        rw_dir.mkdir(parents=True, exist_ok=True)
        patch_dir.mkdir(parents=True, exist_ok=True)

        # Create work directory for overlayfs
        overlay_work_dir = work_dir / "work" / name
        overlay_work_dir.mkdir(parents=True, exist_ok=True)

        # Prepare patch layer with scripts and configuration
        await RootfsManager._prepare_patch_layer(
            patch_dir=patch_dir,
            config=config,
            script=script,
            interactive=interactive,
        )

        # Build lower directories list (image layers + patch layer)
        lower_dirs = layer_paths + [str(patch_dir)]

        return {
            "lower_dirs": lower_dirs,
            "upper_dir": str(rw_dir),
            "work_dir": str(overlay_work_dir),
        }

    @staticmethod
    async def _prepare_patch_layer(
        patch_dir: Path,
        config: SandboxConfig,
        script: Optional[str] = None,
        interactive: bool = False,
    ) -> None:
        """Prepare the patch layer with scripts and configuration.

        Creates script files in the sandbox directory structure
        that will be available inside the VM.
        """
        # Create sandbox scripts directory
        scripts_dir = patch_dir / SANDBOX_DIR / SCRIPTS_DIR
        scripts_dir.mkdir(parents=True, exist_ok=True)

        shell = config.shell or DEFAULT_SHELL

        # Write scripts from configuration
        for script_name, script_content in config.scripts.items():
            script_path = scripts_dir / script_name
            script_path.write_text(f"#!{shell}\n{script_content}\n")
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

        # Write shell script for interactive mode
        if interactive:
            shell_script = scripts_dir / SHELL_SCRIPT_NAME
            shell_script.write_text(f"#!{shell}\nexec {shell}\n")
            shell_script.chmod(shell_script.stat().st_mode | stat.S_IEXEC)

        # Write start script if defined
        if config.start:
            start_script = scripts_dir / "start"
            start_script.write_text(f"#!{shell}\n{config.start}\n")
            start_script.chmod(start_script.stat().st_mode | stat.S_IEXEC)
