# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Shared CLI utilities
"""

from __future__ import annotations

from pathlib import Path

import tomlkit


def load_tomlkit_if_exists(path: Path | None) -> tomlkit.TOMLDocument:
    if path and path.is_file():
        with path.open("r", encoding="utf-8") as fp:
            loaded = tomlkit.load(fp)
    else:
        loaded = tomlkit.document()
    return loaded
