# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

import pytest

from go_vendor_tools.config.base import BaseConfig, load_config
from go_vendor_tools.license_detection.base import LicenseDetector
from go_vendor_tools.license_detection.load import get_detectors as gd

HERE = Path(__file__).resolve().parent
TEST_DATA = HERE / "test_data"
CONFIG1 = load_config(TEST_DATA / "case1" / "config.toml")


@pytest.fixture
def test_data() -> Path:
    return TEST_DATA


@pytest.fixture
def config1(test_data: Path) -> BaseConfig:
    return load_config(test_data / "case1" / "config.toml")


@pytest.fixture
def config1_broken(test_data: Path) -> BaseConfig:
    return load_config(test_data / "case1" / "config-broken.toml")


def get_available_detectors() -> list[type[LicenseDetector]]:
    # TODO(anyone): Allow enforcing "strict mode" if any detectors are missing
    # This can be a env var and then enabled in the noxfile.
    available, _missing = gd({}, CONFIG1["licensing"])
    # HACK: We initialize the classes using a test config to check if they are
    # available and then return the base class so that it can be reinitialized
    return [type(d) for d in available.values()]


@pytest.fixture(name="detector", params=get_available_detectors())
def get_detectors(request) -> type[LicenseDetector]:
    return request.param
