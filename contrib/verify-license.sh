#!/bin/bash
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Unpack archive and verify licenses

set -euo pipefail

_path="$(command -v go_vendor_license 2>/dev/null || :)"
_default_path="pipx run --spec ../../../[specfile] go_vendor_license"
GO_VENDOR_LICENSE="${GO_VENDOR_LICENSE:-${_path:-${_default_path}}}"
IFS=" " read -r -a command <<< "${GO_VENDOR_LICENSE}"


set -x
license_home="${GO_VENDOR_LICENSE_HOME:-"$(pwd)"}"
license="$(rpmspec -q --srpm --qf "%{LICENSE}\n" "${license_home}"/*.spec)"
set +x
if [ -n "${GO_VENDOR_CONFIG-}" ]; then
    command+=("--config" "${GO_VENDOR_CONFIG}")
elif [ -f "${license_home}/go-vendor-tools.toml" ]; then
    command+=("--config" "${license_home}/go-vendor-tools.toml")
fi
set -x
license_path="${GO_VENDOR_LICENSE_DIR:-"$(echo "${license_home}"/*.spec)"}"
# Ensure the stdout is also correct
gotten="$("${command[@]}" -C "${license_path}" report expression --write-json report.json)"
python -c 'from go_vendor_tools.licensing import compare_licenses; import sys; assert compare_licenses(*sys.argv[1:])' "${license}" "${gotten}"
