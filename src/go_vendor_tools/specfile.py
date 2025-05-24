# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

"""
Helpers for working with specfiles
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

# specfile is opened liked this so downstreams can remove the dependency on
# specfile and use the other functionality if they so choose
try:
    import specfile
    import specfile.sections
    import specfile.sources
    import specfile.tags
    from specfile.exceptions import SpecfileException
except ImportError:
    HAS_SPECFILE = False
else:
    HAS_SPECFILE = True

from go_vendor_tools.exceptions import VendorToolsError

_T_co = TypeVar("_T_co", covariant=True)

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from typing_extensions import Self

    class _ContentContext(AbstractContextManager[_T_co], Protocol[_T_co]):
        @property
        def content(self) -> _T_co: ...


def _get_section_name(subpackage: str | None = None) -> str:
    """
    Parse a subpackage name into a %package call that can be passed to
    Sections.get()
    """
    section = "package"
    if subpackage is None:
        pass
    elif subpackage.startswith("-"):
        section += f" {subpackage[1:]}"
    else:
        section += f" -n {subpackage}"
    return section


class VendorSpecfile:
    """
    Wrapper around specfile.Specfile for working with vendor specfiles.
    Must be created using the context manager protocol.
    """

    def __init__(
        self,
        spec_path: Path | str,
        subpackage_name: str | None = None,
    ) -> None:
        """
        Args:
            spec_path: Path to specfile
            subpackage_name:
                Name of a subpackage.
                - "-NAME" for "%package NAME"
                - "NAME" for "%package -n NAME"
                - None for the main package
        """
        if not HAS_SPECFILE:
            raise ImportError("This functionality requires python3-specfile!")
        try:
            self._spec = specfile.Specfile(spec_path, autosave=True)
        except SpecfileException as exc:
            raise VendorToolsError(
                f"Failed to parse specfile {spec_path}: {exc}"
            ) from exc
        self.subpackage_name = subpackage_name

    # Interact with specfile

    @property
    def license(self) -> str:
        se = VendorToolsError(
            "Failed to access License tag in "
            + _get_section_name(self.subpackage_name),
        )
        try:
            value = self.tags().content.get("License").expanded_value
        except AttributeError as exc:
            raise se from exc
        if value is None:
            raise se
        return value

    @license.setter
    def license(self, value: str) -> None:
        with self.tags() as tags:
            try:
                tags.get("License").value = value
            except AttributeError as exc:
                raise VendorToolsError(
                    "Failed to set License tag in "
                    + _get_section_name(self.subpackage_name)
                ) from exc

    def source0_and_source1(self, directory: Path | None = None) -> tuple[Path, Path]:
        """
        Assuming that Source0 is the main archive and Source1 is the vendor archive,
        return absolute paths to each.

        Args:
            directory: Sources directory (defaults to spec path's dirname)

        Yields: (Source0 path, Source1 path)

        Raises:
            VendorToolsError: If Source0 and/or Source1 don't exist
        """
        spec_path = cast(Path, self.spec.path)
        directory = directory or spec_path.resolve().parent
        se = VendorToolsError(f"Source0 and Source1 must be specified in {spec_path}")
        try:
            source0, source1 = self.sources().content[:2]
            source0_name = source0.expanded_filename
            source1_name = source1.expanded_filename
        except IndexError:
            raise se from None
        if not source0_name or not source1_name:
            raise se
        return (directory / source0_name, directory / source1_name)

    # Lower-level
    @property
    def spec(self) -> specfile.Specfile:
        return self._spec

    def sources(self) -> _ContentContext[specfile.sources.Sources]:
        """
        Return a specfile Sources object associated with self.spec.
        """
        return self.spec.sources()

    def tags(
        self, subpackage_name: str | None = None
    ) -> _ContentContext[specfile.tags.Tags]:
        """
        Return a Tags context manager associated with self.subpackage_name

        Args:
            subpackage_name: Defaults to self.subpackage_name
        """

        return self.spec.tags(
            _get_section_name(subpackage_name or self.subpackage_name)
        )

    def save(self) -> None:
        """
        Save specfile changes to disk
        """
        self.spec.save()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_) -> None:
        self.save()
