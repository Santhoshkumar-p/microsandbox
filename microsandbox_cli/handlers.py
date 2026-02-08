"""Command handlers for the microsandbox CLI.

Each handler corresponds to a CLI subcommand and orchestrates the
actual business logic by calling into the core and server packages.
"""

import asyncio
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from microsandbox_cli.error import (
    ConfigError,
    InvalidArgumentError,
    MicrosandboxCliError,
    NamespaceError,
    NotFoundError,
)
from microsandbox_utils.term import print_error, print_success

logger = logging.getLogger(__name__)
console = Console()

# Separator for sandbox name and script
SANDBOX_SCRIPT_SEPARATOR = "~"


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------


def parse_name_and_script(name: str) -> tuple[str, Optional[str]]:
    """Parse a name~script string into (name, script)."""
    if SANDBOX_SCRIPT_SEPARATOR in name:
        parts = name.split(SANDBOX_SCRIPT_SEPARATOR, 1)
        return parts[0], parts[1]
    return name, None


def parse_file_path(file: Optional[Path]) -> tuple[Optional[Path], Optional[str]]:
    """Parse a file path into project path and config file name."""
    if file is None:
        return None, None

    if file.is_dir():
        return file, None

    config_name = file.name
    parent = file.parent
    if not str(parent) or str(parent) == ".":
        return Path("."), config_name
    return parent, config_name


def parse_key_val(s: str) -> tuple[str, str]:
    """Parse a key=value string."""
    if "=" not in s:
        raise InvalidArgumentError(f"invalid KEY=value: no '=' found in '{s}'")
    key, value = s.split("=", 1)
    return key, value


def parse_duration_string(duration_str: str) -> int:
    """Parse a duration string like '1s', '2m', '3h', '4d', '5w' into seconds."""
    duration_str = duration_str.strip()
    if not duration_str:
        raise InvalidArgumentError("Empty duration string")

    match = re.match(r"^(\d+)(s|m|h|d|w|mo|y)?$", duration_str)
    if not match:
        raise InvalidArgumentError(f"Invalid duration format: {duration_str}")

    value = int(match.group(1))
    unit = match.group(2) or "h"

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
        "mo": 2592000,  # 30 days
        "y": 31536000,  # 365 days
    }

    return value * multipliers[unit]


# -------------------------------------------------------------------------
# Project Management Handlers
# -------------------------------------------------------------------------


async def handle_init(file: Optional[Path]) -> None:
    """Handle the init subcommand."""
    from microsandbox_core.management.config import ConfigManager
    from microsandbox_core.management.menv import MenvManager

    project_dir, _ = parse_file_path(file)
    project_dir = project_dir or Path.cwd()

    ConfigManager.init(project_dir=project_dir)
    await MenvManager.init(project_dir)
    print_success("Initialized new microsandbox project")


async def handle_add(
    names: list[str],
    image: str,
    sandbox: bool = False,
    build: bool = False,
    memory: Optional[int] = None,
    cpus: Optional[int] = None,
    volumes: list[str] | None = None,
    ports: list[str] | None = None,
    envs: list[str] | None = None,
    env_file: Optional[str] = None,
    depends_on: list[str] | None = None,
    workdir: Optional[str] = None,
    shell: Optional[str] = None,
    scripts: list[str] | None = None,
    start: Optional[str] = None,
    imports: list[str] | None = None,
    exports: list[str] | None = None,
    scope: Optional[str] = None,
    file: Optional[Path] = None,
) -> None:
    """Handle the add subcommand."""
    from microsandbox_core.management.config import ConfigManager

    if build and sandbox:
        print_error("Cannot specify both --build and --sandbox flags")
        return

    project_dir, config_name = parse_file_path(file)

    # Parse scripts
    parsed_scripts: dict[str, str] = {}
    for s in (scripts or []):
        k, v = parse_key_val(s)
        parsed_scripts[k] = v
    if start:
        parsed_scripts["start"] = start

    for name in names:
        ConfigManager.add_sandbox(
            name=name,
            image=image,
            project_dir=project_dir,
            memory=memory,
            cpus=cpus,
            volumes=volumes,
            ports=ports,
            envs=envs,
            depends_on=depends_on,
            workdir=workdir,
            shell=shell,
            scripts=parsed_scripts if parsed_scripts else None,
            scope=scope,
        )

    print_success(f"Added {len(names)} sandbox(es) to configuration")


