"""Default values and constants used throughout the microsandbox project."""

import os
import sys
from pathlib import Path
from functools import lru_cache

from microsandbox_utils.path import MICROSANDBOX_HOME_DIR

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

#: The default maximum log file size (10MB)
DEFAULT_LOG_MAX_SIZE: int = 10 * 1024 * 1024

#: The default number of vCPUs to use for the MicroVm.
DEFAULT_NUM_VCPUS: int = 1

#: The default amount of memory in MiB to use for the MicroVm.
DEFAULT_MEMORY_MIB: int = 1024

#: The default OCI registry domain.
DEFAULT_OCI_REGISTRY: str = "docker.io"

#: The default OCI reference tag.
DEFAULT_OCI_REFERENCE_TAG: str = "latest"

#: The default OCI reference repository namespace.
DEFAULT_OCI_REFERENCE_REPO_NAMESPACE: str = "library"

#: The default configuration file content
DEFAULT_CONFIG: str = "# Sandbox configurations\nsandboxes:\n"

#: The default shell to use for the sandbox.
DEFAULT_SHELL: str = "/bin/sh"

#: The default working directory for the sandbox.
DEFAULT_WORKDIR: str = "/"

#: The default namespace for the sandbox server.
DEFAULT_SERVER_NAMESPACE: str = "default"

#: The default localhost address.
DEFAULT_SERVER_HOST: str = "127.0.0.1"

#: The default microsandbox-server port.
DEFAULT_SERVER_PORT: int = 5555

#: The default microsandbox-portal port.
DEFAULT_PORTAL_GUEST_PORT: int = 4444


@lru_cache(maxsize=1)
def get_default_microsandbox_home() -> Path:
    """The path where all microsandbox global data is stored."""
    return Path.home() / MICROSANDBOX_HOME_DIR


#: The path where all microsandbox global data is stored.
DEFAULT_MICROSANDBOX_HOME: Path = get_default_microsandbox_home()


@lru_cache(maxsize=1)
def get_default_msbrun_exe_path() -> Path:
    """The default path to the msbrun binary."""
    current_exe = Path(sys.executable).resolve()
    return current_exe.parent / "msbrun"


@lru_cache(maxsize=1)
def get_default_msbserver_exe_path() -> Path:
    """The default path to the msbserver binary."""
    current_exe = Path(sys.executable).resolve()
    return current_exe.parent / "msbserver"


DEFAULT_MSBRUN_EXE_PATH: Path = get_default_msbrun_exe_path()
DEFAULT_MSBSERVER_EXE_PATH: Path = get_default_msbserver_exe_path()
