#!/usr/bin/env python3
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
import tempfile
from contextlib import AbstractContextManager, nullcontext
from functools import partial
from pathlib import Path

import click

from go_vendor_tools.archive import add_files_to_archive

ARCHIVE_FILES = (Path("go.mod"), Path("go.sum"), Path("vendor"))


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
def main(path: Path, output: Path, top_level_dir: bool) -> None:
    if not output.name.endswith((".tar.xz", "txz")):
        raise ValueError(f"{output} must end with '.tar.xz' or '.txz'")
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
        runner = partial(subprocess.run, cwd=cwd, check=True)
        print("* go mod tidy", file=sys.stderr)
        runner(["go", "mod", "tidy"])
        print("* go mod vendor", file=sys.stderr)
        runner(["go", "mod", "vendor"])
        with tarfile.open(output, "w:xz") as tf:
            add_files_to_archive(
                tf, Path(cwd), ARCHIVE_FILES, top_level_dir=top_level_dir
            )


if __name__ == "__main__":
    main()
