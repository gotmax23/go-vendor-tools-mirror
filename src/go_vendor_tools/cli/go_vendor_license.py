#!/usr/bin/env python3
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
from collections.abc import Collection, Iterable, Iterator, MutableSequence, Sequence
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import IO, Any, cast

import license_expression

from go_vendor_tools import __version__
from go_vendor_tools.archive import get_toplevel_directory
from go_vendor_tools.config.base import load_config
from go_vendor_tools.config.licenses import (
    LicenseConfig,
    LicenseEntry,
    create_license_config,
)
from go_vendor_tools.gomod import get_unlicensed_mods
from go_vendor_tools.hashing import get_hash
from go_vendor_tools.license_detection.base import LicenseData, LicenseDetector
from go_vendor_tools.license_detection.load import DETECTORS, get_detctors
from go_vendor_tools.licensing import compare_licenses, simplify_license
from go_vendor_tools.specfile_sources import get_path_and_output_from_specfile

try:
    import tomlkit
except ImportError:
    HAS_TOMLKIT = False
else:
    HAS_TOMLKIT = True
    from go_vendor_tools.cli.utils import load_tomlkit_if_exists

COLOR = None
RED = "\033[31m"  # ]
CLEAR = "\033[0m"  # ]


def red(__msg: str, /, *, file: IO[str] = sys.stdout) -> None:
    color = COLOR
    if color is None:
        color = file.isatty()
    print(f"{RED if color else ''}{__msg}{CLEAR if color else ''}", file=file)


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


def _add_json_argument(parser: argparse.ArgumentParser, **kwargs) -> None:
    our_kwargs: dict[str, Any] = {
        "type": Path,
        "help": "Write license data to a JSON file",
    }
    kwargs = our_kwargs | kwargs
    parser.add_argument("--write-json", **kwargs)


