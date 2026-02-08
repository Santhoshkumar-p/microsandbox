"""FFI bindings to libkrun.

This module provides Python bindings to the libkrun C library for
creating and managing lightweight virtual machines.
"""

import ctypes
import ctypes.util
import logging
from pathlib import Path
from typing import Optional

from microsandbox_core.config.env_pair import EnvPair
from microsandbox_core.config.port_pair import PortPair
from microsandbox_core.vm.rlimit import LinuxRlimit

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class LibKrun:
    """Python bindings for the libkrun C library.

    Provides methods for creating and managing microVM instances
    through the krun API.
    """

    def __init__(self, lib_path: Optional[str] = None):
        """Initialize libkrun bindings.

        Args:
            lib_path: Optional path to the libkrun shared library.
                     If not provided, searches standard library paths.
        """
        self._lib = None
        self._loaded = False

        if lib_path:
            try:
                self._lib = ctypes.CDLL(lib_path)
                self._loaded = True
            except OSError as e:
                logger.warning(f"Failed to load libkrun from {lib_path}: {e}")
        else:
            # Try to find libkrun in standard locations
            for name in ["libkrun.so", "libkrun.dylib", "libkrun.so.1"]:
                lib_found = ctypes.util.find_library(name.replace("lib", "").split(".")[0])
                if lib_found:
                    try:
                        self._lib = ctypes.CDLL(lib_found)
                        self._loaded = True
                        break
                    except OSError:
                        continue

            if not self._loaded:
                # Try direct paths
                for search_path in [
                    Path.home() / ".local" / "lib",
                    Path("/usr/local/lib"),
                    Path("/usr/lib"),
                ]:
                    for name in ["libkrun.so", "libkrun.dylib", "libkrun.so.1"]:
                        full_path = search_path / name
                        if full_path.exists():
                            try:
                                self._lib = ctypes.CDLL(str(full_path))
                                self._loaded = True
                                break
                            except OSError:
                                continue
                    if self._loaded:
                        break

        if not self._loaded:
            logger.warning(
                "libkrun not found. VM operations will not be available. "
                "Install libkrun to enable microVM support."
            )

    @property
    def is_available(self) -> bool:
        """Check if libkrun is loaded and available."""
        return self._loaded

    def _check_loaded(self) -> None:
        """Ensure libkrun is loaded."""
        if not self._loaded:
            raise RuntimeError(
                "libkrun is not available. Install libkrun to enable microVM support."
            )

    def set_log_level(self, level: int) -> None:
        """Set the log level for krun."""
        self._check_loaded()
        self._lib.krun_set_log_level(ctypes.c_uint32(level))

    def create_ctx(self) -> int:
        """Create a new VM context.

        Returns:
            The context ID for the new VM.
        """
        self._check_loaded()
        ctx_id = self._lib.krun_create_ctx()
        if ctx_id < 0:
            raise RuntimeError(f"Failed to create krun context: {ctx_id}")
        return ctx_id

    def set_vm_config(self, ctx_id: int, num_vcpus: int, ram_mib: int) -> None:
        """Configure VM resources."""
        self._check_loaded()
        ret = self._lib.krun_set_vm_config(
            ctypes.c_uint32(ctx_id),
            ctypes.c_uint8(num_vcpus),
            ctypes.c_uint32(ram_mib),
        )
        if ret < 0:
            raise RuntimeError(f"Failed to set VM config: {ret}")

    def set_root(self, ctx_id: int, root_path: str) -> None:
        """Set the root filesystem path."""
        self._check_loaded()
        ret = self._lib.krun_set_root(
            ctypes.c_uint32(ctx_id),
            ctypes.c_char_p(root_path.encode("utf-8")),
        )
        if ret < 0:
            raise RuntimeError(f"Failed to set root: {ret}")

    def set_root_overlayfs(
        self, ctx_id: int, lower_dirs: list[str], upper_dir: str, work_dir: str
    ) -> None:
        """Set an overlayfs root filesystem."""
        self._check_loaded()
        # Convert lower_dirs to C array of strings
        lower_arr = (ctypes.c_char_p * len(lower_dirs))(
            *[d.encode("utf-8") for d in lower_dirs]
        )
        ret = self._lib.krun_set_root_overlayfs(
            ctypes.c_uint32(ctx_id),
            lower_arr,
            ctypes.c_size_t(len(lower_dirs)),
            ctypes.c_char_p(upper_dir.encode("utf-8")),
            ctypes.c_char_p(work_dir.encode("utf-8")),
        )
        if ret < 0:
            raise RuntimeError(f"Failed to set overlayfs root: {ret}")

    def set_port_map(self, ctx_id: int, port_pair: PortPair) -> None:
        """Set a port mapping."""
        self._check_loaded()
        port_str = f"{port_pair.host}:{port_pair.guest}"
        ret = self._lib.krun_set_port_map(
            ctypes.c_uint32(ctx_id),
            ctypes.c_char_p(port_str.encode("utf-8")),
        )
        if ret < 0:
            raise RuntimeError(f"Failed to set port map: {ret}")

    def add_virtiofs(self, ctx_id: int, tag: str, path: str) -> None:
        """Add a virtiofs mount."""
        self._check_loaded()
        ret = self._lib.krun_add_virtiofs(
            ctypes.c_uint32(ctx_id),
            ctypes.c_char_p(tag.encode("utf-8")),
            ctypes.c_char_p(path.encode("utf-8")),
        )
        if ret < 0:
            raise RuntimeError(f"Failed to add virtiofs: {ret}")

    def set_workdir(self, ctx_id: int, workdir: str) -> None:
        """Set the working directory."""
        self._check_loaded()
        ret = self._lib.krun_set_workdir(
            ctypes.c_uint32(ctx_id),
            ctypes.c_char_p(workdir.encode("utf-8")),
        )
        if ret < 0:
            raise RuntimeError(f"Failed to set workdir: {ret}")

    def set_exec(
        self,
        ctx_id: int,
        exec_path: str,
        args: list[str],
        env_vars: list[EnvPair],
    ) -> None:
        """Set the executable and its arguments."""
        self._check_loaded()
        # Convert args to C array
        argv = (ctypes.c_char_p * (len(args) + 1))(
            *[a.encode("utf-8") for a in args],
            None,
        )

        # Convert env vars to C array
        env_strs = [f"{e.key}={e.value}" for e in env_vars]
        envp = (ctypes.c_char_p * (len(env_strs) + 1))(
            *[e.encode("utf-8") for e in env_strs],
            None,
        )

        ret = self._lib.krun_set_exec(
            ctypes.c_uint32(ctx_id),
            ctypes.c_char_p(exec_path.encode("utf-8")),
            argv,
            envp,
        )
        if ret < 0:
            raise RuntimeError(f"Failed to set exec: {ret}")

    def set_rlimit(self, ctx_id: int, rlimit: LinuxRlimit) -> None:
        """Set a resource limit."""
        self._check_loaded()
        # Use the rlimit resource value and limits
        ret = self._lib.krun_set_rlimit(
            ctypes.c_uint32(ctx_id),
            ctypes.c_int(rlimit.resource.value),
            ctypes.c_uint64(rlimit.cur),
            ctypes.c_uint64(rlimit.max),
        )
        if ret < 0:
            raise RuntimeError(f"Failed to set rlimit: {ret}")

    def set_smbios_oem_strings(self, ctx_id: int, oem_strings: list[str]) -> None:
        """Set SMBIOS OEM strings."""
        self._check_loaded()
        arr = (ctypes.c_char_p * len(oem_strings))(
            *[s.encode("utf-8") for s in oem_strings]
        )
        ret = self._lib.krun_set_smbios_oem_strings(
            ctypes.c_uint32(ctx_id),
            arr,
            ctypes.c_size_t(len(oem_strings)),
        )
        if ret < 0:
            raise RuntimeError(f"Failed to set SMBIOS OEM strings: {ret}")

    def start_enter(self, ctx_id: int) -> int:
        """Start the VM and wait for it to exit.

        Returns:
            The exit code from the VM.
        """
        self._check_loaded()
        ret = self._lib.krun_start_enter(ctypes.c_uint32(ctx_id))
        return ret
