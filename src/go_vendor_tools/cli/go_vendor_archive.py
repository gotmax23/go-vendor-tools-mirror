#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import dataclasses
import os
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from contextlib import ExitStack
from functools import partial
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from go_vendor_tools import __version__
from go_vendor_tools._zstarfile_extra import open_write_compressed
from go_vendor_tools.archive import OurTarFile, add_files_to_archive
from go_vendor_tools.cli.utils import catch_vendor_tools_error
from go_vendor_tools.config.archive import (
    get_go_dependency_update_commands,
)
from go_vendor_tools.config.base import BaseConfig, load_config
from go_vendor_tools.exceptions import ArchiveError
from go_vendor_tools.specfile import VendorSpecfile

try:
    import tomlkit
except ImportError:
    HAS_TOMLKIT = False
else:
    HAS_TOMLKIT = True
    from go_vendor_tools.cli.utils import load_tomlkit_if_exists

try:
    import argcomplete
except ImportError:
    HAS_ARGCOMPLETE = False
else:
    HAS_ARGCOMPLETE = True

if TYPE_CHECKING:
    from _typeshed import StrPath

DEFAULT_OUTPUT = "vendor.tar.bz2"
ARCHIVE_FILES = (Path("go.mod"), Path("go.sum"), Path("vendor/"))
GO_WORK_ARCHIVE_FILES = (Path("go.work"), Path("go.work.sum"), *ARCHIVE_FILES)
OPTIONAL_FILES = frozenset({Path("go.sum")})
GO_WORK_OPTIONAL_FILES = frozenset(
    {Path("go.work.sum"), Path("go.mod"), *OPTIONAL_FILES}
)
GO_PROXY_ENV = {
    "GOPROXY": "https://proxy.golang.org,direct",
    "GOSUMDB": "sum.golang.org",
}


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
    # START: Config options
    use_top_level_dir: bool
    use_module_proxy: bool
    tidy: bool
    idempotent: bool
    compresslevel: int | None
    compression_type: str | None
    # END: Config options
    config_path: Path
    config: BaseConfig
    write_config: bool
    _explicitly_passed: list[str] = dataclasses.field(default_factory=list, repr=False)

    CONFIG_OPTS: ClassVar[tuple[str, ...]] = (
        "use_module_proxy",
        "use_top_level_dir",
        "tidy",
        "compresslevel",
        "compression_type",
    )

    @classmethod
    def construct(cls, **kwargs: Any) -> CreateArchiveArgs:
        if kwargs.pop("subcommand") != "create":
            raise AssertionError  # pragma: no cover
        _explicitly_passed = list(kwargs)
        kwargs["config"] = load_config(kwargs["config_path"], kwargs["write_config"])
        for opt in cls.CONFIG_OPTS:
            if kwargs.get(opt) is None:
                kwargs[opt] = kwargs["config"]["archive"][opt]
        if not kwargs["path"].exists():
            raise ArchiveError(f"{kwargs['path']} does not exist!")
        if kwargs["write_config"]:
            need_tomlkit("--write-config")
            if not kwargs["config_path"]:
                raise ArchiveError("--write-config requires --config to be set")
        if kwargs["config"]["general"]["go_mod_dir"] and kwargs["use_top_level_dir"]:
            raise ArchiveError(
                "archive->use_top_level_dir and general->go_mod_dir"
                " config options are incompatible"
            )
        return CreateArchiveArgs(**kwargs, _explicitly_passed=_explicitly_passed)

    def write_config_opts(self) -> None:
        need_tomlkit("write_config_opts")
        loaded = load_tomlkit_if_exists(self.config_path)
        config = loaded.setdefault("archive", {})
        for opt in self._explicitly_passed:
            if opt not in self.CONFIG_OPTS:
                continue
            config[opt] = getattr(self, opt)
        with open(self.config_path, "w", encoding="utf-8") as fp:
            tomlkit.dump(loaded, fp)


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
        dest="use_top_level_dir",
        action=argparse.BooleanOptionalAction,
        default=argparse.SUPPRESS,
    )
    create_subparser.add_argument(
        "--use-module-proxy",
        action=argparse.BooleanOptionalAction,
        default=argparse.SUPPRESS,
    )
    create_subparser.add_argument(
        "-p", action="store_true", dest="use_module_proxy", default=argparse.SUPPRESS
    )
    create_subparser.add_argument("-c", "--config", type=Path, dest="config_path")
    create_subparser.add_argument(
        "--tidy",
        action=argparse.BooleanOptionalAction,
        default=argparse.SUPPRESS,
    )
    create_subparser.add_argument(
        "-I",
        "--idempotent",
        action="store_true",
        help="Only generate archive if OUTPUT does not already exist",
    )
    create_subparser.add_argument(
        "--compresslevel", type=int, default=argparse.SUPPRESS
    )
    create_subparser.add_argument(
        "--compression",
        dest="compression_type",
        metavar="COMPRESSION_TYPE",
        help=f"Choices: {list(OurTarFile.OPEN_METH)}",
        default=argparse.SUPPRESS,
    )
    create_subparser.add_argument("--write-config", action="store_true")
    create_subparser.add_argument("path", type=Path)
    override_subparser = subparsers.add_parser("override")
    override_subparser.add_argument(
        "--config", type=Path, dest="config_path", required=True
    )
    override_subparser.add_argument("import_path")
    override_subparser.add_argument("version")

    if HAS_ARGCOMPLETE:
        argcomplete.autocomplete(parser)
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
    args.path, args.output = VendorSpecfile(args.path).source0_and_source1()
    if not args.path.is_file():
        sys.exit(
            f"{args.path} does not exist!"
            f" Run 'spectool -g {spec_path}' and try again!"
        )


