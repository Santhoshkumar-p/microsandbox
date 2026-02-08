"""Global microsandbox home directory management.

Manages the ~/.microsandbox directory which stores global data
including layers, installed sandboxes, and server configuration.
"""

import logging
import shutil
from pathlib import Path

from microsandbox_utils.defaults import DEFAULT_MICROSANDBOX_HOME
from microsandbox_utils.env import get_microsandbox_home_path
from microsandbox_utils.path import (
    INSTALLS_SUBDIR,
    LAYERS_SUBDIR,
    NAMESPACES_SUBDIR,
    SERVER_KEY_FILE,
    SERVER_PID_FILE,
    XDG_BIN_DIR,
    XDG_HOME_DIR,
)

logger = logging.getLogger(__name__)


class HomeManager:
    """Manages the microsandbox home directory."""

    @staticmethod
    def get_home() -> Path:
        """Get the microsandbox home directory path."""
        return get_microsandbox_home_path()

    @staticmethod
    def init_home() -> Path:
        """Initialize the microsandbox home directory.

        Creates the directory structure:
        - ~/.microsandbox/layers/
        - ~/.microsandbox/installs/
        - ~/.microsandbox/namespaces/

        Returns:
            Path to the home directory.
        """
        home = get_microsandbox_home_path()
        home.mkdir(parents=True, exist_ok=True)
        (home / LAYERS_SUBDIR).mkdir(exist_ok=True)
        (home / INSTALLS_SUBDIR).mkdir(exist_ok=True)
        (home / NAMESPACES_SUBDIR).mkdir(exist_ok=True)
        return home

    @staticmethod
    def clean(
        clean_all: bool = False,
        clean_layers: bool = False,
        clean_user: bool = False,
        force: bool = False,
    ) -> None:
        """Clean microsandbox home directory data.

        Args:
            clean_all: Remove the entire home directory.
            clean_layers: Remove only the layers directory.
            clean_user: Remove user-installed sandboxes.
            force: Force removal without confirmation.
        """
        home = get_microsandbox_home_path()

        if not home.exists():
            logger.info("No microsandbox home directory found")
            return

        if clean_all:
            if force:
                shutil.rmtree(home)
                logger.info(f"Removed microsandbox home directory: {home}")
            else:
                logger.warning("Use --force to remove the entire home directory")
            return

        if clean_layers:
            layers_dir = home / LAYERS_SUBDIR
            if layers_dir.exists():
                shutil.rmtree(layers_dir)
                layers_dir.mkdir()
                logger.info("Cleaned layers directory")

        if clean_user:
            installs_dir = home / INSTALLS_SUBDIR
            if installs_dir.exists():
                shutil.rmtree(installs_dir)
                installs_dir.mkdir()
                logger.info("Cleaned installed sandboxes")

            # Clean XDG bin links
            bin_dir = XDG_HOME_DIR / XDG_BIN_DIR
            if bin_dir.exists():
                for link in bin_dir.iterdir():
                    if link.is_symlink():
                        target = link.resolve()
                        if str(installs_dir) in str(target):
                            link.unlink()
                            logger.info(f"Removed symlink: {link}")

    @staticmethod
    def install_sandbox(alias: str, script_content: str) -> Path:
        """Install a sandbox as a system command.

        Args:
            alias: The command alias name.
            script_content: The shell script content.

        Returns:
            Path to the installed script.
        """
        home = get_microsandbox_home_path()
        installs_dir = home / INSTALLS_SUBDIR
        installs_dir.mkdir(parents=True, exist_ok=True)

        script_path = installs_dir / alias
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        # Create symlink in XDG bin
        bin_dir = XDG_HOME_DIR / XDG_BIN_DIR
        bin_dir.mkdir(parents=True, exist_ok=True)

        link_path = bin_dir / alias
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to(script_path)

        logger.info(f"Installed sandbox '{alias}' -> {script_path}")
        return script_path

    @staticmethod
    def uninstall_sandbox(alias: str) -> None:
        """Uninstall a sandbox command.

        Args:
            alias: The command alias name.
        """
        home = get_microsandbox_home_path()
        script_path = home / INSTALLS_SUBDIR / alias

        if script_path.exists():
            script_path.unlink()

        # Remove symlink
        link_path = XDG_HOME_DIR / XDG_BIN_DIR / alias
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()

        logger.info(f"Uninstalled sandbox '{alias}'")
