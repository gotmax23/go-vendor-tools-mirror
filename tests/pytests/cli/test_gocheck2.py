# Copyright (C) 2026 Mikel Olasagasti Uranga <mikel@olasagasti.info>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import shutil

import pytest

from go_vendor_tools.cli import gocheck2

# RPM %check buildroots often have no golang; try_get_goipath uses ``go mod edit``.
needs_go = pytest.mark.skipif(
    shutil.which("go") is None,
    reason="go executable not on PATH",
)


def test_try_get_goipath_empty_go_mod_returns_none(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    gomod = tmp_path / "go.mod"
    gomod.write_text("")
    assert gocheck2.try_get_goipath(gomod) is None
    err = capsys.readouterr().err
    assert "empty go.mod" in err


@needs_go
def test_try_get_goipath_whitespace_only_yields_empty_path(tmp_path) -> None:
    """go mod edit -json accepts only newlines but still has no module path."""
    gomod = tmp_path / "go.mod"
    gomod.write_text("\n\n")
    assert gocheck2.try_get_goipath(gomod) is None


@needs_go
def test_try_get_goipath_valid_module(tmp_path) -> None:
    gomod = tmp_path / "go.mod"
    gomod.write_text("module example.com/foo\n\ngo 1.21\n")
    assert gocheck2.try_get_goipath(gomod) == "example.com/foo"


def test_get_goipath_raises_on_empty_go_mod(tmp_path) -> None:
    gomod = tmp_path / "go.mod"
    gomod.write_text("")
    with pytest.raises(ValueError, match="Failed to retrieve"):
        gocheck2.get_goipath(gomod)


@needs_go
def test_find_go_mods_follow_skips_empty_nested_go_mod(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nested empty go.mod (Hugo's internal/warpc/genwebp) must not break discovery."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "go.mod").write_text("module example.com/root\n\ngo 1.21\n")
    nested = tmp_path / "internal/warpc/genwebp"
    nested.mkdir(parents=True)
    (nested / "go.mod").write_text("")

    args = gocheck2.Args(
        paths=["."],
        ignore_dirs=set(),
        ignore_trees=set(),
        list_only=False,
        extra_args=[],
        follow=True,
        test_skips=[],
    )
    mods = gocheck2.find_go_mods(args)
    assert len(mods) == 1
    assert mods[0].goipath == "example.com/root"
    assert mods[0].directory == "."
    err = capsys.readouterr().err
    assert "empty go.mod" in err
    assert "genwebp" in err or "internal/warpc" in err
