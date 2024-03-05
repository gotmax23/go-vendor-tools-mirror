# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TEST_DATA = HERE / "test_data"


@pytest.fixture
def test_data() -> Path:
    return TEST_DATA
