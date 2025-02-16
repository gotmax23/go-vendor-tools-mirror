# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Shared CLI utilities
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import tomlkit

from go_vendor_tools.config.utils import get_envvar_boolean
from go_vendor_tools.exceptions import VendorToolsError


def load_tomlkit_if_exists(path: Path | None) -> tomlkit.TOMLDocument:
    if path and path.is_file():
        with path.open("r", encoding="utf-8") as fp:
            loaded = tomlkit.load(fp)
    else:
        loaded = tomlkit.document()
    return loaded


@contextmanager
def catch_vendor_tools_error() -> Iterator[None]:
    try:
        yield
    except VendorToolsError as exc:
        if get_envvar_boolean("_GVT_DEBUG", False):
            raise
        else:
            sys.exit(f"{type(exc).__name__}: {exc}")
