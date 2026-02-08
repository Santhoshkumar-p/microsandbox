"""Configuration management and loading.

Handles reading, modifying, and writing Sandboxfile configurations
using a nondestructive approach that preserves YAML formatting.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from microsandbox_core.config.microsandbox_config import (
    Microsandbox,
    MicrosandboxConfig,
    SandboxConfig,
)
from microsandbox_core.error import ConfigError
from microsandbox_utils.defaults import DEFAULT_CONFIG
from microsandbox_utils.path import MICROSANDBOX_CONFIG_FILENAME

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages Sandboxfile configuration operations."""

    @staticmethod
    def load(
        config_path: Optional[Path] = None,
        project_dir: Optional[Path] = None,
    ) -> Microsandbox:
        """Load a Sandboxfile configuration.

        Args:
            config_path: Direct path to the Sandboxfile.
            project_dir: Project directory to search for Sandboxfile.

        Returns:
            The parsed Microsandbox configuration.

        Raises:
            ConfigError: If the configuration file is not found.
        """
        if config_path is None:
            project_dir = project_dir or Path.cwd()
            config_path = project_dir / MICROSANDBOX_CONFIG_FILENAME

        if not config_path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        return Microsandbox.from_file(str(config_path))

    @staticmethod
    def init(
        project_dir: Optional[Path] = None,
        config_path: Optional[Path] = None,
    ) -> Path:
        """Initialize a new Sandboxfile.

        Args:
            project_dir: The project directory.
            config_path: Optional custom path for the configuration file.

        Returns:
            Path to the created configuration file.

        Raises:
            ConfigError: If the file already exists.
        """
        project_dir = project_dir or Path.cwd()
        config_path = config_path or project_dir / MICROSANDBOX_CONFIG_FILENAME

        if config_path.exists():
            raise ConfigError(f"Configuration file already exists: {config_path}")

        config_path.write_text(DEFAULT_CONFIG)
        logger.info(f"Created {config_path}")
        return config_path

    @staticmethod
    def add_sandbox(
        name: str,
        image: str,
        config_path: Optional[Path] = None,
        project_dir: Optional[Path] = None,
        memory: Optional[int] = None,
        cpus: Optional[int] = None,
        volumes: Optional[list[str]] = None,
        ports: Optional[list[str]] = None,
        envs: Optional[list[str]] = None,
        depends_on: Optional[list[str]] = None,
        workdir: Optional[str] = None,
        shell: Optional[str] = None,
        scripts: Optional[dict[str, str]] = None,
        scope: Optional[str] = None,
    ) -> None:
        """Add a sandbox configuration to the Sandboxfile.

        Args:
            name: The sandbox name.
            image: The container image.
            config_path: Path to the Sandboxfile.
            project_dir: The project directory.
            memory: Memory in MiB.
            cpus: Number of CPUs.
            volumes: Volume mount strings.
            ports: Port mapping strings.
            envs: Environment variable strings.
            depends_on: Dependency sandbox names.
            workdir: Working directory.
            shell: Shell to use.
            scripts: Named scripts.
            scope: Network scope.
        """
        project_dir = project_dir or Path.cwd()
        config_path = config_path or project_dir / MICROSANDBOX_CONFIG_FILENAME

        if not config_path.exists():
            config_path.write_text(DEFAULT_CONFIG)

        content = config_path.read_text()
        data = yaml.safe_load(content) or {}

        if "sandboxes" not in data:
            data["sandboxes"] = {}

        sandbox_data: dict = {"image": image}
        if memory is not None:
            sandbox_data["memory"] = memory
        if cpus is not None:
            sandbox_data["cpus"] = cpus
        if volumes:
            sandbox_data["volumes"] = volumes
        if ports:
            sandbox_data["ports"] = ports
        if envs:
            sandbox_data["envs"] = envs
        if depends_on:
            sandbox_data["depends_on"] = depends_on
        if workdir:
            sandbox_data["workdir"] = workdir
        if shell:
            sandbox_data["shell"] = shell
        if scripts:
            sandbox_data["scripts"] = scripts
        if scope:
            sandbox_data["scope"] = scope

        data["sandboxes"][name] = sandbox_data

        config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        logger.info(f"Added sandbox '{name}' to {config_path}")

    @staticmethod
    def remove_sandbox(
        name: str,
        config_path: Optional[Path] = None,
        project_dir: Optional[Path] = None,
    ) -> None:
        """Remove a sandbox configuration from the Sandboxfile.

        Args:
            name: The sandbox name.
            config_path: Path to the Sandboxfile.
            project_dir: The project directory.
        """
        project_dir = project_dir or Path.cwd()
        config_path = config_path or project_dir / MICROSANDBOX_CONFIG_FILENAME

        if not config_path.exists():
            raise ConfigError(f"Configuration file not found: {config_path}")

        content = config_path.read_text()
        data = yaml.safe_load(content) or {}

        if "sandboxes" not in data or name not in data["sandboxes"]:
            raise ConfigError(f"Sandbox '{name}' not found in configuration")

        del data["sandboxes"][name]

        config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        logger.info(f"Removed sandbox '{name}' from {config_path}")
