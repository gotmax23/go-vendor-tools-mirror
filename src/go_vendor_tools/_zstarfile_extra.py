# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT
# Based on <https://git.sr.ht/~gotmax23/zstarfile/tree/main/item/src/zstarfile/extra.py>.

"""
Extra functions for dealing with archives that are not part of tarfile.
Vendored from zstarfile.
"""

from __future__ import annotations

from collections.abc import Callable
from inspect import signature
from pathlib import Path
from tarfile import TarFile
from typing import TYPE_CHECKING

from go_vendor_tools.archive import OurTarFile

if TYPE_CHECKING:
    from _typeshed import StrPath


def _get_opener(
    filename: str,
    compression_type: str | None = None,
    tarfile_class: type[TarFile] = OurTarFile,
) -> Callable[..., TarFile]:
    """
    Return a function that can be used to open `filename`.
    """
    open_meths = dict(tarfile_class.OPEN_METH)
    method: str | None = None
    tar_method = open_meths.pop("tar")
    if compression_type:
        if compression_type not in open_meths:
            raise ValueError(f"Invalid compression_type: {compression_type}")
        method = open_meths[compression_type]
    elif filename.endswith(".tar"):
        method = tar_method
    else:
        for ext, meth in open_meths.items():
            if filename.endswith((f".t{ext}", f".tar.{ext}")):
                method = meth
                break
    if not method:
        raise ValueError(f"No match found for {filename}")
    return getattr(tarfile_class, method)


def open_write_compressed(
    file: StrPath,
    /,
    compression_type: str | None = None,
    compresslevel: int | None = None,
    tarfile_class: type[TarFile] = OurTarFile,
    **kwargs,
) -> TarFile:
    """
    Open a TarFile for writing and automatically detect the compression type
    based on the filename

    Args:
        file: File path
        compression_type:
            Compression type, such as `tar` (uncompressed), `gz`, or `bz2`.
            By default, detect filetype based on the filename
        compresslevel:
            An integer compression level.
            If `compresslevel` is None, do not pass the kwarg down to pass the
            kwarg down to the TarFile constructor.
        tarfile_class:
            [`tarfile.TarFile`][tarfile.TarFile] or a subclass
    """
    kwargs.pop("mode", None)
    opener = _get_opener(Path(file).name, compression_type, tarfile_class)
    sig_params = signature(opener).parameters
    if compresslevel is not None:
        level_param_name: str | None = None
        if "compresslevel" in sig_params:
            level_param_name = "compresslevel"
        elif "level" in sig_params:
            level_param_name = "level"
        if level_param_name is None:
            raise ValueError(
                f"compresslevel is not a valid option for {opener.__name__}"
            )
        kwargs[level_param_name] = compresslevel
    return opener(file, "w", **kwargs)


__all__ = ("open_write_compressed",)
