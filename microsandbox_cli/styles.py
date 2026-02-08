"""CLI output styling utilities using Rich."""

from rich.style import Style
from rich.text import Text
from rich.console import Console

from microsandbox_utils.term import is_ansi_interactive_terminal

console = Console()

# Style definitions matching the Rust CLI styles
HEADER_STYLE = Style(color="yellow", bold=True)
USAGE_STYLE = Style(color="yellow", bold=True)
LITERAL_STYLE = Style(color="blue", bold=True)
PLACEHOLDER_STYLE = Style(color="green")
ERROR_STYLE = Style(color="red", bold=True)
VALID_STYLE = Style(color="green", bold=True)
INVALID_STYLE = Style(color="red", bold=True)


def styled(text: str, style: Style) -> str:
    """Apply a Rich style to text and return as string."""
    if not is_ansi_interactive_terminal():
        return text
    t = Text(text)
    t.stylize(style)
    return t.__rich_console__(console, console.options).__next__()


def header(text: str) -> str:
    """Apply header style."""
    return styled(text, HEADER_STYLE)


def literal(text: str) -> str:
    """Apply literal style."""
    return styled(text, LITERAL_STYLE)


def placeholder(text: str) -> str:
    """Apply placeholder style."""
    return styled(text, PLACEHOLDER_STYLE)


def error_style(text: str) -> str:
    """Apply error style."""
    return styled(text, ERROR_STYLE)


def valid(text: str) -> str:
    """Apply valid style."""
    return styled(text, VALID_STYLE)
