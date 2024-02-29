# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
SHA256 hashing utilities
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path


def get_hash(file: Path) -> str:
    hasher = hashlib.sha256()
    with file.open("rb") as fp:
        while chunk := fp.read(4096):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_hash(file: Path, sha256sum: str) -> bool:
    if not file.is_file():
        return False
    return hmac.compare_digest(get_hash(file), sha256sum)
