# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from mkdocs_gen_files.editor import FilesEditor
from releaserr.scd import scd2md

HERE = Path(__file__).resolve().parent

editor = FilesEditor.current()


def main() -> None:
    files = list(HERE.glob("*.scd"))
    mandir = Path(editor.directory, "man")
    mandir.mkdir()
    new_files: list[Path] = scd2md(files, mandir)
    for file in new_files:
        editor._get_file(str(file.relative_to(editor.directory)), True)


main()