def paths_with_go_mod_dir(paths: Iterable[Path], go_mod_dir: str | None) -> list[Path]:
    if not go_mod_dir:
        return list(paths)
    return [go_mod_dir / path for path in paths]


def create_archive(args: CreateArchiveArgs) -> None:
    go_mod_dir = args.config["general"]["go_mod_dir"]
    _already_checked_is_file = False
    cwd = args.path
    if args.path.suffix == ".spec":
        _create_archive_read_from_specfile(args)
        _already_checked_is_file = True
    elif not args.output:
        args.output = Path(DEFAULT_OUTPUT)
    if args.idempotent and args.output.exists():
        print(f"{args.output} already exists")
        sys.exit()
    with ExitStack() as stack:
        # Treat as an archive if it's not a directory
        if _already_checked_is_file or args.path.is_file():
            print(f"* Treating {args.path} as an archive. Unpacking...")
            cwd = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            with OurTarFile.open(args.path) as wtf:
                wtf.extractall(cwd)
            cwd /= next(cwd.iterdir())
        root_cwd = cwd
        # TODO: test go_mod_dir support
        if go_mod_dir:
            cwd /= go_mod_dir
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
        use_go_work = (cwd / "go.work").is_file()
        if use_go_work:
            run_command(runner, ["go", "work", "vendor"])
        else:
            if args.tidy:
                run_command(runner, ["go", "mod", "tidy"])
            run_command(runner, ["go", "mod", "vendor"])
        # Create vendor directory so it is there even if there are no
        # dependencies to download
        (vdir := cwd / "vendor").mkdir(exist_ok=True)
        (vdir / "modules.txt").touch(exist_ok=True)
        for command in args.config["archive"]["post_commands"]:
            run_command(runner, command)
        try:
            tf = stack.enter_context(
                open_write_compressed(
                    args.output,
                    compression_type=args.compression_type,
                    compresslevel=args.compresslevel,
                )
            )
        except ValueError as exc:
            sys.exit(f"Invalid --output value: {exc}")
        print("Creating archive...")
        add_files_to_archive(
            tf,
            root_cwd,
            paths_with_go_mod_dir(
                ARCHIVE_FILES if not use_go_work else GO_WORK_ARCHIVE_FILES, go_mod_dir
            ),
            top_level_dir=args.use_top_level_dir,
            optional_files=paths_with_go_mod_dir(
                OPTIONAL_FILES if not use_go_work else GO_WORK_OPTIONAL_FILES,
                go_mod_dir,
            ),
        )
        if args.write_config:
            args.write_config_opts()


def override_command(args: OverrideArgs) -> None:
    need_tomlkit()
    loaded = load_tomlkit_if_exists(args.config_path)
    overrides = loaded.setdefault("archive", {}).setdefault("dependency_overrides", {})
    overrides[args.import_path] = args.version
    with open(args.config_path, "w", encoding="utf-8") as fp:
        tomlkit.dump(loaded, fp)


def main(argv: list[str] | None = None) -> None:
    args = parseargs(argv)
    with catch_vendor_tools_error():
        if isinstance(args, CreateArchiveArgs):
            create_archive(args)
        elif isinstance(args, OverrideArgs):
            override_command(args)


if __name__ == "__main__":
    try:
        main()
    except ArchiveError as exc:
        sys.exit(str(exc))
