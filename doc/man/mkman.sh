#!/bin/bash
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

US="$(readlink -f "${0}")"
HERE="$(dirname "${US}")"
generator="scdoc"
preview_cmd=("man" "-l")

buildman() {
    input="${1}"
    output="${1%.scd}"
    if [ "${generator}" = "scdoc" ]; then
        (set -x; scdoc <"${input}" >"${output}")
    elif [ "${generator}" = "scd2md" ]; then
        (set -x; releaserr scd2md "${input}" --output-dir "${HERE}")
        output="${output//./}.md"
        preview_cmd=("less")
    else
        echo "Invalid generator: ${generator}"
        exit 1
    fi
}

pages=()

preview=""
while getopts "pn:g:" "OPT"; do
    case "${OPT}" in
        p)
            preview="true"
            ;;
        n)
            pages=("${HERE}/${OPTARG}.scd")
            ;;
        g)
            generator="${OPTARG}"
            ;;
        *)
            echo "Invalid arg ${OPT}"
            exit 1
            ;;
    esac
done
shift "$((OPTIND-1))"

if [ "$#" -gt 0 ]; then
    pages=("$@")
elif [ "${#pages[@]}" -eq 0 ]; then
    pages=("${HERE}"/*.[0-9].scd)
fi

for page in "${pages[@]}"; do
    buildman "${page}"
    if [ "${preview}" = "true" ]; then
        "${preview_cmd[@]}" "${output}"
        exit
    fi
done
