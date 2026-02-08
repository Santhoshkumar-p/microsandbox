"""Orchestra management for coordinated sandbox lifecycle.

Manages the lifecycle of multiple sandboxes defined in a Sandboxfile,
handling dependencies, ordering, and coordinated start/stop operations.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from microsandbox_core.config.microsandbox_config import Microsandbox, SandboxConfig
from microsandbox_core.error import ManagementError
from microsandbox_core.management.sandbox import SandboxManager
from microsandbox_core.management.db import DatabaseManager
from microsandbox_utils.path import MICROSANDBOX_CONFIG_FILENAME

logger = logging.getLogger(__name__)


class OrchestraManager:
    """Manages coordinated sandbox lifecycle operations."""

    @staticmethod
    async def apply(
        config_path: Optional[Path] = None,
        project_dir: Optional[Path] = None,
        detach: bool = False,
    ) -> None:
        """Apply the full Sandboxfile configuration.

        Starts all sandboxes defined in the configuration file,
        respecting dependency ordering.

        Args:
            config_path: Path to the Sandboxfile.
            project_dir: The project directory.
            detach: Whether to run sandboxes in detached mode.
        """
        project_dir = project_dir or Path.cwd()
        config_path = config_path or project_dir / MICROSANDBOX_CONFIG_FILENAME

        if not config_path.exists():
            raise ManagementError(f"Configuration file not found: {config_path}")

        msb = Microsandbox.from_file(str(config_path))

        # Resolve dependency order
        ordered = _topological_sort(msb.sandboxes)

        # Start sandboxes in order
        for name in ordered:
            config = msb.sandboxes[name]
            logger.info(f"Starting sandbox: {name}")
            await SandboxManager.run(
                name=name,
                config=config,
                project_dir=project_dir,
                detach=detach,
            )

    @staticmethod
    async def up(
        sandbox_names: Optional[list[str]] = None,
        config_path: Optional[Path] = None,
        project_dir: Optional[Path] = None,
        detach: bool = True,
    ) -> None:
        """Start one or more sandboxes.

        Args:
            sandbox_names: Optional list of specific sandboxes to start.
            config_path: Path to the Sandboxfile.
            project_dir: The project directory.
            detach: Whether to run in detached mode.
        """
        project_dir = project_dir or Path.cwd()
        config_path = config_path or project_dir / MICROSANDBOX_CONFIG_FILENAME

        if not config_path.exists():
            raise ManagementError(f"Configuration file not found: {config_path}")

        msb = Microsandbox.from_file(str(config_path))

        if sandbox_names:
            # Start only specified sandboxes
            for name in sandbox_names:
                config = msb.get_sandbox(name)
                if not config:
                    raise ManagementError(f"Sandbox '{name}' not found in configuration")
                await SandboxManager.run(
                    name=name,
                    config=config,
                    project_dir=project_dir,
                    detach=detach,
                )
        else:
            # Start all sandboxes
            ordered = _topological_sort(msb.sandboxes)
            for name in ordered:
                config = msb.sandboxes[name]
                await SandboxManager.run(
                    name=name,
                    config=config,
                    project_dir=project_dir,
                    detach=detach,
                )

    @staticmethod
    async def down(
        sandbox_names: Optional[list[str]] = None,
        config_path: Optional[Path] = None,
        project_dir: Optional[Path] = None,
    ) -> None:
        """Stop one or more sandboxes.

        Args:
            sandbox_names: Optional list of specific sandboxes to stop.
            config_path: Path to the Sandboxfile.
            project_dir: The project directory.
        """
        project_dir = project_dir or Path.cwd()
        config_path = config_path or project_dir / MICROSANDBOX_CONFIG_FILENAME

        if not config_path.exists():
            raise ManagementError(f"Configuration file not found: {config_path}")

        msb = Microsandbox.from_file(str(config_path))

        names = sandbox_names or list(msb.sandboxes.keys())

        # Stop sandboxes in reverse dependency order
        ordered = _topological_sort(msb.sandboxes)
        names_to_stop = [n for n in reversed(ordered) if n in names]

        for name in names_to_stop:
            logger.info(f"Stopping sandbox: {name}")
            await SandboxManager.stop(name=name, project_dir=project_dir)

    @staticmethod
    async def status(
        sandbox_names: Optional[list[str]] = None,
        config_path: Optional[Path] = None,
        project_dir: Optional[Path] = None,
    ) -> list[dict]:
        """Get the status of sandboxes.

        Args:
            sandbox_names: Optional list of specific sandboxes to check.
            config_path: Path to the Sandboxfile.
            project_dir: The project directory.

        Returns:
            List of sandbox status dictionaries.
        """
        project_dir = project_dir or Path.cwd()
        db_path = await DatabaseManager.get_sandbox_db_path(project_dir)

        if not db_path.exists():
            return []

        all_sandboxes = await DatabaseManager.list_sandboxes(db_path)

        if sandbox_names:
            return [s for s in all_sandboxes if s["name"] in sandbox_names]
        return all_sandboxes


def _topological_sort(sandboxes: dict[str, SandboxConfig]) -> list[str]:
    """Sort sandboxes based on their dependencies.

    Args:
        sandboxes: Map of sandbox name to configuration.

    Returns:
        List of sandbox names in dependency order.

    Raises:
        ManagementError: If there is a circular dependency.
    """
    visited: set[str] = set()
    temp_mark: set[str] = set()
    result: list[str] = []

    def visit(name: str) -> None:
        if name in temp_mark:
            raise ManagementError(f"Circular dependency detected involving '{name}'")
        if name in visited:
            return

        temp_mark.add(name)

        config = sandboxes.get(name)
        if config:
            for dep in config.depends_on:
                if dep in sandboxes:
                    visit(dep)

        temp_mark.discard(name)
        visited.add(name)
        result.append(name)

    for name in sandboxes:
        visit(name)

    return result
