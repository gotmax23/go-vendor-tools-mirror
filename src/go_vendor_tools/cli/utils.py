# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Shared CLI utilities
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

try:
    import tomlkit
except ImportError:
    HAS_TOMLKIT = False
else:
    HAS_TOMLKIT = True

from go_vendor_tools.config.utils import get_envvar_boolean
from go_vendor_tools.exceptions import MissingDependencyError, VendorToolsError


def need_tomlkit(action="this action"):
    if not HAS_TOMLKIT:
        message = f"tomlkit is required for {action}. Please install it!"
        raise MissingDependencyError(message)


def tomlkit_dump(obj: Any, path: Path) -> None:
    need_tomlkit()
    with path.open("w") as fp:
        tomlkit.dump(obj, fp)


def load_tomlkit_if_exists(path: Path | None) -> tomlkit.TOMLDocument:
    if path and path.is_file():
        with path.open("r", encoding="utf-8") as fp:
            loaded = tomlkit.load(fp)
    else:
        loaded = tomlkit.document()
    return loaded


def color_default(environ: dict[str, str] | None = None) -> bool | None:
    environ = cast(dict[str, str], os.environ if environ is None else environ)
    if environ.get("FORCE_COLOR"):
        return True
    if environ.get("NO_COLOR"):
        return False
    return None


@contextmanager
def catch_vendor_tools_error() -> Iterator[None]:
    try:
        yield
    except VendorToolsError as exc:
        if get_envvar_boolean("_GVT_DEBUG", False):
            raise
        else:
            sys.exit(f"{type(exc).__name__}: {exc}")
