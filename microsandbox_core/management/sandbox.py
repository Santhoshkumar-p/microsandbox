"""Sandbox execution and lifecycle management.

This module handles running sandboxes by setting up configurations,
preparing root filesystems, and launching microVMs.
"""

import asyncio
import logging
import os
import signal
from pathlib import Path
from typing import Any, Optional

from microsandbox_core.config.microsandbox_config import SandboxConfig
from microsandbox_core.config.env_pair import EnvPair
from microsandbox_core.config.path_pair import PathPair
from microsandbox_core.config.port_pair import PortPair
from microsandbox_core.error import ManagementError
from microsandbox_core.management.db import DatabaseManager
from microsandbox_core.management.image import ImageManager
from microsandbox_core.management.rootfs import RootfsManager
from microsandbox_utils.defaults import (
    DEFAULT_MEMORY_MIB,
    DEFAULT_NUM_VCPUS,
    DEFAULT_PORTAL_GUEST_PORT,
    DEFAULT_SHELL,
    DEFAULT_WORKDIR,
)
from microsandbox_utils.env import get_microsandbox_home_path
from microsandbox_utils.path import MICROSANDBOX_ENV_DIR, NAMESPACES_SUBDIR

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manages the lifecycle of individual sandboxes."""

    @staticmethod
    async def run(
        name: str,
        config: SandboxConfig,
        project_dir: Optional[Path] = None,
        namespace: Optional[str] = None,
        portal_host_port: Optional[int] = None,
        detach: bool = False,
        script: Optional[str] = None,
        interactive: bool = False,
    ) -> Optional[int]:
        """Run a sandbox.

        Args:
            name: The sandbox name.
            config: The sandbox configuration.
            project_dir: The project directory (for local mode).
            namespace: The namespace (for server mode).
            portal_host_port: Host port for the portal.
            detach: Whether to run in detached mode.
            script: Optional script name to run.
            interactive: Whether to run in interactive (shell) mode.

        Returns:
            The exit code if not detached, None otherwise.
        """
        if not config.image:
            raise ManagementError(f"No image specified for sandbox '{name}'")

        # Determine working paths
        if namespace:
            work_dir = (
                get_microsandbox_home_path() / NAMESPACES_SUBDIR / namespace / name
            )
        elif project_dir:
            work_dir = project_dir / MICROSANDBOX_ENV_DIR
        else:
            work_dir = Path.cwd() / MICROSANDBOX_ENV_DIR

        work_dir.mkdir(parents=True, exist_ok=True)

        # Ensure image layers are available
        try:
            layer_paths = await ImageManager.get_image_layer_paths(config.image)
        except Exception:
            logger.info(f"Pulling image {config.image}...")
            await ImageManager.pull_image(config.image)
            layer_paths = await ImageManager.get_image_layer_paths(config.image)

        # Prepare rootfs
        rootfs_info = await RootfsManager.prepare_rootfs(
            name=name,
            layer_paths=layer_paths,
            work_dir=work_dir,
            config=config,
            script=script,
            interactive=interactive,
        )

        # Build the msbrun command
        from microsandbox_utils.defaults import DEFAULT_MSBRUN_EXE_PATH
        from microsandbox_utils.env import MSBRUN_EXE_ENV_VAR

        msbrun_path = os.environ.get(MSBRUN_EXE_ENV_VAR, str(DEFAULT_MSBRUN_EXE_PATH))

        cmd = [str(msbrun_path), "--mode", "microvm"]
        cmd.extend(["--vcpus", str(config.cpus or DEFAULT_NUM_VCPUS)])
        cmd.extend(["--memory", str(config.memory or DEFAULT_MEMORY_MIB)])
        cmd.extend(["--workdir", config.workdir or DEFAULT_WORKDIR])

        # Add rootfs layers
        for lp in rootfs_info.get("lower_dirs", []):
            cmd.extend(["--layer", lp])
        if rootfs_info.get("upper_dir"):
            cmd.extend(["--rw-layer", rootfs_info["upper_dir"]])

        # Add port mappings
        portal_port = portal_host_port or DEFAULT_PORTAL_GUEST_PORT
        cmd.extend(["--port", f"{portal_port}:{DEFAULT_PORTAL_GUEST_PORT}"])
        for port_str in config.ports:
            cmd.extend(["--port", port_str])

        # Add volumes
        for vol_str in config.volumes:
            cmd.extend(["--volume", vol_str])

        # Add environment variables
        for env_str in config.envs:
            cmd.extend(["--env", env_str])

        # Add exec path
        shell = config.shell or DEFAULT_SHELL
        if interactive:
            cmd.extend(["--exec", shell])
        elif script and script in config.scripts:
            cmd.extend(["--exec", shell, "--", "-c", config.scripts[script]])
        elif config.start:
            cmd.extend(["--exec", shell, "--", "-c", config.start])
        else:
            cmd.extend(["--exec", shell])

        logger.info(f"Starting sandbox '{name}' with image '{config.image}'")

        if detach:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )

            # Update database
            if project_dir:
                db_path = await DatabaseManager.get_sandbox_db_path(project_dir)
                await DatabaseManager.init_sandbox_db(db_path)
                await DatabaseManager.set_sandbox_status(
                    db_path, name, "running", process.pid, portal_port
                )

            return None
        else:
            process = await asyncio.create_subprocess_exec(*cmd)
            await process.wait()
            return process.returncode

    @staticmethod
    async def stop(
        name: str,
        project_dir: Optional[Path] = None,
        namespace: Optional[str] = None,
    ) -> None:
        """Stop a running sandbox.

        Args:
            name: The sandbox name.
            project_dir: The project directory.
            namespace: The namespace.
        """
        if project_dir:
            db_path = await DatabaseManager.get_sandbox_db_path(project_dir)
            status = await DatabaseManager.get_sandbox_status(db_path, name)
            if status and status.get("pid"):
                try:
                    os.kill(status["pid"], signal.SIGTERM)
                except ProcessLookupError:
                    pass
                await DatabaseManager.set_sandbox_status(db_path, name, "stopped")
        else:
            logger.warning(f"Cannot stop sandbox '{name}': no project directory specified")
