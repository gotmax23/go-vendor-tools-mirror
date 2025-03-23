---

title: Configuration

---
<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->
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
2. askalono
3. scancode (uses the `scancode-toolkit` Python library)

If no detector is specified, `go_vendor_license` will attempt to load the first
available license detector from first to last in the above list.
`go_vendor_license` will error if neither `trivy`, `askalono`, nor
`scancode-toolkit` is installed.

#### `detector_config` (mapping of string to string)

> **CLI flag**: `--detector-config`

Key-value pairs that are passed to the detector backend.

##### askalono

- `multiple` — run `askalono detect` using the `--multiple` flag to allow
  license files that contain more than one license text within it.
  This is disabled by default, as `--multiple` causes some licenses that are
  detected without `--multiple` to no longer be detected.

    ``` toml
    [licensing.detector_config]
    multiple = "true"
    ```

    or

    ``` bash
    go_vendor_archive --detector-config multiple=true
    ```

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

The configuration for `go_vendor_archive` is stored under the `archive` table.

#### `use_module_proxy` (boolean)

> **Default**: `true`
>
> **Environment variable**: `GO_VENDOR_ARCHIVE_USE_MODULE_PROXY`

Whether to use the Google Go module proxy to download modules.
Downloading modules manually is quite slow, so—unless you have privacy
concerns—using the module proxy is recommended.

#### `pre_commands` (list of list of strings)

Commands to run in the temporary source tree used to create the archive before
downloading the vendored dependencies.

For example, to remove unneeded files from the source tree so its dependencies are
not included in the vendor archive:

``` toml
[archive]
pre_commands = [
    ["rm", "-rf", "hacking"],
    ["echo", "Another command to show that multiple commands can be run here"],
]
```

#### `post_commands` (list of list of strings)

Commands to run after downloading the vendored dependencies.
Changes made to the `vendor` directory will be reflected in the final vendor
archive.

For example, this can be used to add missing license files to the archive.
`go_vendor_license` checks to make sure that each Go module has a license file,
but sometimes projects may include license files in subdirectories.
You can use `post_commands` to copy the license file from the subdirectory into
the parent directory where `go_vendor_license` expects to find this file:

``` toml
[archive]
post_commands = [
    [
        "cp", "-p",
        "vendor/github.com/golangci/gofmt/goimports/LICENSE",
        "vendor/github.com/golangci/gofmt/LICENSE"
    ],
    ["echo", "Another command to show that multiple commands can be run here"],
]
```

#### `tidy` (boolean)

> **Default**: `true`

Whether to run `go tidy` before `go mod vendor` when creating the archive.
You should leave this enabled.

#### `dependency_overrides` (string mapping)

See [*Security updates*](./scenarios.md#security-updates).

#### `compression_type` (string)

> **CLI flag**: `--compression`

Compression type, such as `tar` (uncompressed), `gz`, `bz2`, or `zstd`.
By default, the compression type is detected based on the extension of
`--output` passed on the CLI.

#### compresslevel (int)

> **Environment variable**: `GO_VENDOR_ARCHIVE_COMPRESSLEVEL`
>
> **CLI flag**: `--compresslevel`

Compression level as an integer for compression algorithms that support the
setting

[^1]: This is done for security reasons. `pre_commands` and `post_commands` can
    run arbitrary code, so we do not want to blindly load configuration from
    the current working directory.
