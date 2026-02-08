"""Utility functions for working with environment variables."""

import os
from pathlib import Path

from microsandbox_utils.defaults import DEFAULT_MICROSANDBOX_HOME, DEFAULT_OCI_REGISTRY

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

#: Environment variable for the microsandbox home directory
MICROSANDBOX_HOME_ENV_VAR: str = "MICROSANDBOX_HOME"

#: Environment variable for the OCI registry domain
OCI_REGISTRY_ENV_VAR: str = "OCI_REGISTRY_DOMAIN"

#: Environment variable for the msbrun binary path
MSBRUN_EXE_ENV_VAR: str = "MSBRUN_EXE"

#: Environment variable for the msbserver binary path
MSBSERVER_EXE_ENV_VAR: str = "MSBSERVER_EXE"


# -------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------


def get_microsandbox_home_path() -> Path:
    """Returns the path to the microsandbox home directory.

    If the MICROSANDBOX_HOME environment variable is set, returns that path.
    Otherwise, returns the default microsandbox home path.
    """
    env_val = os.environ.get(MICROSANDBOX_HOME_ENV_VAR)
    if env_val:
        return Path(env_val)
    return DEFAULT_MICROSANDBOX_HOME


def get_oci_registry() -> str:
    """Returns the domain for the OCI registry.

    If the OCI_REGISTRY_DOMAIN environment variable is set, returns that value.
    Otherwise, returns the default OCI registry domain.
    """
    return os.environ.get(OCI_REGISTRY_ENV_VAR, DEFAULT_OCI_REGISTRY)
