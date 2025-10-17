#!/usr/bin/bash -x
# Copyright (C) 2025 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

set -euo pipefail
found=""
temp=$(mktemp)
trap 'rm -f $temp' EXIT TERM INT
for rpm in "$@"; do
    if test "$(rpm -qp --qf="%{NAME}\n" "$rpm")" != "test-fzf"; then
        continue
    fi
    found=1
    rpm -qp --provides "$rpm" | grep -E '^bundled\(golang\(.*\)\) = [^ -]+$' | sort -u | tee "$temp"
    diff -u ./expected-provides.list "$temp"
    break
done

if test -z "$found"; then
    echo "Failed to find built RPM"
    exit 1
fi
