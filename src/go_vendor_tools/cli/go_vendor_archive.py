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
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from go_vendor_tools.archive import add_files_to_archive
from go_vendor_tools.config.base import BaseConfig, load_config
from go_vendor_tools.exceptions import ArchiveError

if TYPE_CHECKING:
    from _typeshed import StrPath

ARCHIVE_FILES = (Path("go.mod"), Path("go.sum"), Path("vendor"))
GO_PROXY_ENV = {
    "GOPROXY": "https://proxy.golang.org,direct",
    "GOSUMDB": "sum.golang.org",
}


def run_command(
    runner: Callable[..., subprocess.CompletedProcess],
    command: Sequence[StrPath],
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    print(f"$ {shlex.join(map(os.fspath, command))}")  # type: ignore[arg-type]
    return runner(command, **kwargs)


@dataclasses.dataclass()
class ArchiveArgs:
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
    def construct(cls, **kwargs: Any) -> ArchiveArgs:
        kwargs["config"] = load_config(kwargs["config_path"])
        for opt in cls.CONFIG_OPTS:
            if kwargs[opt] is None:
                kwargs[opt] = kwargs["config"]["archive"][opt]

        if not kwargs["output"].name.endswith((".tar.xz", "txz")):
            raise ValueError(f"{kwargs['output']} must end with '.tar.xz' or '.txz'")

        if not kwargs["path"].exists():
            raise ArchiveError(f"{kwargs['path']} does not exist!")
        return ArchiveArgs(**kwargs)


def parseargs(argv: list[str] | None = None) -> ArchiveArgs:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-O", "--output", type=Path, default="vendor.tar.gz", help="%(default)s"
    )
    parser.add_argument(
        "--top-level-dir",
        default=None,
        dest="use_top_level_dir",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument("--use-module-proxy", action="store_true", default=None)
    parser.add_argument("-p", action="store_true", dest="use_module_proxy")
    parser.add_argument("-c", "--config", type=Path, dest="config_path")
    parser.add_argument(
        "--tidy",
        help="%(default)s",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    return ArchiveArgs.construct(**vars(args))


def main(argv: list[str] | None = None) -> None:
    args = parseargs(argv)

    cwd = args.path
    cm: AbstractContextManager[str] = nullcontext(str(args.path))
    # Treat as an archive if it's not a directory
    if args.path.is_file():
        print(f"* Treating {args.path} as an archive. Unpacking...")
        cm = tempfile.TemporaryDirectory()
        shutil.unpack_archive(args.path, cm.name)
        cwd = Path(cm.name)
        cwd /= next(cwd.iterdir())
    with cm:
        env = os.environ | GO_PROXY_ENV if args.use_module_proxy else None
        runner = partial(subprocess.run, cwd=cwd, check=True, env=env)
        for command in args.config["archive"]["pre_commands"]:
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


if __name__ == "__main__":
    try:
        main()
    except ArchiveError as exc:
        sys.exit(str(exc))
