#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# Copyright (C) 2025 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT
# TODO: Once this code stablizies, we should consider moving it into
# go-rpm-macros.

"""
Rewritten gocheck2 that avoids failing fast and works with GOMODULESMODE enabled.
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
from collections.abc import Iterable
from functools import partial
from pathlib import Path

try:
    import argcomplete
except ImportError:
    HAS_ARGCOMPLETE = False
else:
    HAS_ARGCOMPLETE = True

eprint = partial(print, file=sys.stderr)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, prog="%gocheck2")
    parser.add_argument(
        "-p",
        "--path",
        help="Relative paths that include go.mod packages",
    )
    parser.add_argument(
        "-f",
        "--no-follow",
        help="Don't search for Go submodules (i.e., go.mod files in subdirectories)",
        action="store_false",
        dest="follow",
    )
    # parser.add_argument("-I", "--ignore", nargs="*", help="Ignore individual tests")
    parser.add_argument(
        "-d",
        "--directory",
        nargs="*",
        help="Exclude the files contained in DIRECTORY non-recursively."
        " This accepts either an import path or a subdirectory of %%goipath.",
    )
    parser.add_argument(
        "-t",
        "--tree",
        nargs="*",
        help="Exclude the files contained in DIRECTORY recursively."
        " This accepts either an import path or a subdirectory of %%goipath.",
    )
    parser.add_argument(
        "-L",
        "--list",
        help="List import paths to test, but don't run anything.",
        action="store_true",
    )
    parser.add_argument("extra_args", nargs="*")
    if HAS_ARGCOMPLETE:
        argcomplete.autocomplete( # pyright: ignore[reportPossiblyUnboundVariable]
            parser
        )
    return parser


def parseargs() -> Args:
    ns = get_parser().parse_args()
    if ns.path:
        for path in ns.path:
            if os.path.isabs(path):
                sys.exit(f"Invalid absolute path: {path!r}. Paths must be relative!")
    return Args(
        paths=ns.path or ["."],
        ignore_dirs=ns.directory or [],
        ignore_trees=ns.tree or [],
        list_only=ns.list,
        extra_args=ns.extra_args or [],
        follow=ns.follow,
    )


@dataclasses.dataclass
class Args:
    """
    Attributes:
        ignore_dirs: See -d in the argparser
        ignore_trees: See -t in the argparser
        list_only: See -L in the argparser
        extra_args: Extra arguments to pass to go test.
    """

    ignore_dirs: list[str]
    ignore_trees: list[str]
    list_only: bool
    # ignored_tests: list[str]
    extra_args: list[str]
    follow: bool
    paths: list[str]
    test_paths_seen: set[str] = dataclasses.field(init=False, default_factory=set)


def is_relative_to(path: str | Path, start: str | Path) -> bool:
    try:
        rel = os.path.relpath(path, start)
    except ValueError:
        return False
    return not rel.startswith("../")


def find_go_mods(args: Args) -> list[str]:
    visited: set[str] = set()
    gomods: list[str] = []
    if args.follow:
        for path in args.paths:
            for root, dirnames, files in os.walk(path):
                for dirname in list(dirnames):
                    dirpath = os.path.join(root, dirname)
                    if dirpath in visited:
                        continue
                    visited.add(dirpath)
                    if dirpath in args.ignore_dirs or any(
                        is_relative_to(dirpath, ignore_tree)
                        for ignore_tree in args.ignore_trees
                    ):
                        dirnames.remove(dirname)
                        continue
                for file in files:
                    if file == "go.mod":
                        gomods.append(os.path.join(root, file))
                        break
    else:
        for path in args.paths:
            gomod = os.path.join(path, "go.mod")
            if not os.path.isfile(gomod):
                sys.exit(f"{gomod!r} does not exist!")
            gomods.append(gomod)
    return gomods


def get_goipath(gomod: str | Path = "go.mod") -> str:
    cmd: list[str] = ["go", "mod", "edit", "-json", str(gomod)]
    eprint(f"$ {shlex.join(cmd)}")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=False)
    data = json.loads(proc.stdout) if proc.returncode == 0 else {}
    try:
        goipath = data["Module"]["Path"]
    except KeyError:
        sys.exit(f"Failed to retrieve Go import path from {gomod}")
    return goipath


def list_test_packages(args: Args, paths: Iterable[str], cwd: str = "."):
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
    eprint(f"$ cd {shlex.quote(cwd)}")
    eprint(f"$ {shlex.join(cmd)}")
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
        if goipath in args.ignore_dirs or any(
            (goipath + "/").startswith(tree + "/") for tree in args.ignore_trees
        ):
            continue
        result.append(goipath)
    return result


def dogomod(args: Args, gomod: str | Path) -> int:
    cwd = os.path.dirname(gomod)
    goipath = get_goipath(gomod)
    test_packages = list_test_packages(args, [goipath], cwd)
    if not test_packages:
        eprint(f"No test packages for {goipath} in directory {cwd}")
    if args.list_only:
        print(f"# {gomod}")
        print("\n".join(test_packages))
        return 0
    extra_args = args.extra_args
    if tags := os.environ.get("GO_BUILDTAGS"):
        extra_args.extend(("-tags", tags))
    if gotest_flags := os.environ.get("GOCHECK2_GOTEST_FLAGS"):
        extra_args.extend(shlex.split(gotest_flags))
    cmd = ["go", "test", *extra_args, *test_packages]
    eprint(f"$ {shlex.join(cmd)}")
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        eprint(f"Command failed with rc {proc.returncode}!")
    return proc.returncode


def main() -> None:
    if os.environ.get("GO111MODULE") == "off":
        sys.exit("G0111MODULE=off is not supported by %gocheck2. Use %gocheck instead!")
    args = parseargs()
    go_mods = find_go_mods(args)
    results = {gomod: dogomod(args, gomod) for gomod in go_mods}
    sys.exit(max(results.values()))


if __name__ == "__main__":
    main()
