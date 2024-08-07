#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Unpack archive and verify licenses

set -euo pipefail

_path="$(command -v go_vendor_license 2>/dev/null || :)"
_default_path="pipx run --spec ../../../ go_vendor_license"
GO_VENDOR_LICENSE="${GO_VENDOR_LICENSE:-${_path:-${_default_path}}}"
IFS=" " read -r -a command <<< "${GO_VENDOR_LICENSE}"


license_home="${GO_VENDOR_LICENSE_HOME:-"$(pwd)"}"
license="$(rpmspec -q --qf "%{LICENSE}\n" "${license_home}"/*.spec | head -n1)"
if [ -f "${license_home}/go-vendor-tools.toml" ]; then
    command+=("--config" "${license_home}/go-vendor-tools.toml")
fi
license_path="${GO_VENDOR_LICENSE_DIR:-"$(echo ./*.spec)"}"
# Ensure the stdout is also correct
gotten="$("${command[@]}" -C "${license_path}" report expression --write-json report.json)"
python -c 'from go_vendor_tools.licensing import compare_licenses; import sys; assert compare_licenses(*sys.argv[1:])' "${license}" "${gotten}"
