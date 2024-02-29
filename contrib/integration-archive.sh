#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

set -euo pipefail

spectool -g ./*.spec
ls
source0="$(spectool ./*.spec | grep Source0 | awk '{print $2}' | xargs -d'\n' basename)"
source1="$(spectool ./*.spec | grep Source1 | awk '{print $2}')"
pipx run --spec ../../../ go_vendor_archive \
    -O "${source1}" "$@" "${source0}"
sha512sum -c CHECKSUMS
