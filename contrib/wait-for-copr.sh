#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

set -euo pipefail

if [ -z "${COPR_OWNER-}" ]; then
    echo "COPR_OWNER is not defined. Proceeding..."
    exit 0
fi

evr="$(pipx run fclogr dev-entries --evr-only)"
wait-for-copr \
    --owner "${COPR_OWNER}" --project "${COPR_PROJECT}" \
    go-vendor-tools "${evr}"
