#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT
set -euo pipefail

uv pip install -e '.[all,dev]' -e '../go2rpm[all]' scancode-toolkit
