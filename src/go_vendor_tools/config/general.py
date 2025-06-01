# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
General configuration
"""

from __future__ import annotations

import os.path
from typing import Any, TypedDict, cast


class GeneralConfig(TypedDict):
    go_mod_dir: str | None


def create_general_config(config: dict[str, Any] | None = None) -> GeneralConfig:
    # Keep the same order here as in ArchiveConfig definition
    config = {} if config is None else config.copy()
    if (go_mod_dir := config.setdefault("go_mod_dir", None)) and os.path.isabs(
        go_mod_dir
    ):
        raise ValueError(f"general.go_mod_dir: {go_mod_dir!r} must be a relative path")
    return cast(GeneralConfig, config)
