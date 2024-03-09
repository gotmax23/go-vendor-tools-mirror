#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Unpack archive and verify licenses

set -euo pipefail

_path="$(command -v go_vendor_license 2>/dev/null || :)"
_default_path="pipx run --spec ../../../ go_vendor_license"
GO_VENDOR_LICENSE="${GO_VENDOR_LICENSE:-${_path:-${_default_path}}}"
IFS=" " read -r -a command <<< "${GO_VENDOR_LICENSE}"


license="$(rpmspec -q --qf "%{LICENSE}\n" ./*.spec | head -n1)"
if [ -f "go-vendor-tools.toml" ]; then
    command+=("--config" "$(pwd)/go-vendor-tools.toml")
fi
"${command[@]}" -C ./*.spec report all --verify "${license}"
