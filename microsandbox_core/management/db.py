"""SQLite database operations for sandbox metadata and image configuration.

This module manages two SQLite databases:
1. Project sandbox database (sandbox.db) - Tracks active sandbox state
2. Global OCI database (oci.db) - Caches image metadata and configurations
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from microsandbox_core.error import DatabaseError
from microsandbox_utils.path import SANDBOX_DB_FILENAME, OCI_DB_FILENAME
from microsandbox_utils.env import get_microsandbox_home_path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for microsandbox."""

    # ---- Sandbox Database ----

    @staticmethod
    async def get_sandbox_db_path(project_dir: Path) -> Path:
        """Get the sandbox database path for a project."""
        from microsandbox_utils.path import MICROSANDBOX_ENV_DIR
        return project_dir / MICROSANDBOX_ENV_DIR / SANDBOX_DB_FILENAME

    @staticmethod
    async def init_sandbox_db(db_path: Path) -> None:
        """Initialize the sandbox database with required tables."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sandboxes (
                    name TEXT PRIMARY KEY,
                    image TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'stopped',
                    pid INTEGER,
                    portal_port INTEGER,
                    config TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sandbox_ports (
                    sandbox_name TEXT NOT NULL,
                    host_port INTEGER NOT NULL,
                    guest_port INTEGER NOT NULL,
                    FOREIGN KEY (sandbox_name) REFERENCES sandboxes(name)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sandbox_volumes (
                    sandbox_name TEXT NOT NULL,
                    host_path TEXT NOT NULL,
                    guest_path TEXT NOT NULL,
                    FOREIGN KEY (sandbox_name) REFERENCES sandboxes(name)
                )
            """)
            await db.commit()

    @staticmethod
    async def set_sandbox_status(
        db_path: Path, name: str, status: str, pid: Optional[int] = None,
        portal_port: Optional[int] = None,
    ) -> None:
        """Update sandbox status in the database."""
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT INTO sandboxes (name, image, status, pid, portal_port)
                VALUES (?, '', ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    status = excluded.status,
                    pid = excluded.pid,
                    portal_port = excluded.portal_port,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (name, status, pid, portal_port),
            )
            await db.commit()

    @staticmethod
    async def get_sandbox_status(db_path: Path, name: str) -> Optional[dict[str, Any]]:
        """Get sandbox status from the database."""
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM sandboxes WHERE name = ?", (name,)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    @staticmethod
    async def list_sandboxes(db_path: Path) -> list[dict[str, Any]]:
        """List all sandboxes in the database."""
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM sandboxes")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    async def remove_sandbox(db_path: Path, name: str) -> None:
        """Remove a sandbox from the database."""
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM sandbox_ports WHERE sandbox_name = ?", (name,))
            await db.execute("DELETE FROM sandbox_volumes WHERE sandbox_name = ?", (name,))
            await db.execute("DELETE FROM sandboxes WHERE name = ?", (name,))
            await db.commit()

    # ---- OCI Database ----

    @staticmethod
    async def get_oci_db_path() -> Path:
        """Get the global OCI database path."""
        return get_microsandbox_home_path() / OCI_DB_FILENAME

    @staticmethod
    async def init_oci_db(db_path: Path) -> None:
        """Initialize the OCI database with required tables."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    reference TEXT PRIMARY KEY,
                    manifest TEXT NOT NULL,
                    config TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS layers (
                    digest TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    media_type TEXT NOT NULL,
                    extracted_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS image_layers (
                    image_reference TEXT NOT NULL,
                    layer_digest TEXT NOT NULL,
                    layer_order INTEGER NOT NULL,
                    FOREIGN KEY (image_reference) REFERENCES images(reference),
                    FOREIGN KEY (layer_digest) REFERENCES layers(digest),
                    PRIMARY KEY (image_reference, layer_digest)
                )
            """)
            await db.commit()

    @staticmethod
    async def cache_image(
        db_path: Path,
        reference: str,
        manifest: dict,
        config: dict,
        layers: list[dict],
    ) -> None:
        """Cache image metadata in the OCI database."""
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO images (reference, manifest, config)
                VALUES (?, ?, ?)
                """,
                (reference, json.dumps(manifest), json.dumps(config)),
            )

            for i, layer in enumerate(layers):
                await db.execute(
                    """
                    INSERT OR REPLACE INTO layers (digest, size, media_type)
                    VALUES (?, ?, ?)
                    """,
                    (layer["digest"], layer.get("size", 0), layer.get("mediaType", "")),
                )
                await db.execute(
                    """
                    INSERT OR REPLACE INTO image_layers (image_reference, layer_digest, layer_order)
                    VALUES (?, ?, ?)
                    """,
                    (reference, layer["digest"], i),
                )

            await db.commit()

    @staticmethod
    async def get_cached_image(db_path: Path, reference: str) -> Optional[dict[str, Any]]:
        """Get cached image metadata from the OCI database."""
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM images WHERE reference = ?", (reference,)
            )
            row = await cursor.fetchone()
            if row:
                result = dict(row)
                result["manifest"] = json.loads(result["manifest"])
                result["config"] = json.loads(result["config"])
                return result
            return None
