"""Resource limit configuration for MicroVMs."""

import resource
from dataclasses import dataclass
from enum import IntEnum


class LinuxRLimitResource(IntEnum):
    """Linux resource limit types."""
    RLIMIT_CPU = resource.RLIMIT_CPU
    RLIMIT_FSIZE = resource.RLIMIT_FSIZE
    RLIMIT_DATA = resource.RLIMIT_DATA
    RLIMIT_STACK = resource.RLIMIT_STACK
    RLIMIT_CORE = resource.RLIMIT_CORE
    RLIMIT_RSS = resource.RLIMIT_RSS
    RLIMIT_NPROC = resource.RLIMIT_NPROC
    RLIMIT_NOFILE = resource.RLIMIT_NOFILE
    RLIMIT_MEMLOCK = resource.RLIMIT_MEMLOCK
    RLIMIT_AS = resource.RLIMIT_AS


@dataclass
class LinuxRlimit:
    """A Linux resource limit.

    Attributes:
        resource: The resource type to limit.
        cur: The soft limit.
        max: The hard limit.
    """
    resource: LinuxRLimitResource
    cur: int
    max: int

    @classmethod
    def nofile(cls, soft: int, hard: int) -> "LinuxRlimit":
        """Create a NOFILE (open file descriptors) limit."""
        return cls(resource=LinuxRLimitResource.RLIMIT_NOFILE, cur=soft, max=hard)

    @classmethod
    def nproc(cls, soft: int, hard: int) -> "LinuxRlimit":
        """Create a NPROC (number of processes) limit."""
        return cls(resource=LinuxRLimitResource.RLIMIT_NPROC, cur=soft, max=hard)