async def handle_remove(
    names: list[str],
    sandbox: bool = False,
    build: bool = False,
    file: Optional[Path] = None,
) -> None:
    """Handle the remove subcommand."""
    from microsandbox_core.management.config import ConfigManager

    project_dir, _ = parse_file_path(file)

    for name in names:
        ConfigManager.remove_sandbox(name=name, project_dir=project_dir)

    print_success(f"Removed {len(names)} sandbox(es) from configuration")


async def handle_list(
    sandbox: bool = False,
    build: bool = False,
    file: Optional[Path] = None,
) -> None:
    """Handle the list subcommand."""
    from microsandbox_core.management.config import ConfigManager

    project_dir, _ = parse_file_path(file)

    try:
        msb = ConfigManager.load(project_dir=project_dir)
    except Exception as e:
        print_error(str(e))
        return

    sandboxes = msb.config.sandboxes

    if not sandboxes:
        console.print("No sandboxes defined")
        return

    table = Table(title="Sandboxes")
    table.add_column("Name", style="cyan")
    table.add_column("Image", style="green")
    table.add_column("Memory", style="yellow")
    table.add_column("CPUs", style="yellow")
    table.add_column("Ports", style="blue")

    for name, config in sandboxes.items():
        table.add_row(
            name,
            config.image or "N/A",
            str(config.memory or "default"),
            str(config.cpus or "default"),
            ", ".join(config.ports) if config.ports else "none",
        )

    console.print(table)


# -------------------------------------------------------------------------
# Execution Handlers
# -------------------------------------------------------------------------


async def handle_run(
    name: str,
    sandbox: bool = False,
    build: bool = False,
    file: Optional[Path] = None,
    detach: bool = False,
    exec_cmd: Optional[str] = None,
    args: list[str] | None = None,
) -> None:
    """Handle the run subcommand."""
    from microsandbox_core.management.config import ConfigManager
    from microsandbox_core.management.sandbox import SandboxManager

    sandbox_name, script = parse_name_and_script(name)

    if script and exec_cmd:
        print_error("Cannot specify both a script and --exec option")
        return

    project_dir, _ = parse_file_path(file)
    project_dir = project_dir or Path.cwd()

    msb = ConfigManager.load(project_dir=project_dir)
    config = msb.get_sandbox(sandbox_name)
    if not config:
        print_error(f"Sandbox '{sandbox_name}' not found in configuration")
        return

    await SandboxManager.run(
        name=sandbox_name,
        config=config,
        project_dir=project_dir,
        detach=detach,
        script=script,
    )


async def handle_shell(
    name: str,
    sandbox: bool = False,
    build: bool = False,
    file: Optional[Path] = None,
    detach: bool = False,
    args: list[str] | None = None,
) -> None:
    """Handle the shell subcommand."""
    from microsandbox_core.management.config import ConfigManager
    from microsandbox_core.management.sandbox import SandboxManager

    project_dir, _ = parse_file_path(file)
    project_dir = project_dir or Path.cwd()

    msb = ConfigManager.load(project_dir=project_dir)
    config = msb.get_sandbox(name)
    if not config:
        print_error(f"Sandbox '{name}' not found in configuration")
        return

    await SandboxManager.run(
        name=name,
        config=config,
        project_dir=project_dir,
        detach=detach,
        interactive=True,
    )


async def handle_exe(
    name: str,
    cpus: Optional[int] = None,
    memory: Optional[int] = None,
    volumes: list[str] | None = None,
    ports: list[str] | None = None,
    envs: list[str] | None = None,
    workdir: Optional[str] = None,
    scope: Optional[str] = None,
    exec_cmd: Optional[str] = None,
    args: list[str] | None = None,
) -> None:
    """Handle the exe subcommand."""
    from microsandbox_core.config.microsandbox_config import SandboxConfig
    from microsandbox_core.management.sandbox import SandboxManager

    image_name, script = parse_name_and_script(name)

    if script and exec_cmd:
        print_error("Cannot specify both a script and --exec option")
        return

    config = SandboxConfig(
        image=image_name,
        memory=memory,
        cpus=cpus,
        volumes=volumes or [],
        ports=ports or [],
        envs=envs or [],
        workdir=workdir,
        scope=scope,
    )

    await SandboxManager.run(
        name=f"temp-{image_name.replace('/', '-').replace(':', '-')}",
        config=config,
        script=script,
        interactive=not script and not exec_cmd,
    )


# -------------------------------------------------------------------------
# Installation Handlers
# -------------------------------------------------------------------------


