#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

set -euo pipefail

path="$(command -v go_vendor_archive 2>/dev/null || :)"
command=()
if [ -n "${path}" ]; then
    command=("${path}")
else
    command=("pipx" "run" "--spec" "../../../" "go_vendor_archive")
fi


spectool -g ./*.spec
ls
source0="$(spectool ./*.spec | grep Source0 | awk '{print $2}' | xargs -d'\n' basename)"
source1="$(spectool ./*.spec | grep Source1 | awk '{print $2}')"
"${command[@]}" -O "${source1}" "$@" "${source0}"
sha512sum -c CHECKSUMS
