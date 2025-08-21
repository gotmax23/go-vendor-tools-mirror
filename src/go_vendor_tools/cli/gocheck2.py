#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# Copyright (C) 2025 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# TODO: Once this code stablizies, we should consider moving it into
# go-rpm-macros.

# TODO: Add unit tests. This is currently 92% covered, but only by integration
# tests.


"""
Rewritten gocheck2 that avoids failing fast and works with GO111MODULE enabled.
This is meant to be run using the %gocheck2 macro and not directly.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

try:
    import argcomplete
except ImportError:
    HAS_ARGCOMPLETE = False
else:
    HAS_ARGCOMPLETE = True


# Using a partial breaks pytest capsys
def eprint(*args: object, **kwargs: Any) -> None:
    kwargs.setdefault("file", sys.stderr)
    kwargs.setdefault("flush", True)
    return print(*args, **kwargs)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, prog="%gocheck2")
    # NOTE: See the comment about determining the primary goipath in the main function.
    # Allowing to pass custom paths complicates this.
    # Therefore, we might consider removing this argument before the final release.
    parser.add_argument(
        "-p",
        "--path",
        action="append",
        help="Relative paths that include go.mod packages."
        " This flag is SUBJECT TO CHANGE."
        " It is recommended to cd to the correct directory before running"
        " %%gocheck2 and not use this option.",
    )
    parser.add_argument(
        "-F",
        "--no-follow",
        help="Don't search for Go submodules (i.e., go.mod files in subdirectories)",
        action="store_false",
        dest="follow",
    )
    parser.add_argument(
        "-s",
        "--skip",
        action="append",
        help="Skip individual test function names. Can be repeated.",
    )
    parser.add_argument(
        "-d",
        "--directory",
        action="append",
        help="Exclude the files contained in DIRECTORY non-recursively."
        " This accepts either an import path or a path relative to"
        " the go import path of the go.mod in the current directory.",
    )
    parser.add_argument(
        "-t",
        "--tree",
        action="append",
        help="Exclude the files contained in DIRECTORY recursively."
        " This accepts either an import path or a path relative to"
        " the go import path of the go.mod in the current directory.",
    )
    parser.add_argument(
        "-L",
        "--list",
        help="List import paths to test, but don't run anything.",
        action="store_true",
    )
    parser.add_argument("extra_args", nargs="*")
    if HAS_ARGCOMPLETE:
        # fmt: off
        argcomplete.autocomplete(parser) # pyright: ignore[reportPossiblyUnboundVariable]
        # fmt: on
    return parser


def normpath_set(data: Iterable[str] | None) -> set[str]:
    return {os.path.normpath(p) for p in data} if data else set()


def parseargs() -> Args:
    ns = get_parser().parse_args()
    if ns.path:
        for path in ns.path:
            if os.path.isabs(path):
                sys.exit(f"Invalid absolute path: {path!r}. Paths must be relative!")
    return Args(
        paths=ns.path or ["."],
        ignore_dirs=normpath_set(ns.directory),
        ignore_trees=normpath_set(ns.tree),
        list_only=ns.list,
        extra_args=ns.extra_args or [],
        follow=ns.follow,
        test_skips=ns.skip or [],
    )


@dataclasses.dataclass
class Args:
    """
    Attributes:
        ignore_dirs: See -d in the argparser
        ignore_trees: See -t in the argparser
        list_only: See -L in the argparser
        test_skips: See -s in the argparser
        extra_args: Extra arguments to pass to go test.
        follow: Whether to search for go.mod in subdirectories and run tests there
        paths: Directories to find go.mod file in
    """

    ignore_dirs: set[str]
    ignore_trees: set[str]
    list_only: bool
    test_skips: list[str]
    extra_args: list[str]
    follow: bool
    paths: list[str]
    test_paths_seen: set[str] = dataclasses.field(init=False, default_factory=set)


@dataclasses.dataclass(frozen=True)
class GoModResult:
    gomod: str
    directory: str
    goipath: str


def logrun(cmd: Sequence[object], cwd: str = ".") -> None:
    r = "$ " if cwd == "." else f"({cwd}) $ "
    r += shlex.join(map(str, cmd))
    eprint(r)


def dir_okay(args: Args, path: str, goipath: str | None = None) -> bool:
    """
    Check if a directory is ignored.

    Returns: True if okay to test and false if ignored
    """
    path = path.removeprefix("./")
    paths = {path}
    if goipath and (stripped := path.removeprefix(goipath + "/")) != path:
        paths.add(stripped)
    if paths & args.ignore_dirs:
        return False
    for p in paths:
        p += "/"
        for tree in args.ignore_trees:
            if p.startswith(tree + "/"):
                return False
    return True


# args.follow is True
def _find_go_mods_follow(args: Args) -> list[GoModResult]:
    gomods: list[GoModResult] = []
    for path in args.paths:
        for root, dirnames, files in os.walk(path):
            for dirname in list(dirnames):
                dirpath = os.path.join(root, dirname)
                if dirpath.removeprefix("./") in args.ignore_trees:
                    dirnames.remove(dirname)
            if root.removeprefix("./") in args.ignore_dirs:
                continue
            for file in files:
                if file == "go.mod":
                    gomod = os.path.join(root, file)
                    goipath = get_goipath(gomod)
                    gomods.append(
                        GoModResult(gomod=gomod, directory=root, goipath=goipath)
                    )
                    break
            # https://book.pythontips.com/en/latest/for_-_else.html
            else:
                if root != str(path):
                    continue
                if path == ".":
                    msg = "No go.mod found in current directory"
                else:
                    msg = f"No go.mod found in {path}"
                sys.exit(msg)
    return gomods


# args.follow is False
def _find_go_mods_nofollow(args: Args) -> list[GoModResult]:
    gomods: list[GoModResult] = []
    for path in args.paths:
        gomod = os.path.join(path, "go.mod")
        if not os.path.isfile(gomod):
            sys.exit(f"{gomod!r} does not exist!")
        gomods.append(
            GoModResult(gomod=gomod, directory=path, goipath=get_goipath(gomod))
        )
    return gomods


def find_go_mods(args: Args) -> list[GoModResult]:
    return _find_go_mods_follow(args) if args.follow else _find_go_mods_nofollow(args)


def get_goipath(gomod: str | Path = "go.mod") -> str:
    cmd: list[str] = ["go", "mod", "edit", "-json", str(gomod)]
    logrun(cmd)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=False)
    data = json.loads(proc.stdout) if proc.returncode == 0 else {}
    try:
        goipath = data["Module"]["Path"]
    except KeyError:
        raise ValueError(f"Failed to retrieve Go import path from {gomod}") from None
    return goipath


def list_test_packages(
    args: Args, paths: Iterable[str], cwd: str = ".", primary_goipath: str | None = None
):
    # go list command is based on one in kubernetes Makefile.
    # The command is considered not copyrightable so the kubernetes license
    # does not apply.
    cmd = [
        "go",
        "list",
        "-find",
        "-f",
        "{{if or (gt (len .TestGoFiles) 0) (gt (len .XTestGoFiles) 0)}}{{.ImportPath}}{{end}}",  # noqa: E501,
    ]
    if tags := os.environ.get("GO_BUILDTAGS"):
        cmd.extend(("-tags", tags))
    cmd.extend(f"{goipath}/..." for goipath in paths)
    del paths  # Used up iterable
    logrun(cmd, cwd)
    proc = subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        cwd=cwd,
    )
    gotten_goipaths = proc.stdout.splitlines()
    result: list[str] = []
    for goipath in gotten_goipaths:
        if goipath in args.test_paths_seen:
            continue
        args.test_paths_seen.add(goipath)
        if dir_okay(args, goipath, primary_goipath):
            result.append(goipath)
    return result


def dogomod(args: Args, gomod: GoModResult, primary_goipath: str | None) -> int:
    test_packages = list_test_packages(
        args, [gomod.goipath], gomod.directory, primary_goipath
    )
    print(f"# {gomod.gomod}: {gomod.goipath}")
    if not test_packages:
        eprint(
            f"No test packages found for {gomod.goipath} in directory {gomod.directory}"
        )
        return 0
    if args.list_only:
        print("\n".join(test_packages))
        return 0
    extra_args = args.extra_args
    if tags := os.environ.get("GO_BUILDTAGS"):
        extra_args.extend(("-tags", tags))
    if gotest_flags := os.environ.get("GOCHECK2_GOTEST_FLAGS"):
        extra_args.extend(shlex.split(gotest_flags))
    if args.test_skips:
        extra_args.extend(("-skip", "|".join(args.test_skips)))
    cmd = ["go", "test", *extra_args, *test_packages]
    logrun(cmd, gomod.directory)
    proc = subprocess.run(cmd, check=False, cwd=gomod.directory)
    if proc.returncode != 0:
        eprint(f"Command failed with rc {proc.returncode}!")
    return proc.returncode


def main() -> None:
    if os.environ.get("GO111MODULE") == "off":
        sys.exit("G0111MODULE=off is not supported by %gocheck2. Use %gocheck instead!")
    args = parseargs()
    go_mods = find_go_mods(args)
    if not go_mods:
        sys.exit("No go.mod files found!")
    # We need to determine the root directory's go module so we can apply
    # ignore patterns that reference relative paths like the old %gocheck did.
    # This is imperfect, because with Go modules, the directory structure does
    # not have to match go module paths.
    # For example, in the etcd project:
    #  go.mod in the root directory has "go.etcd.io/etcd/v3" but api/go.mod has
    #  "go.etcd.io/etcd/api/v3," not "go.etcd.io/etcd/v3/api."
    # This means that passing "-t api" will not work.
    # Instead, it's necessary to use the full path (-t go.etcd.io/etcd/v3/api).
    if go_mods[0].directory == ".":
        primary_goipath = go_mods[0].goipath
    elif os.path.exists("go.mod"):
        primary_goipath = get_goipath()
    else:
        # TODO: Should this be made an error? Should we require the directory
        # gocheck2 is run from to have a go.mod instead of allowing it to be in
        # a subdirectory?
        eprint(
            "WARNING: No go.mod file found in CWD."
            " -d and -t flags may not work properly."
        )
        primary_goipath = None
    # TODO: Do something (e.g., show pass/fail stats by Go modules) with the
    # gomod dict keys or just make this into a simple list of dogomod() return
    # values.
    results = {gomod: dogomod(args, gomod, primary_goipath) for gomod in go_mods}
    sys.exit(max(results.values()))


if __name__ == "__main__":
    main()