async def handle_install(
    name: str,
    alias: Optional[str] = None,
    cpus: Optional[int] = None,
    memory: Optional[int] = None,
    volumes: list[str] | None = None,
    ports: list[str] | None = None,
    envs: list[str] | None = None,
    workdir: Optional[str] = None,
    scope: Optional[str] = None,
    exec_cmd: Optional[str] = None,
    args: list[str] | None = None,
) -> None:
    """Handle the install subcommand."""
    from microsandbox_core.management.home import HomeManager
    from microsandbox_core.oci.reference import Reference

    image_name, script = parse_name_and_script(name)

    if script and exec_cmd:
        print_error("Cannot specify both a script and --exec option")
        return

    ref = Reference.parse(image_name)
    install_alias = alias or ref.image_name

    # Build the msb exe command
    cmd_parts = [sys.executable, "-m", "microsandbox_cli.main", "exe", name]
    if cpus:
        cmd_parts.extend(["--cpus", str(cpus)])
    if memory:
        cmd_parts.extend(["--memory", str(memory)])
    for v in (volumes or []):
        cmd_parts.extend(["--volume", v])
    for p in (ports or []):
        cmd_parts.extend(["--port", p])
    for e in (envs or []):
        cmd_parts.extend(["--env", e])
    if workdir:
        cmd_parts.extend(["--workdir", workdir])
    if scope:
        cmd_parts.extend(["--scope", scope])
    if exec_cmd:
        cmd_parts.extend(["--exec", exec_cmd])

    script_content = f"#!/bin/sh\n{' '.join(cmd_parts)} \"$@\"\n"

    HomeManager.install_sandbox(install_alias, script_content)
    print_success(f"Installed '{install_alias}'")


async def handle_uninstall(script: Optional[str]) -> None:
    """Handle the uninstall subcommand."""
    if not script:
        print_error("Please specify the name of the script to uninstall")
        return

    from microsandbox_core.management.home import HomeManager

    HomeManager.uninstall_sandbox(script)
    print_success(f"Uninstalled '{script}'")


# -------------------------------------------------------------------------
# Orchestration Handlers
# -------------------------------------------------------------------------


async def handle_apply(
    file: Optional[Path] = None,
    detach: bool = False,
) -> None:
    """Handle the apply subcommand."""
    from microsandbox_core.management.orchestra import OrchestraManager

    project_dir, _ = parse_file_path(file)
    config_path = file if file and file.is_file() else None

    await OrchestraManager.apply(
        config_path=config_path,
        project_dir=project_dir,
        detach=detach,
    )
    print_success("Applied configuration")


async def handle_up(
    names: list[str] | None = None,
    sandbox: bool = False,
    build: bool = False,
    file: Optional[Path] = None,
    detach: bool = True,
) -> None:
    """Handle the up subcommand."""
    from microsandbox_core.management.orchestra import OrchestraManager

    project_dir, _ = parse_file_path(file)
    config_path = file if file and file.is_file() else None

    await OrchestraManager.up(
        sandbox_names=names or None,
        config_path=config_path,
        project_dir=project_dir,
        detach=detach,
    )
    print_success("Started sandbox(es)")


async def handle_down(
    names: list[str] | None = None,
    sandbox: bool = False,
    build: bool = False,
    file: Optional[Path] = None,
) -> None:
    """Handle the down subcommand."""
    from microsandbox_core.management.orchestra import OrchestraManager

    project_dir, _ = parse_file_path(file)
    config_path = file if file and file.is_file() else None

    await OrchestraManager.down(
        sandbox_names=names or None,
        config_path=config_path,
        project_dir=project_dir,
    )
    print_success("Stopped sandbox(es)")


async def handle_status(
    names: list[str] | None = None,
    sandbox: bool = False,
    build: bool = False,
    file: Optional[Path] = None,
) -> None:
    """Handle the status subcommand."""
    from microsandbox_core.management.orchestra import OrchestraManager

    project_dir, _ = parse_file_path(file)
    config_path = file if file and file.is_file() else None

    statuses = await OrchestraManager.status(
        sandbox_names=names or None,
        config_path=config_path,
        project_dir=project_dir,
    )

    if not statuses:
        console.print("No sandboxes found")
        return

    table = Table(title="Sandbox Status")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("PID", style="yellow")
    table.add_column("Portal Port", style="blue")

    for s in statuses:
        table.add_row(
            s.get("name", "N/A"),
            s.get("status", "unknown"),
            str(s.get("pid", "N/A")),
            str(s.get("portal_port", "N/A")),
        )

    console.print(table)


# -------------------------------------------------------------------------
# Utility Handlers
# -------------------------------------------------------------------------


