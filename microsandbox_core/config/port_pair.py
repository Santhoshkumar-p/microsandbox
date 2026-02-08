"""Port mapping type for sandbox configuration."""

from dataclasses import dataclass


@dataclass
class PortPair:
    """A port mapping pair (host:guest or same port).

    Attributes:
        host: The host port number.
        guest: The guest port number.
    """
    host: int
    guest: int

    @classmethod
    def same(cls, port: int) -> "PortPair":
        """Create a PortPair where host and guest are the same."""
        return cls(host=port, guest=port)

    @classmethod
    def distinct(cls, host: int, guest: int) -> "PortPair":
        """Create a PortPair with different host and guest ports."""
        return cls(host=host, guest=guest)

    @classmethod
    def parse(cls, s: str) -> "PortPair":
        """Parse a port pair from a string.

        Formats:
            "8080" -> PortPair(8080, 8080)
            "8080:80" -> PortPair(8080, 80)
        """
        s = s.strip()
        if ":" in s:
            parts = s.split(":", 1)
            return cls.distinct(int(parts[0].strip()), int(parts[1].strip()))
        else:
            port = int(s)
            return cls.same(port)

    def __str__(self) -> str:
        if self.host == self.guest:
            return str(self.host)
        return f"{self.host}:{self.guest}"
