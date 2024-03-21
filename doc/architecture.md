<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->
# Architecture

The Go Vendor Tools project has four main pieces:

- `go_vendor_archive` — this command creates an archive containing a Go
  `vendor/` directory for use in the specfile. The archive metadata is
  normalized so archives are reproducible.
- `go_vendor_license` — this command detects licenses within the project
  tree. It can create a license summary, a normalized SPDX expression, and
  install detected license files into a single directory for the main project
  and all vendored modules.
- RPM macros — the package ships with RPM macros that use the
  `go_vendor_license` command to verify the `License:` tag in the specfile and
  install license files into the package's directory in /usr/share/licenses.
- `go-vendor-license.toml` — settings for the two commands and the macros are
  specified in this shared configuration file.