def parseargs(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse arguments and return an `argparse.Namespace`
    """
    parser = argparse.ArgumentParser(
        description="Handle licenses for vendored go projects"
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("-c", "--config", type=Path, dest="config_path")
    parser.add_argument(
        "-C",
        "--path",
        "--directory",
        type=Path,
        dest="directory",
        action="append",
        help=dedent(
            """
        Can be one of the following:

        1. Top-level directory with a go.mod file and vendor directory
        2. If --use-archive is specified, treat as a tarball and unpack it. Can
           be specified multiple times to unpack multiple tarballs on
           top of one another.
        3. Path to a specfile.
           The paths to Source0 and Source1 will be automatically unpacked.
        """
        ),
    )
    parser.add_argument("--use-archive", action="store_true")
    parser.add_argument(
        "--color",
        action=argparse.BooleanOptionalAction,
        default=False if os.environ.get("NO_COLOR") else None,
    )
    parser.add_argument(
        "-d",
        "--detector",
        choices=DETECTORS,
        default=None,
        help="Choose a license detector. Choices: %(choices)s. Default: autodetect",
        dest="detector_name",
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
        "--prompt",
        action=argparse.BooleanOptionalAction,
        help="Whether to prompt to fill in undetected licenses."
        " Default: %(default)s",
    )
    report_parser.add_argument(
        "mode",
        nargs="?",
        type=str,
        choices=("all", "expression", "list"),
        default="all",
    )
    _add_json_argument(report_parser)
    report_parser.add_argument(
        "--write-config", help="Write a base config.", action="store_true"
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
    # TODO(gotmax23): Should we support writing JSON from the install command
    # or just reading it? _add_json_argument(install_parser)
    generate_buildrequires_parser = subparsers.add_parser(  # noqa F841
        "generate_buildrequires"
    )

    args = parser.parse_args(argv)
    args.directory = list(map(Path, args.directory or (".")))
    if args.subcommand not in ("explicit",):
        loaded = load_config(
            args.config_path, allow_missing=getattr(args, "write_config", False)
        )
        args.config = loaded["licensing"]
        if not args.detector_name:
            args.detector_name = args.config["detector"]
    if args.subcommand in ("report", "install"):
        args.detector = choose_license_detector(
            args.detector_name, args.config, args.detector_config
        )
        # TODO(anyone): Replace the print if/when we implement more granular logging
        print("Using detector:", args.detector.NAME, file=sys.stderr)
    global COLOR  # noqa: PLW0603
    COLOR = args.color
    return args


def bullet_iterator(it: Iterable[object], bullet: str = "- ") -> Iterator[str]:
    for item in it:
        yield bullet + str(item)


def red_if_true(items: Collection[object], message: str, bullet: str = "- ") -> None:
    if not items:
        return
    print(message)
    red("\n".join(bullet_iterator(items, bullet)))


def paths_relative_to_list(paths: Collection[Path], directory: Path) -> list[Path]:
    return [path.resolve().relative_to(directory.resolve()) for path in paths]


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
            print(f"{license_path}: {license_name}")
    if (
        results.undetected_licenses
        or unlicensed_mods
        or results.unmatched_extra_licenses
    ):
        if mode != "expression":
            print()
        if show_undetected:
            red_if_true(
                paths_relative_to_list(results.undetected_licenses, directory),
                "The following license files were found "
                "but the correct license identifier couldn't be determined:",
            )
        if show_unlicensed:
            red_if_true(
                paths_relative_to_list(unlicensed_mods, directory),
                "The following modules are missing license files:",
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


def write_license_json(data: LicenseData, file: Path) -> None:
    with file.open("w", encoding="utf-8") as fp:
        json.dump(data.to_jsonable(), fp)


@cache
def need_tomlkit(action="this action"):
    if not HAS_TOMLKIT:
        message = f"tomlkit is required for {action}. Please install it!"
        sys.exit(message)


def tomlkit_dump(obj: Any, path: Path) -> None:
    need_tomlkit()
    with path.open("w") as fp:
        tomlkit.dump(obj, fp)


def prompt_missing_licenses(
    data: LicenseData,
    entries: MutableSequence[LicenseEntry],
) -> tuple[LicenseData, MutableSequence[LicenseEntry]]:
    if not data.undetected_licenses:
        return data, entries
    print("Undetected licenses found! Please enter them manually.")
    undetected_licenses = set(data.undetected_licenses)
    license_map: dict[Path, str] = dict(data.license_map)
    for undetected in sorted(data.undetected_licenses):
        print(f"* Undetected license: {data.directory / undetected}")
        expression_str = input("Enter SPDX expression (or IGNORE): ")
        if expression_str == "IGNORE":
            undetected_licenses.remove(undetected)
            print("Ignoring...")
            continue
        expression: str = (
            str(simplify_license(expression_str)) if expression_str else ""
        )
        print(f"Expression simplified to {expression!r}")
        license_map[undetected] = expression
        entry_dict = LicenseEntry(
            path=str(undetected),
            sha256sum=get_hash(data.directory / undetected),
            expression=expression,
        )
        replace_entry(entries, entry_dict, undetected)
        undetected_licenses.remove(undetected)
    assert not undetected_licenses
    return (
        data.replace(undetected_licenses=undetected_licenses, license_map=license_map),
        entries,
    )


def _write_config_verify_path(config_path: Path | None) -> Path:
    if config_path:
        return config_path
    need_tomlkit("--write-config")

    default = Path.cwd() / "go-vendor-tools.toml"
    if default.is_file():
        sys.exit("--write-config: Please pass --config to write configuration file!")
    else:
        print(
            "WARNING --write-config: No --config path specified"
            f" Will write to {default}",
            file=sys.stderr,
        )
    return config_path or default


def get_report_write_config_data(
    config_path: Path | None, detector: LicenseDetector
) -> tuple[Path, tomlkit.TOMLDocument]:
    need_tomlkit("--write-config")
    new_config_path = _write_config_verify_path(config_path)
    loaded = load_tomlkit_if_exists(config_path)
    write_config_data = loaded.setdefault("licensing", {})
    write_config_data |= {"detector": detector.NAME}
    return new_config_path, loaded


def write_and_prompt_report_licenses(
    license_data: LicenseData, write_config_data: tomlkit.TOMLDocument
) -> LicenseData:
    # fmt: off
    license_config_list = (
        write_config_data
        .setdefault("licensing", {})
        .setdefault("licenses", tomlkit.aot() if HAS_TOMLKIT else [])
    )
    # fmt: on
    license_data, _ = prompt_missing_licenses(license_data, license_config_list)
    return license_data


@contextmanager
def handle_alternative_sources(
    directories: Sequence[Path], is_archive: bool
) -> Iterator[Path]:
    directories = list(directories)
    # The CLI code already checks that the value is greater than zero, so
    # assert is fine here
    assert directories
    if not is_archive and len(directories) > 1:
        sys.exit("Too many paths were passed!")

    if directories[0].suffix == ".spec":
        directories[:] = get_path_and_output_from_specfile(directories[0])
        is_archive = True
    if is_archive:
        with TemporaryDirectory() as _tmp:
            tmp = Path(_tmp)
            # Extract the first archive
            with tarfile.open(directories[0]) as tar:
                first_toplevel = get_toplevel_directory(tar)
                if not first_toplevel:
                    sys.exit(f"{directories[0]} does not have a top-level directory!")
                print(f"Extracting {directories[0]}", file=sys.stderr)
                tar.extractall(tmp)
            for directory in directories[1:]:
                with tarfile.open(directory) as tar:
                    toplevel = get_toplevel_directory(tar)
                    print(f"Extracting {directory}", file=sys.stderr)
                    tar.extractall(tmp if toplevel else tmp / first_toplevel)
            yield tmp / first_toplevel

    else:
        yield directories[0]


def report_command(args: argparse.Namespace) -> None:
    detector: LicenseDetector = args.detector
    paths: Sequence[Path] = args.directory
    ignore_undetected: bool = args.ignore_undetected
    ignore_unlicensed_mods: bool = args.ignore_unlicensed_mods
    mode: str = args.mode
    verify: str | None = args.verify
    write_json: Path | None = args.write_json
    write_config: Path | None = args.write_config
    prompt: bool = args.prompt
    config_path: Path | None = args.config_path
    use_archive: bool = args.use_archive
    del args

    if write_config:
        config_path, loaded = get_report_write_config_data(config_path, detector)

    with handle_alternative_sources(paths, use_archive) as directory:
        license_data: LicenseData = detector.detect(directory)
        unlicensed_mods = (
            set()
            if ignore_unlicensed_mods
            else get_unlicensed_mods(directory, license_data.license_file_paths)
        )
        if prompt:
            license_data = write_and_prompt_report_licenses(license_data, loaded)
        print_licenses(
            license_data,
            unlicensed_mods,
            mode,
            not ignore_undetected,
            not ignore_unlicensed_mods,
            directory,
        )
    if write_json:
        write_license_json(license_data, write_json)
    if verify and not compare_licenses(license_data.license_expression, verify):
        sys.exit("Failed to verify license. Expected ^")
    if write_config:
        tomlkit_dump(loaded, cast(Path, config_path))
    sys.exit(
        bool(
            (license_data.undetected_licenses and not ignore_undetected)
            or (unlicensed_mods and not ignore_unlicensed_mods)
            or license_data.unmatched_extra_licenses
        )
    )


def copy_licenses(
    base_directory: Path,
    license_paths: Iterable[Path],
    install_destdir: Path,
    install_directory: Path,
    install_filelist: Path,
) -> None:
    installdir = install_destdir / install_directory.relative_to("/")
    base_directory = base_directory.resolve()

    with install_filelist.open("w", encoding="utf-8") as fp:
        installdir.mkdir(parents=True, exist_ok=True)
        fp.write(f"%license %dir {install_directory}\n")
        for lic in license_paths:
            relpath = lic.resolve().relative_to(base_directory)
            (installdir / relpath).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(lic, installdir / relpath)
            fp.write(f"%license {install_directory / relpath}\n")


def install_command(args: argparse.Namespace) -> None:
    """
    Install license files into the license directory
    """
    directory: Path = args.directory[0]
    detector: LicenseDetector = args.detector
    install_destdir: Path = args.install_destdir
    install_directory: Path = args.install_directory
    install_filelist: Path = args.install_filelist
    del args

    license_data: LicenseData = detector.detect(directory)
    copy_licenses(
        directory,
        sorted({*license_data.license_file_paths, *license_data.extra_license_files}),
        install_destdir,
        install_directory,
        install_filelist,
    )


def get_relpath(base_directory: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.relative_to(base_directory)
    return path


def replace_entry(
    data: MutableSequence[LicenseEntry], new_entry: LicenseEntry, relpath: Path
) -> None:
    for entry in data:
        if entry == new_entry:
            return
        if Path(entry["path"]) == relpath:
            cast(dict, entry).clear()
            entry.update(new_entry)
            return
    data.append(new_entry)


def explicit_command(args: argparse.Namespace) -> None:
    if not args.config_path:
        sys.exit("--config must be specified!")
    loaded = load_tomlkit_if_exists(args.config_path)

    if "licensing" not in loaded:
        loaded.add("licensing", tomlkit.table())
    data = loaded["licensing"]

    licenses = cast(dict, data).setdefault("licenses", tomlkit.aot())
    relpath = get_relpath(args.directory[0], args.license_file)
    try:
        expression = (
            simplify_license(args.license_expression) if args.license_expression else ""
        )
    except license_expression.ExpressionError as exc:
        sys.exit(f"Failed to parse license: {exc}")
    entry = LicenseEntry(
        path=str(relpath),
        sha256sum=get_hash(args.license_file),
        expression=expression,
    )
    replace_entry(licenses, entry, relpath)
    tomlkit_dump(loaded, args.config_path)


def generate_buildrequires_command(args: argparse.Namespace) -> None:
    detector: str = args.detector_name
    del args

    if not detector:
        # If the detector is not explicitly specified, attempt to fall back to
        # the one whose dependencies are already installed.
        available, missing = get_detctors({}, create_license_config())
        detector = next(iter(available), "") or next(iter(missing))
    elif detector not in DETECTORS:
        sys.exit(f"{detector!r} is does not exist! Choices: {tuple(DETECTORS)}")
    detector_cls = DETECTORS[detector]
    for requirement in detector_cls.PACKAGES_NEEDED:
        print(requirement)


def main(argv: list[str] | None = None) -> None:
    args = parseargs(argv)
    if args.subcommand == "report":
        report_command(args)
    elif args.subcommand == "explicit":
        explicit_command(args)
    elif args.subcommand == "install":
        install_command(args)
    elif args.subcommand == "generate_buildrequires":
        generate_buildrequires_command(args)


if __name__ == "__main__":
    main()
