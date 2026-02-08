"""Main CLI entry point for microsandbox (msb).

Provides the full command-line interface for managing sandboxes,
images, configurations, and the orchestration server.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from microsandbox_cli.handlers import (
    handle_add,
    handle_apply,
    handle_clean,
    handle_down,
    handle_exe,
    handle_init,
    handle_install,
    handle_list,
    handle_log,
    handle_login,
    handle_pull,
    handle_push,
    handle_remove,
    handle_run,
    handle_self_action,
    handle_shell,
    handle_status,
    handle_uninstall,
    handle_up,
)

console = Console()

# -------------------------------------------------------------------------
# Main CLI App
# -------------------------------------------------------------------------

app = typer.Typer(
    name="msb",
    help="msb (microsandbox) is a tool for managing lightweight sandboxes and images",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Server subcommand group
server_app = typer.Typer(
    name="server",
    help="Manage the microsandbox server",
    no_args_is_help=True,
)
app.add_typer(server_app, name="server")

# Self subcommand group
self_app = typer.Typer(
    name="self",
    help="Manage microsandbox itself",
    no_args_is_help=True,
)
app.add_typer(self_app, name="self")


# -------------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------------


def setup_logging(error: bool, warn: bool, info: bool, debug: bool, trace: bool) -> None:
    """Configure logging based on CLI flags."""
    if trace:
        level = logging.DEBUG  # Python doesn't have TRACE
    elif debug:
        level = logging.DEBUG
    elif info:
        level = logging.INFO
    elif warn:
        level = logging.WARNING
    elif error:
        level = logging.ERROR
    else:
        return  # No logging configured

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# -------------------------------------------------------------------------
# Global Options Callback
# -------------------------------------------------------------------------


@app.callback()
def main_callback(
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
    error: bool = typer.Option(False, "--error", help="Show logs with error level"),
    warn: bool = typer.Option(False, "--warn", help="Show logs with warn level"),
    info: bool = typer.Option(False, "--info", help="Show logs with info level"),
    debug: bool = typer.Option(False, "--debug", help="Show logs with debug level"),
    trace: bool = typer.Option(False, "--trace", help="Show logs with trace level"),
) -> None:
    """Global options for microsandbox CLI."""
    setup_logging(error, warn, info, debug, trace)
    if version:
        console.print("[blue bold]v0.2.6[/blue bold]")
        raise typer.Exit()


# -------------------------------------------------------------------------
# Project Management Commands
# -------------------------------------------------------------------------


@app.command()
def init(
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to Sandboxfile or project directory"),
) -> None:
    """Initialize a new microsandbox project."""
    asyncio.run(handle_init(file))


@app.command()
def add(
    names: list[str] = typer.Argument(..., help="Names of sandboxes to add"),
    image: str = typer.Option(..., "--image", "-i", help="Image to use"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s", help="Apply to sandbox"),
    build: bool = typer.Option(False, "--build", "-b", help="Apply to build sandbox"),
    memory: Optional[int] = typer.Option(None, "--memory", help="Memory in MiB"),
    cpus: Optional[int] = typer.Option(None, "--cpus", "--cpu", help="Number of CPUs"),
    volumes: Optional[list[str]] = typer.Option(None, "--volume", "-v", help="Volume mappings"),
    ports: Optional[list[str]] = typer.Option(None, "--port", "-p", help="Port mappings"),
    envs: Optional[list[str]] = typer.Option(None, "--env", help="Environment variables"),
    env_file: Optional[str] = typer.Option(None, "--env-file", help="Environment file"),
    depends_on: Optional[list[str]] = typer.Option(None, "--depends-on", help="Dependencies"),
    workdir: Optional[str] = typer.Option(None, "--workdir", help="Working directory"),
    shell: Optional[str] = typer.Option(None, "--shell", help="Shell to use"),
    scripts: Optional[list[str]] = typer.Option(None, "--script", help="Scripts (name=cmd)"),
    start: Optional[str] = typer.Option(None, "--start", help="Start command"),
    imports: Optional[list[str]] = typer.Option(None, "--import", help="Import files (name=path)"),
    exports: Optional[list[str]] = typer.Option(None, "--export", help="Export files (name=path)"),
    scope: Optional[str] = typer.Option(None, "--scope", help="Network scope"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to Sandboxfile"),
) -> None:
    """Add a new sandbox to the project."""
    asyncio.run(handle_add(
        names=names, image=image, sandbox=sandbox, build=build,
        memory=memory, cpus=cpus, volumes=volumes or [], ports=ports or [],
        envs=envs or [], env_file=env_file, depends_on=depends_on or [],
        workdir=workdir, shell=shell, scripts=scripts or [],
        start=start, imports=imports or [], exports=exports or [],
        scope=scope, file=file,
    ))


@app.command(name="remove")
def remove(
    names: list[str] = typer.Argument(..., help="Names of sandboxes to remove"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    build: bool = typer.Option(False, "--build", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """Remove a sandbox from the project."""
    asyncio.run(handle_remove(names=names, sandbox=sandbox, build=build, file=file))


@app.command(name="list")
def list_cmd(
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    build: bool = typer.Option(False, "--build", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """List sandboxes defined in the project."""
    asyncio.run(handle_list(sandbox=sandbox, build=build, file=file))


# -------------------------------------------------------------------------
# Execution Commands
# -------------------------------------------------------------------------


@app.command()
def run(
    name: str = typer.Argument(..., help="Name of sandbox or sandbox~script"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    build: bool = typer.Option(False, "--build", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
    detach: bool = typer.Option(False, "--detach", "-d", help="Run in background"),
    exec_cmd: Optional[str] = typer.Option(None, "--exec", "-x", help="Execute command"),
    args: Optional[list[str]] = typer.Argument(None, help="Additional arguments"),
) -> None:
    """Run a sandbox defined in the project."""
    asyncio.run(handle_run(
        name=name, sandbox=sandbox, build=build, file=file,
        detach=detach, exec_cmd=exec_cmd, args=args or [],
    ))


@app.command()
def shell(
    name: str = typer.Argument(..., help="Name of sandbox"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    build: bool = typer.Option(False, "--build", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
    detach: bool = typer.Option(False, "--detach", "-d"),
    args: Optional[list[str]] = typer.Argument(None, help="Additional arguments"),
) -> None:
    """Open a shell in a sandbox."""
    asyncio.run(handle_shell(
        name=name, sandbox=sandbox, build=build, file=file,
        detach=detach, args=args or [],
    ))


@app.command()
def exe(
    name: str = typer.Argument(..., help="Image name or image~script"),
    cpus: Optional[int] = typer.Option(None, "--cpus", "--cpu"),
    memory: Optional[int] = typer.Option(None, "--memory"),
    volumes: Optional[list[str]] = typer.Option(None, "--volume", "-v"),
    ports: Optional[list[str]] = typer.Option(None, "--port", "-p"),
    envs: Optional[list[str]] = typer.Option(None, "--env"),
    workdir: Optional[str] = typer.Option(None, "--workdir"),
    scope: Optional[str] = typer.Option(None, "--scope"),
    exec_cmd: Optional[str] = typer.Option(None, "--exec", "-x"),
    args: Optional[list[str]] = typer.Argument(None),
) -> None:
    """Run a temporary sandbox from an image."""
    asyncio.run(handle_exe(
        name=name, cpus=cpus, memory=memory, volumes=volumes or [],
        ports=ports or [], envs=envs or [], workdir=workdir,
        scope=scope, exec_cmd=exec_cmd, args=args or [],
    ))


# -------------------------------------------------------------------------
# Installation Commands
# -------------------------------------------------------------------------


@app.command()
def install(
    name: str = typer.Argument(..., help="Image name or image~script"),
    alias: Optional[str] = typer.Argument(None, help="Alias for the script"),
    cpus: Optional[int] = typer.Option(None, "--cpus", "--cpu"),
    memory: Optional[int] = typer.Option(None, "--memory"),
    volumes: Optional[list[str]] = typer.Option(None, "--volume", "-v"),
    ports: Optional[list[str]] = typer.Option(None, "--port", "-p"),
    envs: Optional[list[str]] = typer.Option(None, "--env"),
    workdir: Optional[str] = typer.Option(None, "--workdir"),
    scope: Optional[str] = typer.Option(None, "--scope"),
    exec_cmd: Optional[str] = typer.Option(None, "--exec", "-x"),
    args: Optional[list[str]] = typer.Argument(None),
) -> None:
    """Install a script from an image."""
    asyncio.run(handle_install(
        name=name, alias=alias, cpus=cpus, memory=memory,
        volumes=volumes or [], ports=ports or [], envs=envs or [],
        workdir=workdir, scope=scope, exec_cmd=exec_cmd, args=args or [],
    ))


@app.command()
def uninstall(
    script: Optional[str] = typer.Argument(None, help="Script to uninstall"),
) -> None:
    """Uninstall a script."""
    asyncio.run(handle_uninstall(script))


# -------------------------------------------------------------------------
# Orchestration Commands
# -------------------------------------------------------------------------


@app.command()
def apply(
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
    detach: bool = typer.Option(False, "--detach", "-d"),
) -> None:
    """Apply full configuration from Sandboxfile."""
    asyncio.run(handle_apply(file=file, detach=detach))


@app.command()
def up(
    names: Optional[list[str]] = typer.Argument(None, help="Sandboxes to start"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    build: bool = typer.Option(False, "--build", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
    detach: bool = typer.Option(False, "--detach", "-d"),
) -> None:
    """Start project sandboxes."""
    asyncio.run(handle_up(
        names=names or [], sandbox=sandbox, build=build, file=file, detach=detach,
    ))


@app.command()
def down(
    names: Optional[list[str]] = typer.Argument(None, help="Sandboxes to stop"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    build: bool = typer.Option(False, "--build", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """Stop project sandboxes."""
    asyncio.run(handle_down(names=names or [], sandbox=sandbox, build=build, file=file))


@app.command()
def status(
    names: Optional[list[str]] = typer.Argument(None, help="Sandboxes to check"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    build: bool = typer.Option(False, "--build", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """Show status of project sandboxes."""
    asyncio.run(handle_status(names=names or [], sandbox=sandbox, build=build, file=file))


# -------------------------------------------------------------------------
# Utility Commands
# -------------------------------------------------------------------------


@app.command()
def log(
    name: str = typer.Argument(..., help="Name of sandbox"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    build: bool = typer.Option(False, "--build", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
    follow: bool = typer.Option(False, "--follow", "-F"),
    tail: Optional[int] = typer.Option(None, "--tail", "-t"),
) -> None:
    """Show logs of a sandbox."""
    asyncio.run(handle_log(
        name=name, sandbox=sandbox, build=build, file=file,
        follow=follow, tail=tail,
    ))


@app.command()
def clean(
    name: Optional[str] = typer.Argument(None, help="Sandbox name to clean"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    user: bool = typer.Option(False, "--user", "-u", help="Clean user caches"),
    all_: bool = typer.Option(False, "--all", "-a", help="Clean all"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
    force: bool = typer.Option(False, "--force", "-F"),
) -> None:
    """Clean cached sandbox layers, metadata, etc."""
    asyncio.run(handle_clean(
        sandbox=sandbox, name=name, user=user, all_=all_, file=file, force=force,
    ))


@app.command()
def pull(
    name: str = typer.Argument(..., help="Image name to pull"),
    layer_path: Optional[Path] = typer.Option(None, "--layer-path", "-L"),
) -> None:
    """Pull image from a registry."""
    asyncio.run(handle_pull(name=name, layer_path=layer_path))


@app.command()
def login() -> None:
    """Login to a registry."""
    asyncio.run(handle_login())


@app.command()
def push(
    name: str = typer.Argument(..., help="Image name"),
    image: bool = typer.Option(False, "--image", "-i"),
) -> None:
    """Push image to a registry."""
    asyncio.run(handle_push(image=image, name=name))


@app.command(name="version")
def version_cmd() -> None:
    """Print version of microsandbox."""
    console.print("[blue bold]v0.2.6[/blue bold]")


# -------------------------------------------------------------------------
# Self Management Commands
# -------------------------------------------------------------------------


@self_app.command(name="uninstall")
def self_uninstall(
    force: bool = typer.Option(False, "--force", "-F"),
) -> None:
    """Uninstall microsandbox."""
    asyncio.run(handle_self_action("uninstall", force=force))


@self_app.command(name="upgrade")
def self_upgrade() -> None:
    """Upgrade microsandbox."""
    asyncio.run(handle_self_action("upgrade"))


# -------------------------------------------------------------------------
# Server Management Commands
# -------------------------------------------------------------------------


@server_app.command(name="start")
def server_start(
    host: Optional[str] = typer.Option(None, "--host"),
    port: Optional[int] = typer.Option(None, "--port"),
    namespace_dir: Optional[Path] = typer.Option(None, "--path", "-p"),
    dev: bool = typer.Option(False, "--dev"),
    key: Optional[str] = typer.Option(None, "--key", "-k"),
    detach: bool = typer.Option(False, "--detach", "-d"),
    reset_key: bool = typer.Option(False, "--reset-key", "-r"),
) -> None:
    """Start the sandbox server."""
    from microsandbox_cli.handlers import handle_server_start
    asyncio.run(handle_server_start(
        host=host, port=port, namespace_dir=namespace_dir,
        dev=dev, key=key, detach=detach, reset_key=reset_key,
    ))


@server_app.command(name="stop")
def server_stop() -> None:
    """Stop the sandbox server."""
    from microsandbox_cli.handlers import handle_server_stop
    asyncio.run(handle_server_stop())


@server_app.command(name="keygen")
def server_keygen(
    expire: Optional[str] = typer.Option(None, "--expire"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n"),
) -> None:
    """Generate a new API key."""
    from microsandbox_cli.handlers import handle_server_keygen
    asyncio.run(handle_server_keygen(expire=expire, namespace=namespace))


@server_app.command(name="log")
def server_log(
    name: str = typer.Argument(..., help="Name of sandbox"),
    namespace: str = typer.Option(..., "--namespace", "-n"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    follow: bool = typer.Option(False, "--follow", "-f"),
    tail: Optional[int] = typer.Option(None, "--tail", "-t"),
) -> None:
    """Show logs of a server sandbox."""
    from microsandbox_cli.handlers import handle_server_log
    asyncio.run(handle_server_log(
        sandbox=sandbox, name=name, namespace=namespace, follow=follow, tail=tail,
    ))


@server_app.command(name="list")
def server_list(
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n"),
) -> None:
    """List sandboxes in a namespace."""
    from microsandbox_cli.handlers import handle_server_list
    asyncio.run(handle_server_list(namespace=namespace))


@server_app.command(name="status")
def server_status(
    names: Optional[list[str]] = typer.Argument(None),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n"),
) -> None:
    """Show server status."""
    from microsandbox_cli.handlers import handle_server_status
    asyncio.run(handle_server_status(sandbox=sandbox, names=names or [], namespace=namespace))


@server_app.command(name="ssh")
def server_ssh(
    name: str = typer.Argument(..., help="Name of sandbox"),
    namespace: str = typer.Option(..., "--namespace", "-n"),
    sandbox: bool = typer.Option(False, "--sandbox", "-s"),
) -> None:
    """SSH into a sandbox."""
    console.print("[red bold]error:[/red bold] SSH functionality is not yet implemented")


if __name__ == "__main__":
    app()
