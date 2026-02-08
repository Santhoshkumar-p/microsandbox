"""Path mapping type for volume mounts in sandbox configuration."""

from dataclasses import dataclass


@dataclass
class PathPair:
    """A path mapping pair (host:guest or same path).

    Attributes:
        host: The host path.
        guest: The guest path.
    """
    host: str
    guest: str

    @classmethod
    def same(cls, path: str) -> "PathPair":
        """Create a PathPair where host and guest are the same."""
        return cls(host=path, guest=path)

    @classmethod
    def distinct(cls, host: str, guest: str) -> "PathPair":
        """Create a PathPair with different host and guest paths."""
        return cls(host=host, guest=guest)

    @classmethod
    def parse(cls, s: str) -> "PathPair":
        """Parse a path pair from a string.

        Formats:
            "/data" -> PathPair("/data", "/data")
            "./app:/container/app" -> PathPair("./app", "/container/app")
        """
        s = s.strip()
        if ":" in s:
            # Handle potential Windows-style paths or paths with colons
            parts = s.split(":", 1)
            return cls.distinct(parts[0].strip(), parts[1].strip())
        else:
            return cls.same(s)

    def __str__(self) -> str:
        if self.host == self.guest:
            return self.host
        return f"{self.host}:{self.guest}"
