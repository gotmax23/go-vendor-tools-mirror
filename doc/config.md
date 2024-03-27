---
title: Configuration
---
<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->

# Configuration

go-vendor-tools stores its configuration in a TOML file.
Conventionally, this file is named `go-vendor-tools.toml`,
but this is not a requirement;
go-vendor-tools does not automatically load configuration[^1],
so it is up to the user to explicitly pass `--config go-vendor-tools.toml`.

## Schema

The following sections outline the configuration options.
All fields are optional.

### `licensing`

`go_vendor_license`'s configuration is stored under the `licensing` table.

#### `detector` (string)

> **Environment variable**: `GO_VENDOR_LICENSE_DETECTOR`

Explicitly choose a license detector.
Currently supported detectors are:

1. trivy
2. askalono`

If no detector is specified, `go_vendor_license` will attempt to load the first
available license detector from first to last in the above list.
`go_vendor_license` will error if neither `trivy` nor `askalono` is installed.

#### `licenses` (list of license entry tables)

License detectors are not perfect.
The `detector.licenses` list allows packagers to manually specify license files
to include in the license calculation.

- `path` (string) — relative path to a license file
- `sha256sum` (string) — sha256 checksum of the license file.
  This ensures that packagers re-check the license when the file's contents
  change.
- `expression` (string) — valid SPDX expression containing the file's
  contents

See [*Manually detecting licenses*](./scenarios.md#manually-detecting-licenses).

#### `exclude_files` (list of strings)

List of license file paths to exclude from the licensing calculation

#### `exclude_directories` (list of strings)

List of directories to ignore when scanning for license files

### `archive`

The configuration for `go_vendor_archive` is stored under the `archive` table`.

#### `use_module_proxy` (boolean)

> **Default**: `true`
>
> **Environment variable**: `GO_VENDOR_ARCHIVE_USE_MODULE_PROXY`

Whether to use the Google Go module proxy to download modules.
Downloading modules manually is quite slow, so—unless you have privacy
concerns—using the module proxy is recommended.

#### `pre_commands` and `post_commands` (list of list of strings)

TODO

#### `tidy` (boolean)

> **Default**: `true`

Whether to run `go tidy` before `go mod vendor` when creating the archive.
You should leave this enabled.

#### `dependency_overrides` (string mapping)

See [*Security updates*](./scenarios.md#security-updates).

[^1]: This is done for security reasons. `pre_commands` and `post_commands` can
    run arbitrary code, so we do not want to blindly load configuration from
    the current working directory.
