#!/usr/bin/env python3
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import dataclasses
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager, nullcontext
from functools import cache, partial
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from go_vendor_tools import __version__
from go_vendor_tools.archive import add_files_to_archive
from go_vendor_tools.config.archive import get_go_dependency_update_commands
from go_vendor_tools.config.base import BaseConfig, load_config
from go_vendor_tools.exceptions import ArchiveError
from go_vendor_tools.specfile_sources import get_path_and_output_from_specfile

try:
    import tomlkit
except ImportError:
    HAS_TOMLKIT = False
else:
    HAS_TOMLKIT = True
    from go_vendor_tools.cli.utils import load_tomlkit_if_exists

if TYPE_CHECKING:
    from _typeshed import StrPath

DEFAULT_OUTPUT = "vendor.tar.xz"
ARCHIVE_FILES = (Path("go.mod"), Path("go.sum"), Path("vendor"))
GO_PROXY_ENV = {
    "GOPROXY": "https://proxy.golang.org,direct",
    "GOSUMDB": "sum.golang.org",
}


@cache
def need_tomlkit(action="this action"):
    if not HAS_TOMLKIT:
        message = f"tomlkit is required for {action}. Please install it!"
        sys.exit(message)


def run_command(
    runner: Callable[..., subprocess.CompletedProcess],
    command: Sequence[StrPath],
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    print(f"$ {shlex.join(map(os.fspath, command))}")  # type: ignore[arg-type]
    return runner(command, **kwargs)


@dataclasses.dataclass()
class CreateArchiveArgs:
    path: Path
    output: Path
    use_top_level_dir: bool
    use_module_proxy: bool
    tidy: bool
    config_path: Path
    config: BaseConfig

    CONFIG_OPTS: ClassVar[tuple[str, ...]] = (
        "use_module_proxy",
        "use_top_level_dir",
        "tidy",
    )

    @classmethod
    def construct(cls, **kwargs: Any) -> CreateArchiveArgs:
        if kwargs.pop("subcommand") != "create":
            raise AssertionError  # pragma: no cover
        kwargs["config"] = load_config(kwargs["config_path"])
        for opt in cls.CONFIG_OPTS:
            if kwargs[opt] is None:
                kwargs[opt] = kwargs["config"]["archive"][opt]

        if kwargs["output"] and not kwargs["output"].name.endswith((".tar.xz", "txz")):
            raise ValueError(f"{kwargs['output']} must end with '.tar.xz' or '.txz'")

        if not kwargs["path"].exists():
            raise ArchiveError(f"{kwargs['path']} does not exist!")
        return CreateArchiveArgs(**kwargs)


@dataclasses.dataclass()
class OverrideArgs:
    config_path: Path
    import_path: str
    version: str

    @classmethod
    def construct(cls, **kwargs: Any) -> OverrideArgs:
        if kwargs.pop("subcommand") != "override":
            raise AssertionError  # pragma: no cover
        return cls(**kwargs)


def parseargs(argv: list[str] | None = None) -> CreateArchiveArgs | OverrideArgs:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.required = True
    create_subparser = subparsers.add_parser("create")
    create_subparser.add_argument("--version", action="version", version=__version__)
    create_subparser.add_argument(
        "-O", "--output", type=Path, default=None, help=f"Default: {DEFAULT_OUTPUT}"
    )
    create_subparser.add_argument(
        "--top-level-dir",
        default=None,
        dest="use_top_level_dir",
        action=argparse.BooleanOptionalAction,
    )
    create_subparser.add_argument(
        "--use-module-proxy", action="store_true", default=None
    )
    create_subparser.add_argument("-p", action="store_true", dest="use_module_proxy")
    create_subparser.add_argument("-c", "--config", type=Path, dest="config_path")
    create_subparser.add_argument(
        "--tidy",
        help="%(default)s",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    create_subparser.add_argument("path", type=Path)
    override_subparser = subparsers.add_parser("override")
    override_subparser.add_argument(
        "--config", type=Path, dest="config_path", required=True
    )
    override_subparser.add_argument("import_path")
    override_subparser.add_argument("version")

    args = parser.parse_args(argv)
    if args.subcommand == "create":
        return CreateArchiveArgs.construct(**vars(args))
    elif args.subcommand == "override":
        return OverrideArgs.construct(**vars(args))
    else:
        raise RuntimeError("unreachable")


def _create_archive_read_from_specfile(args: CreateArchiveArgs) -> None:
    if args.output:
        sys.exit("Cannot pass --output when reading paths from a specfile!")
    spec_path = args.path
    args.path, args.output = get_path_and_output_from_specfile(args.path)
    if not args.path.is_file():
        sys.exit(
            f"{args.path} does not exist!"
            f" Run 'spectool -g {spec_path}' and try again!"
        )


def create_archive(args: CreateArchiveArgs) -> None:
    _already_checked_is_file = False
    cwd = args.path
    cm: AbstractContextManager[str] = nullcontext(str(args.path))
    if args.path.suffix == ".spec":
        _create_archive_read_from_specfile(args)
        _already_checked_is_file = True
    else:
        args.output = Path(DEFAULT_OUTPUT)
    # Treat as an archive if it's not a directory
    if _already_checked_is_file or args.path.is_file():
        print(f"* Treating {args.path} as an archive. Unpacking...")
        cm = tempfile.TemporaryDirectory()
        shutil.unpack_archive(args.path, cm.name)
        cwd = Path(cm.name)
        cwd /= next(cwd.iterdir())
    with cm:
        env = os.environ | GO_PROXY_ENV if args.use_module_proxy else None
        runner = partial(subprocess.run, cwd=cwd, check=True, env=env)
        pre_commands = chain(
            args.config["archive"]["pre_commands"],
            get_go_dependency_update_commands(
                args.config["archive"]["dependency_overrides"]
            ),
        )
        for command in pre_commands:
            run_command(runner, command)
        if args.tidy:
            run_command(runner, ["go", "mod", "tidy"])
        run_command(runner, ["go", "mod", "vendor"])
        for command in args.config["archive"]["post_commands"]:
            run_command(runner, command)
        print("Creating archive...")
        with tarfile.open(args.output, "w:xz") as tf:
            add_files_to_archive(
                tf, Path(cwd), ARCHIVE_FILES, top_level_dir=args.use_top_level_dir
            )


def override_command(args: OverrideArgs) -> None:
    need_tomlkit()
    loaded = load_tomlkit_if_exists(args.config_path)
    overrides = loaded.setdefault("archive", {}).setdefault("dependency_overrides", {})
    overrides[args.import_path] = args.version
    with open(args.config_path, "w", encoding="utf-8") as fp:
        tomlkit.dump(loaded, fp)


def main(argv: list[str] | None = None) -> None:
    args = parseargs(argv)
    if isinstance(args, CreateArchiveArgs):
        create_archive(args)
    elif isinstance(args, OverrideArgs):
        override_command(args)


if __name__ == "__main__":
    try:
        main()
    except ArchiveError as exc:
        sys.exit(str(exc))
