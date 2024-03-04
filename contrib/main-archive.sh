#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Create an archive for the main project

set -euo pipefail

_path="$(command -v fclogr 2>/dev/null || :)"
_default_path="pipx run --spec fclogr>=0.8.0 fclogr"
FCLOGR="${FCLOGR:-${_path:-${_default_path}}}"
IFS=" " read -r -a command <<< "${FCLOGR}"


"${command[@]}" dev-entries --archive "$@"
