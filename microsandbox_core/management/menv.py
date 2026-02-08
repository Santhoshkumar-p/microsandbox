"""Microsandbox environment initialization and cleanup.

Manages the .menv project directory which stores sandbox state,
read-write layers, patch layers, and logs.
"""

import logging
import shutil
from pathlib import Path

from microsandbox_core.error import ManagementError
from microsandbox_core.management.db import DatabaseManager
from microsandbox_utils.path import (
    LOG_SUBDIR,
    MICROSANDBOX_ENV_DIR,
    PATCH_SUBDIR,
    RW_SUBDIR,
)

logger = logging.getLogger(__name__)


class MenvManager:
    """Manages the microsandbox environment directory."""

    @staticmethod
    async def init(project_dir: Path) -> Path:
        """Initialize a microsandbox environment directory.

        Creates the .menv directory structure:
        - .menv/rw/      - Read-write layers
        - .menv/patch/    - Patch layers
        - .menv/log/      - Log files
        - .menv/sandbox.db - Sandbox database

        Args:
            project_dir: The project root directory.

        Returns:
            Path to the .menv directory.
        """
        menv_dir = project_dir / MICROSANDBOX_ENV_DIR
        menv_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (menv_dir / RW_SUBDIR).mkdir(exist_ok=True)
        (menv_dir / PATCH_SUBDIR).mkdir(exist_ok=True)
        (menv_dir / LOG_SUBDIR).mkdir(exist_ok=True)

        # Initialize database
        db_path = await DatabaseManager.get_sandbox_db_path(project_dir)
        await DatabaseManager.init_sandbox_db(db_path)

        logger.info(f"Initialized microsandbox environment at {menv_dir}")
        return menv_dir

    @staticmethod
    async def clean(
        project_dir: Path,
        sandbox_name: str | None = None,
        force: bool = False,
    ) -> None:
        """Clean microsandbox environment data.

        Args:
            project_dir: The project root directory.
            sandbox_name: Optional specific sandbox to clean.
            force: Whether to force clean without confirmation.
        """
        menv_dir = project_dir / MICROSANDBOX_ENV_DIR

        if not menv_dir.exists():
            logger.info("No microsandbox environment found")
            return

        if sandbox_name:
            # Clean specific sandbox data
            for subdir in [RW_SUBDIR, PATCH_SUBDIR, LOG_SUBDIR]:
                sandbox_dir = menv_dir / subdir / sandbox_name
                if sandbox_dir.exists():
                    shutil.rmtree(sandbox_dir)
                    logger.info(f"Cleaned {subdir}/{sandbox_name}")

            # Remove from database
            db_path = await DatabaseManager.get_sandbox_db_path(project_dir)
            if db_path.exists():
                await DatabaseManager.remove_sandbox(db_path, sandbox_name)
        else:
            # Clean all environment data
            if force:
                shutil.rmtree(menv_dir)
                logger.info(f"Removed microsandbox environment at {menv_dir}")
            else:
                # Clean subdirectories but keep the structure
                for subdir in [RW_SUBDIR, PATCH_SUBDIR, LOG_SUBDIR]:
                    dir_path = menv_dir / subdir
                    if dir_path.exists():
                        shutil.rmtree(dir_path)
                        dir_path.mkdir()
                logger.info("Cleaned microsandbox environment data")

    @staticmethod
    def exists(project_dir: Path) -> bool:
        """Check if a microsandbox environment exists.

        Args:
            project_dir: The project root directory.

        Returns:
            True if the .menv directory exists.
        """
        return (project_dir / MICROSANDBOX_ENV_DIR).exists()
