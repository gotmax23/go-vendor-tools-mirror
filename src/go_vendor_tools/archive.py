# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Tools for creating tar archives
"""

from __future__ import annotations

import os
import tarfile
from collections.abc import Sequence
from pathlib import Path, PurePath


### normalize_file_permissions is derived from flit_core
# Copyright (c) 2015, Thomas Kluyver and contributors
# SPDX-License-Identifier: BSD-3-Clause
def normalize_file_permissions(st_mode: int) -> int:
    """Normalize the permission bits in the st_mode field from stat to 644/755

    Popular VCSs only track whether a file is executable or not. The exact
    permissions can vary on systems with different umasks. Normalising
    to 644 (non executable) or 755 (executable) makes builds more reproducible.
    """
    # Set 644 permissions, leaving higher bits of st_mode unchanged
    new_mode = (st_mode | 0o644) & ~0o133
    if st_mode & 0o100:
        new_mode |= 0o111  # Executable: 644 -> 755
    return new_mode


def reproducible_filter(member: tarfile.TarInfo) -> tarfile.TarInfo:
    return member.replace(
        mtime=int(os.environ.get("SOURCE_DATE_EPOCH", 0)),
        mode=normalize_file_permissions(member.mode),
        uid=0,
        gid=0,
        uname="",
        gname="",
        deep=False,
    )


def add_files_to_archive(
    tf: tarfile.TarFile,
    directory: Path,
    files: Sequence[Path],
    top_level_dir: bool = False,
) -> None:
    for file in files:
        if file.is_absolute():
            raise ValueError(f"{file} is not a relative path!")
        dest = (directory.resolve().name / file) if top_level_dir else file
        tf.add(directory / file, dest, filter=reproducible_filter)


def get_toplevel_directory(tar: tarfile.TarFile) -> str | None:
    first_parent = {PurePath(info.name).parts[0] for info in tar.getmembers()}
    if len(first_parent) == 1:
        return next(iter(first_parent))
    return None
