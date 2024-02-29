#!/usr/bin/bash
# Copyright (C) 2023 Maxwell G <maxwell@gtmx.me>
#
# SPDX-License-Identifier: MIT

# USAGE EXAMPLES:
# 1.
#   ./rpmeval.sh \
#       -D 'forgeurl https://git.sr.ht/~gotmax23/forge-srpm-macros'
#       -E '%forgemeta -v'
# 2.
#   RPM=rpmspec ./rpmeval.sh -P package.spec

set -euo pipefail

HERE="$(dirname "$(readlink -f "${0}")")"
_macro_dir="${HERE}/rpm"
MACRO_DIR="${MACRO_DIR-"${_macro_dir}"}"
args=(${RPM:-rpm})
if [ -n "${MACRO_DIR}" ]; then
    _default_macros_dir="$(rpm --showrc | grep 'Macro path' | awk -F ': ' '{print $2}')"
    args+=("--macros" "${_default_macros_dir}:${MACRO_DIR}/macros.*")
fi

exec "${args[@]}" "$@"
