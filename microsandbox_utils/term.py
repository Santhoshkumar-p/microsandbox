"""Terminal utilities for the microsandbox project."""

import os
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# -------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------

#: Console for rich output
console = Console()

#: The checkmark for CLI visualizations
CHECKMARK: str = "[green]\u2713[/green]"

#: The error mark for CLI visualizations
ERROR_MARK: str = "[red]\u2717[/red]"

#: Spinner characters
TICK_STRINGS: list[str] = ["\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834",
                            "\u2826", "\u2827", "\u2807", "\u280f"]


# -------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------


def is_interactive_terminal() -> bool:
    """Determines if the process is running in an interactive terminal environment."""
    stdin_is_tty = sys.stdin.isatty() if hasattr(sys.stdin, 'isatty') else False
    stdout_is_tty = sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else False
    return stdin_is_tty and stdout_is_tty


def is_ansi_interactive_terminal() -> bool:
    """Determines if the process is running in an ANSI terminal environment."""
    term = os.environ.get("TERM", "")
    return is_interactive_terminal() and "dumb" not in term


def create_progress() -> Progress:
    """Creates a Rich progress instance for visualizing operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


def print_success(message: str) -> None:
    """Print a success message with a checkmark."""
    console.print(f"{CHECKMARK} {message}")


def print_error(message: str) -> None:
    """Print an error message with an error mark."""
    console.print(f"{ERROR_MARK} {message}")
