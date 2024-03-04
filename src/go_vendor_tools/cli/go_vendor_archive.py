#!/usr/bin/env python3
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager, nullcontext
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import requests

from go_vendor_tools.archive import add_files_to_archive
from go_vendor_tools.config.archive import ExtraFileEntry
from go_vendor_tools.config.base import load_config
from go_vendor_tools.exceptions import ArchiveError

if TYPE_CHECKING:
    from _typeshed import StrPath

ARCHIVE_FILES = (Path("go.mod"), Path("go.sum"), Path("vendor"))
GO_PROXY_ENV = {
    "GOPROXY": "https://proxy.golang.org,direct",
    "GOSUMDB": "sum.golang.org",
}


def download_extra_file(extra_file: ExtraFileEntry, directory: Path) -> None:
    """
    Basic file downloader.
    Meant for small text files, as all downloading is done in memory.
    """
    print(f"Downloading {extra_file['url']}...")
    req = requests.get(extra_file["url"])
    if not req.ok:
        raise ArchiveError(f"Failed to download requested file: {extra_file['url']}")
    dest = directory / extra_file["dest"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    with (dest).open("wb") as fp:
        fp.write(req.content)


def run_command(
    runner: Callable[..., subprocess.CompletedProcess],
    command: Sequence[StrPath],
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    print(f"$ {shlex.join(map(os.fspath, command))}")  # type: ignore[arg-type]
    return runner(command, **kwargs)


@click.command(
    context_settings={"help_option_names": ["-h", "--help"], "show_default": True}
)
@click.argument(
    "path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
)
@click.option(
    "-O",
    "--output",
    default="vendor.tar.xz",
    type=click.Path(dir_okay=False, file_okay=True, path_type=Path, resolve_path=True),
)
@click.option("--top-level-dir / --no-top-level-dir", default=False)
@click.option(
    "--use-module-proxy / --no-use-module-proxy",
    "-p",
    default=None,
    is_flag=True,
    help="Whether to enable Google's Go module proxy",
)
@click.option("-c", "--config", "config_path", type=click.Path(path_type=Path))
def main(
    path: Path,
    output: Path,
    top_level_dir: bool,
    use_module_proxy: bool | None,
    config_path: Path | None,
) -> None:
    if not output.name.endswith((".tar.xz", "txz")):
        raise ValueError(f"{output} must end with '.tar.xz' or '.txz'")
    config = load_config(config_path)
    if use_module_proxy is None:
        use_module_proxy = config["archive"]["use_module_proxy"]
    cwd = path
    cm: AbstractContextManager[str] = nullcontext(str(path))
    # Treat as an archive if it's not a directory
    if path.is_file():
        print(f"* Treating {path} as an archive. Unpacking...")
        cm = tempfile.TemporaryDirectory()
        shutil.unpack_archive(path, cm.name)
        cwd = Path(cm.name)
        cwd /= next(cwd.iterdir())
    with cm:
        env = os.environ | GO_PROXY_ENV if use_module_proxy else None
        runner = partial(subprocess.run, cwd=cwd, check=True, env=env)
        for command in config["archive"]["pre_commands"]:
            run_command(runner, command)
        run_command(runner, ["go", "mod", "tidy"])
        run_command(runner, ["go", "mod", "vendor"])
        for command in config["archive"]["post_commands"]:
            run_command(runner, command)
        for entry in config["archive"]["extra_files"]:
            download_extra_file(entry, cwd)
        print("Creating archive...")
        with tarfile.open(output, "w:xz") as tf:
            add_files_to_archive(
                tf, Path(cwd), ARCHIVE_FILES, top_level_dir=top_level_dir
            )


if __name__ == "__main__":
    main()
