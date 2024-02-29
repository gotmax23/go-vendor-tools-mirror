#!/usr/bin/env python3
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Collection, Iterable, Iterator
from pathlib import Path
from typing import IO, cast

import license_expression

from go_vendor_tools.config.licenses import LicenseConfig, LicenseEntry, load_config
from go_vendor_tools.gomod import get_unlicensed_mods
from go_vendor_tools.hashing import get_hash
from go_vendor_tools.licensing import (
    LicenseResults,
    compare_licenses,
    get_license_file_paths,
    get_license_results,
    simplify_license,
)

COLOR = None
RED = "\033[31m"
CLEAR = "\033[0m"


def red(__msg: str, /, *, file: IO[str] = sys.stdout) -> None:
    color = COLOR
    if color is None:
        color = file.isatty()
    print(f"{RED}{__msg}{CLEAR}", file=file)


def parseargs() -> argparse.Namespace:
    """
    Parse arguments and return an `argparse.Namespace`
    """
    parser = argparse.ArgumentParser(
        description="Handle licenses for vendored go projects"
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "-C",
        "--directory",
        type=Path,
        default=Path(),
        help="Top-level directory with a go.mod file and vendor directory",
    )
    parser.add_argument(
        "--color",
        action=argparse.BooleanOptionalAction,
        default=False if os.environ.get("NO_COLOR") else None,
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    report_parser = subparsers.add_parser("report", help="Main subcommand")
    report_parser.add_argument("-i", "--ignore-undetected", action="store_true")
    report_parser.add_argument(
        "--verify",
        help="Verify license expression to make sure it matches caluclated expression",
        metavar="EXPRESSION",
    )
    report_parser.add_argument(
        "mode",
        nargs="?",
        type=str,
        choices=("all", "expression", "list"),
    )
    explict_parser = subparsers.add_parser(
        "explicit", help="Add manual license entry to a config file"
    )
    explict_parser.add_argument(
        "-f", "--file", dest="license_file", required=True, type=Path
    )
    explict_parser.add_argument("license_expression")
    install_parser = subparsers.add_parser(
        "install", description=f"INTERNAL: {install_command.__doc__}"
    )
    install_parser.add_argument(
        "--install-directory", dest="install_directory", type=Path, required=True
    )
    install_parser.add_argument(
        "--destdir", dest="install_destdir", type=Path, default=Path("/")
    )
    install_parser.add_argument(
        "--filelist", dest="install_filelist", type=Path, required=True
    )

    args = parser.parse_args()
    global COLOR  # noqa: PLW0603
    COLOR = args.color
    if args.subcommand == "report" and not args.mode:
        args.mode = "list" if args.verify else "all"
    if not args.directory.is_dir():
        sys.exit(f"{args.directory} must exist and be a directory")
    if not (modtxt := args.directory / "vendor/modules.txt"):
        sys.exit(f"{modtxt} does not exist!")
    return args


def bullet_iterator(it: Iterable[object], bullet: str = "- ") -> Iterator[str]:
    for item in it:
        yield bullet + str(item)


def red_if_true(items: Collection[object], message: str, bullet: str = "- ") -> None:
    if not items:
        return
    red(message)
    red("\n".join(bullet_iterator(items, bullet)))


def print_licenses(
    results: LicenseResults,
    unlicensed_mods: Collection[Path],
    mode: str,
    show_undetected: bool,
    directory: Path,
) -> None:
    if mode in ("all", "list"):
        for (
            license_path,
            license_name,
        ) in results.simplified_license_map.items():
            print(f"{license_path.relative_to(directory)}: {license_name}")
    if (
        results.undetected_licenses
        or unlicensed_mods
        or results.unmatched_extra_licenses
    ) and show_undetected:
        if mode != "expression":
            print()
        red_if_true(
            results.undetected_licenses,
            "The following license files were found "
            "but the correct license identifier couldn't be determined:",
        )
        red_if_true(unlicensed_mods, "The following modules are missing license files:")
        red_if_true(
            results.unmatched_extra_licenses,
            "The following license files that were specified in the configuration"
            " have changed:",
        )
    if mode == "list":
        return
    if mode != "expression":
        print()
    print(results.license_expression)


def report_command(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    results = get_license_results(args.directory, config)
    unlicensed_mods = get_unlicensed_mods(
        args.directory, (*results.simplified_license_map, *results.undetected_licenses)
    )
    print_licenses(
        results,
        unlicensed_mods,
        args.mode,
        not args.ignore_undetected,
        args.directory,
    )
    if args.verify and not compare_licenses(results.license_expression, args.verify):
        sys.exit("Failed to verify license. Expected ^")
    sys.exit(bool(results.undetected_licenses or results.unmatched_extra_licenses))


def copy_licenses(
    license_paths: Iterable[Path],
    install_destdir: Path,
    install_directory: Path,
    install_filelist: Path,
) -> None:
    installdir = install_destdir / install_directory.relative_to("/")

    with install_filelist.open("w", encoding="utf-8") as fp:
        installdir.mkdir(parents=True, exist_ok=True)
        fp.write(f"%license %dir {install_directory}\n")
        for lic in license_paths:
            (installdir / lic).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(lic, installdir / lic)
            fp.write(f"%license {install_directory / lic}\n")


def install_command(args: argparse.Namespace) -> None:
    """
    Install license files into the license directory
    """
    config = load_config(args.config)
    directory: Path = args.directory
    install_destdir: Path = args.install_destdir
    install_directory: Path = args.install_directory
    install_filelist: Path = args.install_filelist
    license_paths = get_license_file_paths(directory, config)
    copy_licenses(license_paths, install_destdir, install_directory, install_filelist)


def get_relpath(base_directory: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.relative_to(base_directory)
    return path


def replace_entry(
    data: list[LicenseEntry], new_entry: LicenseEntry, relpath: Path
) -> None:
    for entry in data:
        if Path(entry["path"]) == relpath:
            cast(dict, entry).clear()
            entry.update(new_entry)
            return
    data.append(new_entry)


def explicit_command(args: argparse.Namespace) -> None:
    try:
        import tomlkit
    except ImportError:
        sys.exit("tomlkit is required for the 'explicit' subcommand")
    if not args.config:
        sys.exit("--config must be specified!")

    data: LicenseConfig = {}
    if args.config.is_file():
        with args.config.open("r", encoding="utf-8") as fp:
            data = cast("LicenseConfig", tomlkit.load(fp))

    licenses = data.setdefault("licenses", tomlkit.aot())
    relpath = get_relpath(args.directory, args.license_file)
    try:
        expression = simplify_license(args.license_expression)
    except license_expression.ExpressionError as exc:
        sys.exit(f"Failed to parse license: {exc}")
    entry = LicenseEntry(
        path=str(relpath),
        sha256sum=get_hash(args.license_file),
        expression=expression,
    )
    replace_entry(licenses, entry, relpath)
    with args.config.open("w", encoding="utf-8") as fp:
        tomlkit.dump(data, fp)


def main() -> None:
    args = parseargs()
    if args.subcommand == "report":
        report_command(args)
    elif args.subcommand == "explicit":
        explicit_command(args)
    elif args.subcommand == "install":
        install_command(args)


if __name__ == "__main__":
    main()