async def handle_log(
    name: str,
    sandbox: bool = False,
    build: bool = False,
    file: Optional[Path] = None,
    follow: bool = False,
    tail: Optional[int] = None,
) -> None:
    """Handle the log subcommand."""
    from microsandbox_utils.path import LOG_SUBDIR, MICROSANDBOX_ENV_DIR

    project_dir, _ = parse_file_path(file)
    project_dir = project_dir or Path.cwd()

    log_dir = project_dir / MICROSANDBOX_ENV_DIR / LOG_SUBDIR / name
    log_file = log_dir / "sandbox.log"

    if not log_file.exists():
        print_error(f"No log file found for sandbox '{name}'")
        return

    if follow:
        # Use tail -f for following
        try:
            process = subprocess.Popen(
                ["tail", "-f"] + (["-n", str(tail)] if tail else []) + [str(log_file)],
            )
            process.wait()
        except KeyboardInterrupt:
            pass
    elif tail:
        lines = log_file.read_text().splitlines()
        for line in lines[-tail:]:
            console.print(line)
    else:
        console.print(log_file.read_text())


async def handle_clean(
    sandbox: bool = False,
    name: Optional[str] = None,
    user: bool = False,
    all_: bool = False,
    file: Optional[Path] = None,
    force: bool = False,
) -> None:
    """Handle the clean subcommand."""
    from microsandbox_core.management.home import HomeManager
    from microsandbox_core.management.menv import MenvManager
    from microsandbox_core.management.toolchain import ToolchainManager

    if user or all_:
        HomeManager.clean(clean_all=all_, clean_user=user, force=force)
        if force:
            ToolchainManager.uninstall(force=True)
        print_success("Cleaned user data")

    if not user or all_:
        project_dir, _ = parse_file_path(file)
        project_dir = project_dir or Path.cwd()
        await MenvManager.clean(project_dir, sandbox_name=name, force=force)
        print_success("Cleaned project data")


async def handle_pull(
    name: str,
    layer_path: Optional[Path] = None,
) -> None:
    """Handle the pull subcommand."""
    from microsandbox_core.management.image import ImageManager

    console.print(f"Pulling image: {name}")
    result = await ImageManager.pull_image(name, layer_path=layer_path)
    layers = result.get("layers", [])
    print_success(f"Pulled {len(layers)} layer(s) for {name}")


async def handle_login() -> None:
    """Handle the login subcommand."""
    print_error("Login functionality is not yet implemented")


async def handle_push(image: bool, name: str) -> None:
    """Handle the push subcommand."""
    print_error("Push functionality is not yet implemented")


async def handle_self_action(action: str, force: bool = False) -> None:
    """Handle self subcommand actions."""
    if action == "upgrade":
        print_error("Upgrade functionality is not yet implemented")
    elif action == "uninstall":
        from microsandbox_core.management.home import HomeManager
        from microsandbox_core.management.toolchain import ToolchainManager

        HomeManager.clean(clean_all=True, force=True)
        ToolchainManager.uninstall(force=True)
        print_success("Microsandbox uninstalled")


# -------------------------------------------------------------------------
# Server Handlers
# -------------------------------------------------------------------------


async def handle_server_start(
    host: Optional[str] = None,
    port: Optional[int] = None,
    namespace_dir: Optional[Path] = None,
    dev: bool = False,
    key: Optional[str] = None,
    detach: bool = False,
    reset_key: bool = False,
) -> None:
    """Handle server start subcommand."""
    from microsandbox_server.__main__ import main as server_main
    from microsandbox_server.config import Config
    from microsandbox_server.management import (
        generate_random_key,
        is_server_running,
        load_server_key,
        save_pid_file,
        save_server_key,
    )
    from microsandbox_utils.defaults import DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT

    if is_server_running():
        print_error("Server is already running")
        return

    host = host or DEFAULT_SERVER_HOST
    port = port or DEFAULT_SERVER_PORT

    # Handle key management
    if not key and not dev:
        key = load_server_key()
        if not key or reset_key:
            key = generate_random_key()
            save_server_key(key)
            console.print(f"[green]Generated new server key[/green]")

    if detach:
        # Run in background
        import sys
        cmd = [sys.executable, "-m", "microsandbox_server",
               "--host", host, "--port", str(port)]
        if key:
            cmd.extend(["--key", key])
        if dev:
            cmd.append("--dev")
        if namespace_dir:
            cmd.extend(["--namespace-dir", str(namespace_dir)])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
        save_pid_file(process.pid)
        if dev:
            console.print(f"[green]\u2713[/green] Running in [yellow]development[/yellow] mode")
        console.print(f"[green]\u2713[/green] Server started on [yellow]{host}:{port}[/yellow] (PID: {process.pid})")
    else:
        # Run in foreground
        import uvicorn
        from microsandbox_server.config import Config
        from microsandbox_server.route import create_app

        config = Config(key=key, host=host, port=port, namespace_dir=namespace_dir, dev_mode=dev)
        app = create_app(config)

        save_pid_file(os.getpid())
        if dev:
            console.print(f"[green]\u2713[/green] Running in [yellow]development[/yellow] mode")
        console.print(f"[green]\u2713[/green] Server listening on [yellow]{host}:{port}[/yellow]")

        uvicorn_config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
        server = uvicorn.Server(uvicorn_config)
        await server.serve()


