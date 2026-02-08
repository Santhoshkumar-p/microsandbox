"""Path utilities for the microsandbox project."""

import os
from enum import Enum
from pathlib import Path, PurePosixPath

from microsandbox_utils.error import PathValidationError, FileNotFoundError_

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

#: The directory name for microsandbox's project-specific data
MICROSANDBOX_ENV_DIR: str = ".menv"

#: The directory name for microsandbox's global data
MICROSANDBOX_HOME_DIR: str = ".microsandbox"

#: The directory where project read-write layers are stored
RW_SUBDIR: str = "rw"

#: The directory where project patch layers are stored
PATCH_SUBDIR: str = "patch"

#: The directory where project logs are stored
LOG_SUBDIR: str = "log"

#: The directory where global image layers are stored
LAYERS_SUBDIR: str = "layers"

#: The directory where installed sandboxes are stored
INSTALLS_SUBDIR: str = "installs"

#: The filename for the project active sandbox database
SANDBOX_DB_FILENAME: str = "sandbox.db"

#: The filename for the global OCI database
OCI_DB_FILENAME: str = "oci.db"

#: The directory on the microvm where sandbox scripts are stored
SANDBOX_DIR: str = ".sandbox"

#: The directory on the microvm where sandbox scripts are stored
SCRIPTS_DIR: str = "scripts"

#: The suffix added to extracted layer directories
EXTRACTED_LAYER_SUFFIX: str = "extracted"

#: The microsandbox config file name.
MICROSANDBOX_CONFIG_FILENAME: str = "Sandboxfile"

#: The shell script name.
SHELL_SCRIPT_NAME: str = "shell"

#: The directory where namespaces are stored
NAMESPACES_SUBDIR: str = "namespaces"

#: The PID file for the server
SERVER_PID_FILE: str = "server.pid"

#: The server secret key file
SERVER_KEY_FILE: str = "server.key"

#: The file where sandbox portal ports are stored
PORTAL_PORTS_FILE: str = "portal.ports"

#: The XDG home directory
XDG_HOME_DIR: Path = Path.home() / ".local"

#: The bin subdirectory for microsandbox
XDG_BIN_DIR: str = "bin"

#: The lib subdirectory for microsandbox
XDG_LIB_DIR: str = "lib"

#: The suffix for log files
LOG_SUFFIX: str = "log"

#: The filename for the supervisor's log file
SUPERVISOR_LOG_FILENAME: str = "supervisor.log"


# -------------------------------------------------------------------------
# Types
# -------------------------------------------------------------------------


class SupportedPathType(Enum):
    """The type of a supported path."""
    ANY = "any"
    ABSOLUTE = "absolute"
    RELATIVE = "relative"


# -------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------


def normalize_path(path: str, path_type: SupportedPathType = SupportedPathType.ANY) -> str:
    """Normalizes a path string for volume mount comparison.

    Rules:
    - Resolves . and .. components where possible
    - Prevents path traversal that would escape the root
    - Removes redundant separators and trailing slashes
    - Case-sensitive comparison (Unix standard)
    - Can enforce path type requirements (absolute, relative, or any)

    Args:
        path: The path to normalize.
        path_type: The required path type (absolute, relative, or any).

    Returns:
        The normalized path string.

    Raises:
        PathValidationError: If the path is invalid, would escape root,
            or doesn't meet path type requirement.
    """
    if not path:
        raise PathValidationError("Path cannot be empty")

    posix_path = PurePosixPath(path)
    parts = list(posix_path.parts)
    is_absolute = parts[0] == "/" if parts else False

    normalized: list[str] = []
    depth = 0

    start_idx = 1 if is_absolute else 0

    for part in parts[start_idx:]:
        if part == ".":
            continue
        elif part == "..":
            if depth > 0:
                normalized.pop()
                depth -= 1
            else:
                raise PathValidationError(
                    "Invalid path: cannot traverse above root directory"
                )
        else:
            if part:
                normalized.append(part)
                depth += 1

    # Check path type requirements
    if path_type == SupportedPathType.ABSOLUTE and not is_absolute:
        raise PathValidationError("Path must be absolute (start with '/')")
    if path_type == SupportedPathType.RELATIVE and is_absolute:
        raise PathValidationError("Path must be relative (must not start with '/')")

    if is_absolute:
        if not normalized:
            return "/"
        return "/" + "/".join(normalized)
    else:
        return "/".join(normalized)


def resolve_env_path(env_var: str, default_path: Path) -> Path:
    """Resolves the path to a file, checking both environment variable and default locations.

    First checks the environment variable specified by `env_var`.
    If that's not set, falls back to `default_path`.
    Returns an error if the file is not found at the resolved location.

    Args:
        env_var: The environment variable name to check.
        default_path: The default path to use if env var is not set.

    Returns:
        The resolved path.

    Raises:
        FileNotFoundError_: If the file is not found at the resolved location.
    """
    env_val = os.environ.get(env_var)
    if env_val:
        resolved_path = Path(env_val)
        source = "environment variable"
    else:
        resolved_path = default_path
        source = "default path"

    if not resolved_path.exists():
        raise FileNotFoundError_(str(resolved_path), source)

    return resolved_path
