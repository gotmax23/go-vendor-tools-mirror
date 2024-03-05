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

from go_vendor_tools.config.base import load_config
from go_vendor_tools.config.licenses import LicenseConfig, LicenseEntry
from go_vendor_tools.gomod import get_unlicensed_mods
from go_vendor_tools.hashing import get_hash
from go_vendor_tools.license_detection.base import LicenseData, LicenseDetector
from go_vendor_tools.license_detection.load import DETECTORS, get_detctors
from go_vendor_tools.licensing import compare_licenses, simplify_license

COLOR = None
RED = "\033[31m"  # ]
CLEAR = "\033[0m"  # ]


def red(__msg: str, /, *, file: IO[str] = sys.stdout) -> None:
    color = COLOR
    if color is None:
        color = file.isatty()
    print(f"{RED}{__msg}{CLEAR}", file=file)


def split_kv_options(kv_config: list[str]) -> dict[str, str]:
    results: dict[str, str] = {}
    for opt in kv_config:
        if ";" in opt:
            results |= split_kv_options(opt.split(";"))
        else:
            key, _, value = opt.partition("=")
            results[key] = value
    return results


def choose_license_detector(
    choice: str | None, license_config: LicenseConfig, kv_config: list[str] | None
) -> LicenseDetector:
    kv_config = kv_config or []
    cli_config = split_kv_options(kv_config)
    available, missing = get_detctors(cli_config, license_config)
    if choice:
        if choice in missing:
            sys.exit(f"Failed to get detector {choice!r}: {missing[choice]}")
        return available[choice]
    if not available:
        print("Failed to load license detectors:", file=sys.stderr)
        for detector, err in missing.items():
            print(f"! {detector}: {err}")
        sys.exit()
    return next(iter(available.values()))


def parseargs(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse arguments and return an `argparse.Namespace`
    """
    parser = argparse.ArgumentParser(
        description="Handle licenses for vendored go projects"
    )
    parser.add_argument("-c", "--config", type=Path, dest="config_path")
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
    parser.add_argument(
        "-d",
        "--detector",
        choices=DETECTORS,
        default=os.environ.get("GO_VENDOR_LICENSE_DETECTOR"),
        help="Choose a license detector. Choices: %(choices)s. Default: autodetect",
    )
    parser.add_argument(
        "-D",
        "--dc",
        "--detector-config",
        help="KEY=VALUE pairs to pass to the license detector."
        " Can be passed multiple times",
        dest="detector_config",
        action="append",
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.required = True
    report_parser = subparsers.add_parser("report", help="Main subcommand")
    report_parser.add_argument(
        "-i",
        "--ignore-undetected",
        action="store_true",
        help="Whether to show undetected licenses in the output",
    )
    report_parser.add_argument(
        "-L",
        "--ignore-unlicensed-mods",
        action="store_true",
        help="Whether to show Go modules without licenses in the output",
    )
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

    args = parser.parse_args(argv)
    if args.subcommand != "explicit":
        args.config = load_config(args.config_path)["licensing"]
        if not args.detector:
            args.detector = args.config["detector"]
        args.detector = choose_license_detector(
            args.detector, args.config, args.detector_config
        )
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
    print(message)
    red("\n".join(bullet_iterator(items, bullet)))


def print_licenses(
    results: LicenseData,
    unlicensed_mods: Collection[Path],
    mode: str,
    show_undetected: bool,
    show_unlicensed,
    directory: Path,
) -> None:
    if mode in ("all", "list"):
        for (
            license_path,
            license_name,
        ) in results.license_map.items():
            print(f"{license_path.relative_to(directory)}: {license_name}")
    if (
        results.undetected_licenses
        or unlicensed_mods
        or results.unmatched_extra_licenses
    ):
        if mode != "expression":
            print()
        if show_undetected:
            red_if_true(
                results.undetected_licenses,
                "The following license files were found "
                "but the correct license identifier couldn't be determined:",
            )
        if show_unlicensed:
            red_if_true(
                unlicensed_mods, "The following modules are missing license files:"
            )
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
    detector: LicenseDetector = args.detector
    directory: Path = args.directory
    ignore_undetected: bool = args.ignore_undetected
    ignore_unlicensed_mods: bool = args.ignore_unlicensed_mods
    mode: str = args.mode
    verify: str | None = args.verify
    del args

    license_data: LicenseData = detector.detect(directory)
    unlicensed_mods = get_unlicensed_mods(directory, license_data.license_file_paths)
    print_licenses(
        license_data,
        unlicensed_mods,
        mode,
        not ignore_undetected,
        not ignore_unlicensed_mods,
        directory,
    )
    if verify and not compare_licenses(license_data.license_expression, verify):
        sys.exit("Failed to verify license. Expected ^")
    sys.exit(
        bool(
            (license_data.undetected_licenses and not ignore_undetected)
            or (unlicensed_mods and not ignore_unlicensed_mods)
            or license_data.unmatched_extra_licenses
        )
    )


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
    directory: Path = args.directory
    detector: LicenseDetector = args.detector
    install_destdir: Path = args.install_destdir
    install_directory: Path = args.install_directory
    install_filelist: Path = args.install_filelist
    del args

    license_data: LicenseData = detector.detect(directory)
    copy_licenses(
        license_data.license_file_paths,
        install_destdir,
        install_directory,
        install_filelist,
    )


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
    if not args.config_path:
        sys.exit("--config must be specified!")

    if args.config_path.is_file():
        with args.config_path.open("r", encoding="utf-8") as fp:
            loaded = tomlkit.load(fp)
    else:
        loaded = tomlkit.document()
    if "licensing" not in loaded:
        loaded.add("licensing", tomlkit.table())
    data = loaded["licensing"]

    licenses = cast(dict, data).setdefault("licenses", tomlkit.aot())
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
    with args.config_path.open("w", encoding="utf-8") as fp:
        tomlkit.dump(loaded, fp)


def main(argv: list[str] | None = None) -> None:
    args = parseargs(argv)
    if args.subcommand == "report":
        report_command(args)
    elif args.subcommand == "explicit":
        explicit_command(args)
    elif args.subcommand == "install":
        install_command(args)


if __name__ == "__main__":
    main()
