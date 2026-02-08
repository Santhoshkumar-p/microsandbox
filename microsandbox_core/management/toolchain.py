"""Microsandbox toolchain lifecycle management.

Manages the installation, detection, and cleanup of microsandbox executables
and their associated libraries.
"""

import logging
import shutil
from pathlib import Path

from microsandbox_utils.path import XDG_BIN_DIR, XDG_HOME_DIR, XDG_LIB_DIR

logger = logging.getLogger(__name__)

# Microsandbox executables
EXECUTABLES = ["msb", "msbrun", "msbserver"]

# Microsandbox libraries
LIBRARIES = ["libkrun.so", "libkrunfw.so", "libkrun.dylib"]


class ToolchainManager:
    """Manages microsandbox toolchain installation and cleanup."""

    @staticmethod
    def get_bin_dir() -> Path:
        """Get the binary installation directory."""
        return XDG_HOME_DIR / XDG_BIN_DIR

    @staticmethod
    def get_lib_dir() -> Path:
        """Get the library installation directory."""
        return XDG_HOME_DIR / XDG_LIB_DIR

    @staticmethod
    def is_installed() -> bool:
        """Check if microsandbox toolchain is installed."""
        bin_dir = ToolchainManager.get_bin_dir()
        return any((bin_dir / exe).exists() for exe in EXECUTABLES)

    @staticmethod
    def uninstall(force: bool = False) -> None:
        """Uninstall the microsandbox toolchain.

        Args:
            force: Whether to force uninstallation.
        """
        bin_dir = ToolchainManager.get_bin_dir()
        lib_dir = ToolchainManager.get_lib_dir()

        # Remove executables
        for exe in EXECUTABLES:
            exe_path = bin_dir / exe
            if exe_path.exists():
                exe_path.unlink()
                logger.info(f"Removed {exe_path}")

        # Remove libraries
        for lib in LIBRARIES:
            lib_path = lib_dir / lib
            if lib_path.exists():
                lib_path.unlink()
                logger.info(f"Removed {lib_path}")

        logger.info("Microsandbox toolchain uninstalled")

    @staticmethod
    def find_executable(name: str) -> Path | None:
        """Find a microsandbox executable.

        Args:
            name: The executable name.

        Returns:
            Path to the executable, or None if not found.
        """
        bin_dir = ToolchainManager.get_bin_dir()
        exe_path = bin_dir / name
        if exe_path.exists():
            return exe_path

        # Also check PATH
        import shutil as sh
        found = sh.which(name)
        if found:
            return Path(found)

        return None
