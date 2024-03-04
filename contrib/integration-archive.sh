#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Create an archive for a tests/integration specfile

set -euo pipefail

_path="$(command -v go_vendor_archive 2>/dev/null || :)"
_default_path="pipx run --spec ../../../ go_vendor_archive"
GO_VENDOR_ARCHIVE="${GO_VENDOR_ARCHIVE:-${_path-${_default_path}}}"
IFS=" " read -r -a command <<< "${GO_VENDOR_ARCHIVE}"


spectool -g ./*.spec
ls
source0="$(spectool ./*.spec | grep Source0 | awk '{print $2}' | xargs -d'\n' basename)"
source1="$(spectool ./*.spec | grep Source1 | awk '{print $2}')"
if [ -f "go-vendor-tools.toml" ]; then
    command+=("--config" "$(pwd)/go-vendor-tools.toml")
fi
time "${command[@]}" -O "${source1}" "$@" "${source0}"
sha512sum -c CHECKSUMS
