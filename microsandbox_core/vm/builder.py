"""Builder pattern for MicroVM configuration.

Provides a fluent interface for constructing MicroVM instances.
"""

from pathlib import Path
from typing import Optional

from microsandbox_core.config.env_pair import EnvPair
from microsandbox_core.config.path_pair import PathPair
from microsandbox_core.config.port_pair import PortPair
from microsandbox_core.vm.microvm import LogLevel, MicroVm, MicroVmConfig, Rootfs
from microsandbox_core.vm.rlimit import LinuxRlimit
from microsandbox_utils.defaults import DEFAULT_NUM_VCPUS, DEFAULT_MEMORY_MIB


# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class MicroVmConfigBuilder:
    """Builder for MicroVmConfig."""

    def __init__(self):
        self._num_vcpus = DEFAULT_NUM_VCPUS
        self._memory_mib = DEFAULT_MEMORY_MIB
        self._log_level = LogLevel.OFF
        self._rootfs: Optional[Rootfs] = None
        self._exec_path = ""
        self._args: list[str] = []
        self._env_vars: list[EnvPair] = []
        self._workdir = "/"
        self._rlimits: list[LinuxRlimit] = []
        self._port_mappings: list[PortPair] = []
        self._virtiofs_mounts: list[PathPair] = []
        self._smbios_oem_strings: list[str] = []

    def num_vcpus(self, num: int) -> "MicroVmConfigBuilder":
        """Set the number of virtual CPUs."""
        self._num_vcpus = num
        return self

    def memory_mib(self, mib: int) -> "MicroVmConfigBuilder":
        """Set the memory size in MiB."""
        self._memory_mib = mib
        return self

    def log_level(self, level: LogLevel) -> "MicroVmConfigBuilder":
        """Set the log level."""
        self._log_level = level
        return self

    def rootfs(self, rootfs: Rootfs) -> "MicroVmConfigBuilder":
        """Set the root filesystem."""
        self._rootfs = rootfs
        return self

    def exec_path(self, path: str) -> "MicroVmConfigBuilder":
        """Set the executable path."""
        self._exec_path = path
        return self

    def args(self, args: list[str]) -> "MicroVmConfigBuilder":
        """Set the command arguments."""
        self._args = args
        return self

    def env_var(self, key: str, value: str) -> "MicroVmConfigBuilder":
        """Add an environment variable."""
        self._env_vars.append(EnvPair(key=key, value=value))
        return self

    def env_vars(self, pairs: list[EnvPair]) -> "MicroVmConfigBuilder":
        """Set all environment variables."""
        self._env_vars = pairs
        return self

    def workdir(self, path: str) -> "MicroVmConfigBuilder":
        """Set the working directory."""
        self._workdir = path
        return self

    def rlimit(self, rlimit: LinuxRlimit) -> "MicroVmConfigBuilder":
        """Add a resource limit."""
        self._rlimits.append(rlimit)
        return self

    def rlimits(self, rlimits: list[LinuxRlimit]) -> "MicroVmConfigBuilder":
        """Set all resource limits."""
        self._rlimits = rlimits
        return self

    def port_mapping(self, pair: PortPair) -> "MicroVmConfigBuilder":
        """Add a port mapping."""
        self._port_mappings.append(pair)
        return self

    def port_mappings(self, pairs: list[PortPair]) -> "MicroVmConfigBuilder":
        """Set all port mappings."""
        self._port_mappings = pairs
        return self

    def virtiofs_mount(self, mount: PathPair) -> "MicroVmConfigBuilder":
        """Add a virtiofs mount."""
        self._virtiofs_mounts.append(mount)
        return self

    def virtiofs_mounts(self, mounts: list[PathPair]) -> "MicroVmConfigBuilder":
        """Set all virtiofs mounts."""
        self._virtiofs_mounts = mounts
        return self

    def smbios_oem_string(self, s: str) -> "MicroVmConfigBuilder":
        """Add an SMBIOS OEM string."""
        self._smbios_oem_strings.append(s)
        return self

    def smbios_oem_strings(self, strings: list[str]) -> "MicroVmConfigBuilder":
        """Set all SMBIOS OEM strings."""
        self._smbios_oem_strings = strings
        return self

    def build(self) -> MicroVmConfig:
        """Build the MicroVmConfig."""
        return MicroVmConfig(
            num_vcpus=self._num_vcpus,
            memory_mib=self._memory_mib,
            log_level=self._log_level,
            rootfs=self._rootfs,
            exec_path=self._exec_path,
            args=self._args,
            env_vars=self._env_vars,
            workdir=self._workdir,
            rlimits=self._rlimits,
            port_mappings=self._port_mappings,
            virtiofs_mounts=self._virtiofs_mounts,
            smbios_oem_strings=self._smbios_oem_strings,
        )


class MicroVmBuilder:
    """Builder for creating MicroVm instances."""

    def __init__(self):
        self._config_builder = MicroVmConfigBuilder()

    def num_vcpus(self, num: int) -> "MicroVmBuilder":
        """Set the number of virtual CPUs."""
        self._config_builder.num_vcpus(num)
        return self

    def memory_mib(self, mib: int) -> "MicroVmBuilder":
        """Set the memory size in MiB."""
        self._config_builder.memory_mib(mib)
        return self

    def log_level(self, level: LogLevel) -> "MicroVmBuilder":
        """Set the log level."""
        self._config_builder.log_level(level)
        return self

    def rootfs(self, rootfs: Rootfs) -> "MicroVmBuilder":
        """Set the root filesystem."""
        self._config_builder.rootfs(rootfs)
        return self

    def exec_path(self, path: str) -> "MicroVmBuilder":
        """Set the executable path."""
        self._config_builder.exec_path(path)
        return self

    def args(self, args: list[str]) -> "MicroVmBuilder":
        """Set the command arguments."""
        self._config_builder.args(args)
        return self

    def env_var(self, key: str, value: str) -> "MicroVmBuilder":
        """Add an environment variable."""
        self._config_builder.env_var(key, value)
        return self

    def workdir(self, path: str) -> "MicroVmBuilder":
        """Set the working directory."""
        self._config_builder.workdir(path)
        return self

    def port_mapping(self, pair: PortPair) -> "MicroVmBuilder":
        """Add a port mapping."""
        self._config_builder.port_mapping(pair)
        return self

    def virtiofs_mount(self, mount: PathPair) -> "MicroVmBuilder":
        """Add a virtiofs mount."""
        self._config_builder.virtiofs_mount(mount)
        return self

    def smbios_oem_string(self, s: str) -> "MicroVmBuilder":
        """Add an SMBIOS OEM string."""
        self._config_builder.smbios_oem_string(s)
        return self

    def build(self) -> MicroVm:
        """Build the MicroVm instance."""
        config = self._config_builder.build()
        return MicroVm(config)
