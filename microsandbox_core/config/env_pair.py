"""Environment variable pair for sandbox configuration."""

from dataclasses import dataclass


@dataclass
class EnvPair:
    """An environment variable key-value pair.

    Attributes:
        key: The environment variable name.
        value: The environment variable value.
    """
    key: str
    value: str

    @classmethod
    def parse(cls, s: str) -> "EnvPair":
        """Parse an environment pair from a string.

        Format: "KEY=VALUE"
        """
        s = s.strip()
        if "=" not in s:
            raise ValueError(f"Invalid environment variable format: {s!r} (expected KEY=VALUE)")
        key, value = s.split("=", 1)
        return cls(key=key.strip(), value=value.strip())

    def __str__(self) -> str:
        return f"{self.key}={self.value}"
