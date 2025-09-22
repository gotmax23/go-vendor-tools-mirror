#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Unpack archive and verify licenses

set -euo pipefail

verify_license=$(readlink -f "../../../contrib/verify-license.sh")
here="$(pwd)"
_path="$(command -v go_vendor_license 2>/dev/null || :)"
_default_path="pipx run --spec '../../../[scancode,specfile]' go_vendor_license"
GO_VENDOR_LICENSE="${GO_VENDOR_LICENSE:-${_path:-${_default_path}}}"
IFS=" " read -r -a command <<< "${GO_VENDOR_LICENSE}"
temp="$(mktemp -d)"
trap 'rm -rf "${temp}"' EXIT

# Run first with the standard path
"${verify_license}"
# Use --verify-spec
"${command[@]}" --path ./*.spec report --verify-spec
cp "fzf.spec.wrong-license" "${temp}/fzf2.spec"
ln -sr ./*.tar* "${temp}"
# Try to verify an invalid spec
(! "${command[@]}" --path "${temp}/fzf2.spec" report --verify-spec)
# Update invalid spec
"${command[@]}" --path "${temp}/fzf2.spec" report --update-spec
diff -u "fzf.spec" "${temp}/fzf2.spec"
(cd "${temp}" && rm -r ./*)
# Run again in a temporary directory with unpacked sources
name="fzf-0.46.1"
tar -C "${temp}" -xf "./${name}.tar.gz"
tar -C "${temp}" -xf "./${name}-vendor.tar.bz2"
cd "${temp}"
GO_VENDOR_LICENSE_HOME="${here}" GO_VENDOR_LICENSE_DIR="./${name}" "${verify_license}"
cd "${name}"
GO_VENDOR_LICENSE_HOME="${here}" GO_VENDOR_LICENSE_DIR=./ "${verify_license}"
cd "${here}"
