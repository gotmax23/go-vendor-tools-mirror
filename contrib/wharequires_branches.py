#!/usr/bin/env python3

# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Iterable

import click
from fedrq.backends.base import PackageQueryAlias, RepoqueryBase

# NOTE(gotmax23): formatters is a private API that I'm only using because I wrote it
from fedrq.cli import formatters
from fedrq.config import get_config

from go_vendor_tools.license_detection.base import LicenseDetector
from go_vendor_tools.license_detection.load import DETECTORS


def get_whatrequires_map(
    rq: RepoqueryBase,
    detectors: Iterable[type[LicenseDetector]] = DETECTORS.values(),
) -> dict[type[LicenseDetector], PackageQueryAlias]:
    result: dict[type[LicenseDetector], PackageQueryAlias] = {}
    whatbuildrequires = rq.query(requires="go-vendor-tools", arch="src")
    for detector in detectors:
        detector_wbr = rq.query(pkg=whatbuildrequires)
        for require in detector.PACKAGES_NEEDED:
            detector_wbr = detector_wbr.intersection(rq.query(requires=require))
        result[detector] = detector_wbr
    return result


@click.command(
    context_settings={"show_default": True, "help_option_names": ["-h", "--help"]}
)
@click.option("-b", "--branch")
@click.option("-r", "--repo", default="@base")
@click.option("-F", "--formatter", "formatter_name", default="plain")
def main(branch: str | None, repo: str, formatter_name: str) -> None:
    config = get_config()
    rq = config.get_rq(branch or config.default_branch, repo)
    formatter_obj = formatters.DefaultFormatters.get_formatter(
        formatter_name, repoquery=rq
    )
    wr_map = get_whatrequires_map(rq)
    for idx, (detector, detector_wbr) in enumerate(wr_map.items()):
        for require in detector.PACKAGES_NEEDED:
            detector_wbr = detector_wbr.intersection(rq.query(requires=require))
        click.secho(f"{detector.NAME} (total {len(detector_wbr)})", bold=True)
        for line in formatter_obj.format(detector_wbr):
            click.echo(line)
        if idx + 1 < len(wr_map):
            click.echo()


if __name__ == "__main__":
    main()
