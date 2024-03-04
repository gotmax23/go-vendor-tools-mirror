#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Unpack archive and verify licenses

set -euo pipefail

_path="$(command -v go_vendor_license 2>/dev/null || :)"
_default_path="pipx run --spec ../../../ go_vendor_license"
GO_VENDOR_LICENSE="${GO_VENDOR_LICENSE:-${_path-${_default_path}}}"
IFS=" " read -r -a command <<< "${GO_VENDOR_LICENSE}"


rm -rf .unpack
mkdir .unpack
license="$(rpmspec -q --qf "%{LICENSE}\n" ./*.spec | head -n1)"
rpmbuild \
    -D '_sourcedir %(pwd)' \
    -D '_srcrpmdir %(pwd)' \
    -D '_specdir %(pwd)' \
    -D '_builddir %(pwd)/.unpack' \
    --nodeps \
-bp ./*.spec
if [ -f "go-vendor-tools.toml" ]; then
    command+=("--config" "$(pwd)/go-vendor-tools.toml")
fi
rm -rf .unpack/*SPECPARTS
cd .unpack/*
rm -rf _build
if [ -f ".gitignore" ]; then
    sed -i '/vendor/d' .gitignore
fi
"${command[@]}" report all --verify "${license}"
