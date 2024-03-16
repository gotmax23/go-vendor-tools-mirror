# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Utilities for reading configuartion
"""

from __future__ import annotations

import os

FALSY_STRINGS = frozenset(("", "0", "false"))


def get_envvar_boolean(variable: str, default: bool) -> bool:
    gotten = os.environ.get(variable)
    if gotten is None:
        return default
    return gotten.lower() not in FALSY_STRINGS