async def handle_server_stop() -> None:
    """Handle server stop subcommand."""
    from microsandbox_server.management import stop_server

    if stop_server():
        print_success("Server stopped")
    else:
        print_error("Server is not running")


async def handle_server_keygen(
    expire: Optional[str] = None,
    namespace: Optional[str] = None,
) -> None:
    """Handle server keygen subcommand."""
    from microsandbox_server.management import generate_api_key, load_server_key

    key = load_server_key()
    if not key:
        print_error("No server key found. Start the server first.")
        return

    expire_days = 30
    if expire:
        expire_seconds = parse_duration_string(expire)
        expire_days = max(1, expire_seconds // 86400)

    ns = namespace or "*"
    token = generate_api_key(key, namespace=ns, expire_days=expire_days)
    console.print(f"[green]Generated API key for namespace '{ns}':[/green]")
    console.print(f"[yellow]{token}[/yellow]")


async def handle_server_log(
    sandbox: bool,
    name: str,
    namespace: str,
    follow: bool,
    tail: Optional[int],
) -> None:
    """Handle server log subcommand."""
    from microsandbox_utils.env import get_microsandbox_home_path
    from microsandbox_utils.path import LOG_SUBDIR, NAMESPACES_SUBDIR

    ns_path = get_microsandbox_home_path() / NAMESPACES_SUBDIR / namespace
    if not ns_path.exists():
        print_error(f"Namespace '{namespace}' not found")
        return

    log_file = ns_path / name / LOG_SUBDIR / "sandbox.log"
    if not log_file.exists():
        print_error(f"No log file found for sandbox '{name}' in namespace '{namespace}'")
        return

    if follow:
        try:
            process = subprocess.Popen(
                ["tail", "-f"] + (["-n", str(tail)] if tail else []) + [str(log_file)],
            )
            process.wait()
        except KeyboardInterrupt:
            pass
    elif tail:
        lines = log_file.read_text().splitlines()
        for line in lines[-tail:]:
            console.print(line)
    else:
        console.print(log_file.read_text())


async def handle_server_list(namespace: Optional[str] = None) -> None:
    """Handle server list subcommand."""
    from microsandbox_utils.env import get_microsandbox_home_path
    from microsandbox_utils.path import NAMESPACES_SUBDIR

    ns_dir = get_microsandbox_home_path() / NAMESPACES_SUBDIR

    if not ns_dir.exists():
        console.print("No namespaces found")
        return

    if namespace:
        ns_path = ns_dir / namespace
        if not ns_path.exists():
            print_error(f"Namespace '{namespace}' not found")
            return
        # List sandboxes in namespace
        sandboxes = [d.name for d in ns_path.iterdir() if d.is_dir()]
        if sandboxes:
            table = Table(title=f"Sandboxes in namespace '{namespace}'")
            table.add_column("Name", style="cyan")
            for s in sorted(sandboxes):
                table.add_row(s)
            console.print(table)
        else:
            console.print(f"No sandboxes in namespace '{namespace}'")
    else:
        # List all namespaces
        namespaces = [d.name for d in ns_dir.iterdir() if d.is_dir()]
        if namespaces:
            table = Table(title="Namespaces")
            table.add_column("Namespace", style="cyan")
            for ns in sorted(namespaces):
                table.add_row(ns)
            console.print(table)
        else:
            console.print("No namespaces found")


async def handle_server_status(
    sandbox: bool,
    names: list[str],
    namespace: Optional[str] = None,
) -> None:
    """Handle server status subcommand."""
    from microsandbox_server.management import is_server_running, load_pid_file

    if is_server_running():
        pid = load_pid_file()
        console.print(f"[green]\u2713[/green] Server is running (PID: {pid})")
    else:
        console.print("[yellow]Server is not running[/yellow]")
