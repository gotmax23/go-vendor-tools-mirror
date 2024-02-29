#!/usr/bin/env python3

# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
#
# SPDX-License-Identifier: MIT

"""
Sync the upstream specfile with downstream.
Include gpg signature and verify it.
"""

import argparse
import subprocess
import specfile
from pathlib import Path


def parseargs() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path, nargs=1)
    return parser.parse_args()


def main():
    args = parseargs()
    out = args.out[0]
    with specfile.Specfile(out) as spec:
        with spec.sources() as sources:
            sources.insert_numbered(1, sources[0].location.strip() + ".asc")
            sources.insert_numbered(2, "https://meta.sr.ht/~gotmax23.pgp")
        with spec.sections() as sections:
            prep = sections.prep
            prep.insert(0, "%gpgverify -d0 -s1 -k2")


if __name__ == "__main__":
    main()
