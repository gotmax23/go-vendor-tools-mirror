#!/bin/bash -x
# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT
set -euo pipefail

uv pip install -c constraints.txt -e '.[all,dev]' -e '../go2rpm[all]' scancode-toolkit ipython fedrq libdnf5-shim pytest-cov
