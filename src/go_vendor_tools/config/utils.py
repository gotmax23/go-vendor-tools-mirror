# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Utilities for reading configuartion
"""

from __future__ import annotations

import os

FALSY_STRINGS = frozenset(("", "0", "false"))


def get_envvar_boolean(variable: str, default: bool) -> bool:
    return str_to_bool(os.environ.get(variable), default)


def str_to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() not in FALSY_STRINGS
