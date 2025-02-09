#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Unpack archive and verify licenses

set -euo pipefail

verify_license=$(readlink -f "../../../contrib/verify-license.sh")
here="$(pwd)"
export GO_VENDOR_LICENSE_HOME="${here}"

for GO_VENDOR_CONFIG in "${here}/go-vendor-tools.toml" "${here}/scancode_go-vendor-tools.toml"; do
    if [ "${GO_VENDOR_CONFIG}" = "${here}/scancode_go-vendor-tools.toml" ] && [ "${NO_SCANCODE-}" = "true" ]; then
        continue
    fi
    export GO_VENDOR_CONFIG
    # Run first with the standard path
    "${verify_license}"
    # Run again in a temporary directory with unpacked sources
    temp="$(mktemp -d)"
    trap 'rm -rf "${temp}"' EXIT
    name="autorestic-1.7.11"
    tar -C "${temp}" -xf "${here}/${name}.tar.gz"
    dest="${temp}/${name}"
    tar -C "${dest}" -xf "${here}/${name}-vendor.tar.xz"
    cd "${temp}"
    GO_VENDOR_LICENSE_DIR="./${name}" "${verify_license}"
    cd "${name}"
    GO_VENDOR_LICENSE_DIR=./ "${verify_license}"
    cd "${here}"
done
