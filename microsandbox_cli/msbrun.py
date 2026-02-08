"""msbrun - Polymorphic binary for running MicroVMs and supervisors.

This binary provides a unified interface for running either:
- A MicroVM that provides an isolated execution environment
- A supervisor process that manages and monitors child processes
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main():
    """Main entry point for msbrun."""
    parser = argparse.ArgumentParser(description="Microsandbox Runner")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # MicroVM subcommand
    microvm_parser = subparsers.add_parser("microvm", help="Run as microVM")
    microvm_parser.add_argument("--log-level", type=int, default=None)
    microvm_parser.add_argument("--native-rootfs", type=str, default=None)
    microvm_parser.add_argument("--overlayfs-layer", type=str, action="append", default=[])
    microvm_parser.add_argument("--num-vcpus", type=int, default=None)
    microvm_parser.add_argument("--memory-mib", type=int, default=None)
    microvm_parser.add_argument("--workdir-path", type=str, default=None)
    microvm_parser.add_argument("--exec-path", type=str, required=True)
    microvm_parser.add_argument("--env", type=str, action="append", default=[])
    microvm_parser.add_argument("--mapped-dir", type=str, action="append", default=[])
    microvm_parser.add_argument("--port-map", type=str, action="append", default=[])
    microvm_parser.add_argument("--scope", type=str, default=None)
    microvm_parser.add_argument("--ip", type=str, default=None)
    microvm_parser.add_argument("--subnet", type=str, default=None)
    microvm_parser.add_argument("args", nargs="*")

    # Supervisor subcommand
    supervisor_parser = subparsers.add_parser("supervisor", help="Run as supervisor")
    supervisor_parser.add_argument("--log-dir", type=str, required=True)
    supervisor_parser.add_argument("--sandbox-db-path", type=str, required=True)
    supervisor_parser.add_argument("--sandbox-name", type=str, required=True)
    supervisor_parser.add_argument("--config-file", type=str, required=True)
    supervisor_parser.add_argument("--config-last-modified", type=str, default=None)
    supervisor_parser.add_argument("--log-level", type=int, default=None)
    supervisor_parser.add_argument("--forward-output", type=bool, default=True)
    supervisor_parser.add_argument("--native-rootfs", type=str, default=None)
    supervisor_parser.add_argument("--overlayfs-layer", type=str, action="append", default=[])
    supervisor_parser.add_argument("--num-vcpus", type=int, default=None)
    supervisor_parser.add_argument("--memory-mib", type=int, default=None)
    supervisor_parser.add_argument("--workdir-path", type=str, default=None)
    supervisor_parser.add_argument("--exec-path", type=str, required=True)
    supervisor_parser.add_argument("--env", type=str, action="append", default=[])
    supervisor_parser.add_argument("--mapped-dir", type=str, action="append", default=[])
    supervisor_parser.add_argument("--port-map", type=str, action="append", default=[])
    supervisor_parser.add_argument("--scope", type=str, default=None)
    supervisor_parser.add_argument("--ip", type=str, default=None)
    supervisor_parser.add_argument("--subnet", type=str, default=None)
    supervisor_parser.add_argument("args", nargs="*")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.subcommand == "microvm":
        asyncio.run(run_microvm(args))
    elif args.subcommand == "supervisor":
        asyncio.run(run_supervisor(args))


async def run_microvm(args) -> None:
    """Run as a MicroVM."""
    from microsandbox_core.config.env_pair import EnvPair
    from microsandbox_core.config.path_pair import PathPair
    from microsandbox_core.config.port_pair import PortPair
    from microsandbox_core.vm.builder import MicroVmBuilder
    from microsandbox_core.vm.microvm import LogLevel, Rootfs

    # Determine rootfs
    if args.native_rootfs and not args.overlayfs_layer:
        rootfs = Rootfs.native(args.native_rootfs)
    elif args.overlayfs_layer and not args.native_rootfs:
        rootfs = Rootfs.overlay(
            lower_dirs=args.overlayfs_layer,
            upper_dir="",
            work_dir="",
        )
    elif args.native_rootfs and args.overlayfs_layer:
        logger.error("Cannot specify both native_rootfs and overlayfs_layer")
        sys.exit(1)
    else:
        logger.error("Must specify either native_rootfs or overlayfs_layer")
        sys.exit(1)

    builder = MicroVmBuilder()
    builder.rootfs(rootfs)
    builder.exec_path(args.exec_path)

    if args.num_vcpus:
        builder.num_vcpus(args.num_vcpus)
    if args.memory_mib:
        builder.memory_mib(args.memory_mib)
    if args.log_level is not None:
        builder.log_level(LogLevel(args.log_level))
    if args.workdir_path:
        builder.workdir(args.workdir_path)

    # Parse env vars
    for env_str in args.env:
        pair = EnvPair.parse(env_str)
        builder.env_var(pair.key, pair.value)

    # Parse mapped dirs
    for dir_str in args.mapped_dir:
        pair = PathPair.parse(dir_str)
        builder.virtiofs_mount(pair)

    # Parse port maps
    for port_str in args.port_map:
        pair = PortPair.parse(port_str)
        builder.port_mapping(pair)

    if args.args:
        builder.args(args.args)

    vm = builder.build()
    logger.info("Starting microVM")
    vm.start()


async def run_supervisor(args) -> None:
    """Run as a supervisor."""
    from microsandbox_utils.runtime.supervisor import Supervisor

    child_exe = sys.executable
    child_args = ["msbrun", "microvm", f"--exec-path={args.exec_path}"]

    if args.num_vcpus:
        child_args.append(f"--num-vcpus={args.num_vcpus}")
    if args.memory_mib:
        child_args.append(f"--memory-mib={args.memory_mib}")
    if args.workdir_path:
        child_args.append(f"--workdir-path={args.workdir_path}")
    if args.native_rootfs:
        child_args.append(f"--native-rootfs={args.native_rootfs}")
    for layer in args.overlayfs_layer:
        child_args.append(f"--overlayfs-layer={layer}")
    for env in args.env:
        child_args.append(f"--env={env}")
    for dir_map in args.mapped_dir:
        child_args.append(f"--mapped-dir={dir_map}")
    for port in args.port_map:
        child_args.append(f"--port-map={port}")
    if args.scope:
        child_args.append(f"--scope={args.scope}")
    if args.ip:
        child_args.append(f"--ip={args.ip}")
    if args.subnet:
        child_args.append(f"--subnet={args.subnet}")
    if args.log_level is not None:
        child_args.append(f"--log-level={args.log_level}")
    if args.args:
        child_args.append("--")
        child_args.extend(args.args)

    child_envs = {}
    rust_log = os.environ.get("RUST_LOG")
    if rust_log:
        child_envs["RUST_LOG"] = rust_log

    supervisor = Supervisor(
        child_exe=child_exe,
        child_args=child_args,
        child_envs=child_envs,
        log_dir=args.log_dir,
    )

    await supervisor.start()


if __name__ == "__main__":
    main()
