"""Microsandbox configuration types.

This module defines the configuration structures for the Sandboxfile YAML format.
"""

from dataclasses import dataclass, field
from typing import Optional

import yaml
from pydantic import BaseModel

from microsandbox_core.config.env_pair import EnvPair
from microsandbox_core.config.path_pair import PathPair
from microsandbox_core.config.port_pair import PortPair


# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class MetaConfig(BaseModel):
    """Metadata for a microsandbox project."""
    authors: list[str] = []
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    readme: Optional[str] = None
    tags: list[str] = []
    icon: Optional[str] = None


class SandboxConfig(BaseModel):
    """Configuration for a single sandbox."""
    image: Optional[str] = None
    memory: Optional[int] = None
    cpus: Optional[int] = None
    volumes: list[str] = []
    ports: list[str] = []
    envs: list[str] = []
    env_file: Optional[str] = None
    depends_on: list[str] = []
    workdir: Optional[str] = None
    shell: Optional[str] = None
    scripts: dict[str, str] = {}
    imports: dict[str, str] = {}
    exports: dict[str, str] = {}
    scope: Optional[str] = None
    start: Optional[str] = None

    def get_port_pairs(self) -> list[PortPair]:
        """Parse port strings into PortPair objects."""
        return [PortPair.parse(p) for p in self.ports]

    def get_env_pairs(self) -> list[EnvPair]:
        """Parse env strings into EnvPair objects."""
        return [EnvPair.parse(e) for e in self.envs]

    def get_volume_pairs(self) -> list[PathPair]:
        """Parse volume strings into PathPair objects."""
        return [PathPair.parse(v) for v in self.volumes]


class BuildConfig(BaseModel):
    """Configuration for a build step."""
    image: Optional[str] = None
    memory: Optional[int] = None
    cpus: Optional[int] = None
    volumes: list[str] = []
    ports: list[str] = []
    envs: list[str] = []
    env_file: Optional[str] = None
    depends_on: list[str] = []
    workdir: Optional[str] = None
    shell: Optional[str] = None
    scripts: dict[str, str] = {}
    imports: dict[str, str] = {}
    exports: dict[str, str] = {}
    scope: Optional[str] = None


class MicrosandboxConfig(BaseModel):
    """Top-level microsandbox configuration (Sandboxfile)."""
    meta: Optional[MetaConfig] = None
    modules: dict[str, dict] = {}
    builds: dict[str, BuildConfig] = {}
    sandboxes: dict[str, SandboxConfig] = {}


class Microsandbox:
    """Microsandbox configuration manager.

    Loads and manages the Sandboxfile configuration.
    """

    def __init__(self, config: MicrosandboxConfig, raw_content: str = ""):
        self._config = config
        self._raw_content = raw_content

    @classmethod
    def from_yaml(cls, content: str) -> "Microsandbox":
        """Parse a Sandboxfile YAML string into a Microsandbox configuration."""
        data = yaml.safe_load(content) or {}
        config = MicrosandboxConfig(**data)
        return cls(config, content)

    @classmethod
    def from_file(cls, path: str) -> "Microsandbox":
        """Load a Sandboxfile from a file path."""
        with open(path, "r") as f:
            content = f.read()
        return cls.from_yaml(content)

    @property
    def config(self) -> MicrosandboxConfig:
        """Get the parsed configuration."""
        return self._config

    @property
    def sandboxes(self) -> dict[str, SandboxConfig]:
        """Get the sandbox configurations."""
        return self._config.sandboxes

    @property
    def builds(self) -> dict[str, BuildConfig]:
        """Get the build configurations."""
        return self._config.builds

    @property
    def meta(self) -> Optional[MetaConfig]:
        """Get the metadata configuration."""
        return self._config.meta

    def get_sandbox(self, name: str) -> Optional[SandboxConfig]:
        """Get a sandbox configuration by name."""
        return self._config.sandboxes.get(name)

    def get_build(self, name: str) -> Optional[BuildConfig]:
        """Get a build configuration by name."""
        return self._config.builds.get(name)

    def to_yaml(self) -> str:
        """Serialize the configuration to YAML."""
        data = self._config.model_dump(exclude_none=True, exclude_defaults=True)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
