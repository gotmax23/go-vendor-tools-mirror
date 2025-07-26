# Copyright (C) 2025 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from collections.abc import Generator, Iterable
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pytest import MonkeyPatch

from go_vendor_tools.cli import go_vendor_license
from go_vendor_tools.license_detection.base import LicenseData

if TYPE_CHECKING:
    from typing_extensions import Self, TypeAlias


class CallAction(Enum):
    PRINT = auto()
    INPUT = auto()


# TODO(gotmax23): WHY DOES THIS NOT WORK ON EPEL 9 BUT ONLY SOMETIMES?
# git blame this comment for the error message.
# @dataclasses.dataclass
class Call:  # noqa: PLW1641
    action: CallAction
    args: tuple[object, ...]
    kwargs: dict[str, Any]

    # Implement the methods manually instead...
    def __init__(
        self, action: CallAction, args: tuple[object, ...], kwargs: dict[str, Any]
    ) -> None:
        self.action = action
        self.args = args
        self.kwargs = kwargs

    def __repr__(self) -> str:
        action = self.action
        args = self.args
        kwargs = self.kwargs
        return f"{type(self).__name__}({action=}, {args=}, {kwargs=})"

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return (
            self.action == other.action
            and self.args == other.args
            and self.kwargs == other.kwargs
        )

    @classmethod
    def print(cls, *args, **kwargs) -> Self:
        return cls(CallAction.PRINT, args, kwargs)

    @classmethod
    def input(cls, *args, **kwargs) -> Self:
        return cls(CallAction.INPUT, args, kwargs)


TestGenType: TypeAlias = "Generator[Any, Call, None]"


class AssertCall:
    def __init__(self) -> None:
        self.nassert = 0

    def assert_call(self, call1: Call, call2: Call) -> None:
        assert call1 == call2, f"assert {self.nassert} failed"
        self.nassert += 1


# TODO(anyone): Test combinations.
# - Both disabled
# - Nothing to fill
# - Prompt w/o autofill
# - Autofill w/o prompt
# - EXCLUDE
def generator(directory: Path) -> TestGenType:
    assert_call = AssertCall().assert_call
    p = Call.print
    i = Call.input
    yield

    assert_call(
        (yield),
        p(
            "The test_autofill backend will be used to autofill missing licenses",
            file=sys.stderr,
        ),
    )
    yield None

    assert_call((yield), p("Autofilled 1 manual license entries", file=sys.stderr))
    yield None

    assert_call((yield), p("Undetected licenses found! Please enter them manually."))
    yield None

    assert_call((yield), p(f"* Undetected license: {directory / 'LICENSE.MIT'}"))
    yield None

    assert_call((yield), i("Enter SPDX expression (or EXCLUDE): "))
    yield "MIT"

    assert_call((yield), p("Expression simplified to 'MIT'"))
    yield None


class Helper:
    def __init__(self, gen: TestGenType) -> None:
        self._gen = gen
        next(gen)

    def send(self, call: Call) -> Any:
        try:
            next(self._gen)
            return self._gen.send(call)
        except StopIteration:
            assert not call, "The generator ran out"
            raise

    def print(self, *args, **kwargs):
        return self.send(Call.print(*args, **kwargs))

    def input(self, *args, **kwargs):
        return self.send(Call.input(*args, **kwargs))

    def finish(self) -> None:
        try:
            next(self._gen)
        except StopIteration:
            return
        else:
            raise AssertionError("Generator did not finish as expected")


class TestAutofill:
    NAME = "test_autofill"

    def detect_files(
        self, files: Iterable[Path], directory: Path | None = None
    ) -> tuple[dict[Path, str], set[Path]]:
        files = set(files)
        assert files == {Path("LICENSE.GPL3"), Path("LICENSE.MIT")}
        files.remove(Path("LICENSE.GPL3"))
        return {Path("LICENSE.GPL3"): "GPL-3.0-or-later"}, files


def test_get_missing_licenses(monkeypatch: MonkeyPatch, test_data: Path) -> None:
    directory = test_data / "test_get_missing_licenses"
    helper = Helper(generator(directory))
    monkeypatch.setattr(go_vendor_license, "print", helper.print, False)
    monkeypatch.setattr(go_vendor_license, "input", helper.input, False)
    data = LicenseData(
        directory=directory,
        license_map={Path("LICENSE.BSD3"): "BSD-3-Clause"},
        undetected_licenses=frozenset({Path("LICENSE.GPL3"), Path("LICENSE.MIT")}),
        unmatched_manual_licenses=(),
        extra_license_files=(),
        detector_name="test",
    )
    expected_data = LicenseData(
        directory=directory,
        license_map={
            Path("LICENSE.BSD3"): "BSD-3-Clause",
            Path("LICENSE.GPL3"): "GPL-3.0-or-later",
            Path("LICENSE.MIT"): "MIT",
        },
        undetected_licenses=frozenset(),
        unmatched_manual_licenses=(),
        extra_license_files=(),
        detector_name="test",
    )
    config: Any = {"licensing": {"licenses": []}}
    expected_config: Any = {
        "licensing": {
            "licenses": [
                {
                    "expression": "GPL-3.0-or-later",
                    "path": "LICENSE.GPL3",
                    "sha256sum": "13fa41e00e7fea297e91099d24670d0f237a7ea853ba370330b2ea0a7fe2dcfb",  # noqa: E501
                },
                {
                    "expression": "MIT",
                    "path": "LICENSE.MIT",
                    "sha256sum": "111fc6ef9cb7a4932b0a11af2e0323b2a2130233dc1f4fa11b13cff74afc4cd9",  # noqa: E501
                },
            ]
        }
    }
    test_autofill = TestAutofill()
    gotten_data = go_vendor_license.fill_missing_licenses(
        data, config, test_autofill, True  # type: ignore
    )
    helper.finish()
    assert gotten_data == expected_data
    assert config == expected_config
