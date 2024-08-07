#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Unpack archive and verify licenses

set -euo pipefail

verify_license=$(readlink -f "../../../contrib/verify-license.sh")
here="$(pwd)"

# Run first with the standard path
"${verify_license}"
# Run again in a temporary directory with unpacked sources
temp="$(mktemp -d)"
trap 'rm -rf "${temp}"' EXIT
name="fzf-0.46.1"
tar -C "${temp}" -xf "./${name}.tar.gz"
tar -C "${temp}" -xf "./${name}-vendor.tar.bz2"
cd "${temp}"
GO_VENDOR_LICENSE_HOME="${here}" GO_VENDOR_LICENSE_DIR="./${name}" "${verify_license}"
cd "${name}"
GO_VENDOR_LICENSE_HOME="${here}" GO_VENDOR_LICENSE_DIR=./ "${verify_license}"
