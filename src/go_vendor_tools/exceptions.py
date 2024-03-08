# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Exceptions used throughout the codebase
"""

from __future__ import annotations


class VendorToolsException(Exception):
    """
    Base Exception class
    """


class MissingDependencyError(Exception):
    """
    An optional dependency required by this operation is missing
    """


class LicenseError(VendorToolsException):
    """
    An issue occured while detecting licenses
    """


class ConfigError(VendorToolsException):
    """
    Failed to load config
    """


class ArchiveError(VendorToolsException):
    """
    An issue occured while creating an archive
    """
