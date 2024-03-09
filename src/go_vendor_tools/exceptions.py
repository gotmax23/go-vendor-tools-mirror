# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Exceptions used throughout the codebase
"""

from __future__ import annotations


class VendorToolsError(Exception):
    """
    Base Exception class
    """


class MissingDependencyError(VendorToolsError):
    """
    An optional dependency required by this operation is missing
    """


class LicenseError(VendorToolsError):
    """
    An issue occured while detecting licenses
    """


class ConfigError(VendorToolsError):
    """
    Failed to load config
    """


class ArchiveError(VendorToolsError):
    """
    An issue occured while creating an archive
    """
