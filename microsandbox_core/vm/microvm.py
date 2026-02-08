"""MicroVM structure and lifecycle management.

This module provides the core MicroVM abstraction for running isolated
sandbox environments using libkrun.
"""

import logging
import os
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Optional

from microsandbox_core.config.env_pair import EnvPair
from microsandbox_core.config.path_pair import PathPair
from microsandbox_core.config.port_pair import PortPair
from microsandbox_core.vm.rlimit import LinuxRlimit

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class LogLevel(IntEnum):
    """Log level for the MicroVM."""
    OFF = 0
    ERROR = 1
    WARN = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5


class RootfsType:
    """Root filesystem type."""
    NATIVE = "native"
    OVERLAYFS = "overlayfs"


@dataclass
class NativeRootfs:
    """A native root filesystem path."""
    path: str


@dataclass
class OverlayfsRootfs:
    """An overlayfs-based root filesystem."""
    lower_dirs: list[str]
    upper_dir: str
    work_dir: str


class Rootfs:
    """Root filesystem configuration."""

    def __init__(self, rootfs_type: str, **kwargs):
        self.rootfs_type = rootfs_type
        if rootfs_type == RootfsType.NATIVE:
            self.native = NativeRootfs(**kwargs)
            self.overlayfs = None
        elif rootfs_type == RootfsType.OVERLAYFS:
            self.native = None
            self.overlayfs = OverlayfsRootfs(**kwargs)
        else:
            raise ValueError(f"Unknown rootfs type: {rootfs_type}")

    @classmethod
    def native(cls, path: str) -> "Rootfs":
        """Create a native rootfs."""
        return cls(RootfsType.NATIVE, path=path)

    @classmethod
    def overlay(cls, lower_dirs: list[str], upper_dir: str, work_dir: str) -> "Rootfs":
        """Create an overlayfs rootfs."""
        return cls(RootfsType.OVERLAYFS, lower_dirs=lower_dirs, upper_dir=upper_dir, work_dir=work_dir)


@dataclass
class MicroVmConfig:
    """Configuration for a MicroVM instance."""
    # VM resources
    num_vcpus: int = 1
    memory_mib: int = 1024
    log_level: LogLevel = LogLevel.OFF

    # Root filesystem
    rootfs: Optional[Rootfs] = None

    # Execution
    exec_path: str = ""
    args: list[str] = field(default_factory=list)
    env_vars: list[EnvPair] = field(default_factory=list)
    workdir: str = "/"

    # Resources
    rlimits: list[LinuxRlimit] = field(default_factory=list)

    # Networking
    port_mappings: list[PortPair] = field(default_factory=list)

    # Volumes
    virtiofs_mounts: list[PathPair] = field(default_factory=list)

    # Misc
    smbios_oem_strings: list[str] = field(default_factory=list)


class MicroVm:
    """A MicroVM instance.

    Manages the lifecycle of an isolated virtual machine using libkrun.
    """

    def __init__(self, config: MicroVmConfig):
        self._config = config
        self._ctx_id: Optional[int] = None

    @property
    def config(self) -> MicroVmConfig:
        """Get the VM configuration."""
        return self._config

    def start(self) -> int:
        """Start the MicroVM.

        Returns:
            The exit code from the VM.
        """
        from microsandbox_core.vm.ffi import LibKrun

        krun = LibKrun()

        # Set log level
        krun.set_log_level(self._config.log_level)

        # Create VM context
        self._ctx_id = krun.create_ctx()

        # Configure VM
        krun.set_vm_config(self._ctx_id, self._config.num_vcpus, self._config.memory_mib)

        # Set root filesystem
        if self._config.rootfs:
            if self._config.rootfs.rootfs_type == RootfsType.NATIVE:
                krun.set_root(self._ctx_id, self._config.rootfs.native.path)
            elif self._config.rootfs.rootfs_type == RootfsType.OVERLAYFS:
                overlay = self._config.rootfs.overlayfs
                krun.set_root_overlayfs(
                    self._ctx_id,
                    overlay.lower_dirs,
                    overlay.upper_dir,
                    overlay.work_dir,
                )

        # Configure port mappings
        for port_pair in self._config.port_mappings:
            krun.set_port_map(self._ctx_id, port_pair)

        # Configure virtiofs mounts
        for mount in self._config.virtiofs_mounts:
            krun.add_virtiofs(self._ctx_id, mount.guest, mount.host)

        # Set working directory
        krun.set_workdir(self._ctx_id, self._config.workdir)

        # Set exec path and args
        krun.set_exec(
            self._ctx_id,
            self._config.exec_path,
            self._config.args,
            self._config.env_vars,
        )

        # Set resource limits
        for rlimit in self._config.rlimits:
            krun.set_rlimit(self._ctx_id, rlimit)

        # Set SMBIOS OEM strings
        if self._config.smbios_oem_strings:
            krun.set_smbios_oem_strings(self._ctx_id, self._config.smbios_oem_strings)

        # Start the VM
        return krun.start_enter(self._ctx_id)
