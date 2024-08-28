<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->

# NEWS

## 0.6.0 - 2024-08-28 <a id='0.6.0'></a>

### Added

**Documentation:**

- CONTRIBUTING: add additional sections about testing
- README: add note about project stability
- scenarios: document how to manually update specfile for new upstream version
  (from Brad Smith)

**`go_vendor_archive`**

- create: add support for go workspaces

**`go_vendor_license`**

- **Add `scancode-toolkit`-based backend.**
  See the [warning in the docs] before using.
- `report --write-json`: use pretty formatting for JSON
- install: include `PATENTS` in installed license files

[warning in the docs]: https://fedora.gitlab.io/sigs/go/go-vendor-tools/config/#detector-string

### Fixed

**`go_vendor_license`**

- all: exit with proper error code when no backends are available
- all: allow users to pass either relative or absolute paths to `--path` and
  improve testing of this functionality
- report: fix printing of undetected licenses.
- `report --write-config`: work around bug with old tomlkit versions

**rpm:**

- all: use `%{go_vendor_license_filelist}` in the other macros

## 0.5.1 - 2024-04-11 <a id='0.5.1'></a>

- `go_vendor_archive create`: don't override manually specified `--output`

## 0.5.0 - 2024-04-11 <a id='0.5.0'></a>

### Added

- `cli`: add argcomplete-generated shell completions

### Fixed

- `doc scenarios`: fix outdated info about go2rpm profile
- `go_vendor_archive`: fix broken `--help` message

## 0.4.0 - 2024-04-10 <a id='0.4.0'></a>

See the notes for 0.4.0b1.

## 0.4.0b1 - 2024-04-10 <a id='0.4.0b1'></a>

### Added

- `cli`: support compression algorithms other than `xz` (#7, #45)
- `doc`: add manpages for go_vendor_archive commands (#40)
- `go_vendor_archive create`: add `--idempotent` flag
- `go_vendor_archive create`: add `--write-config` flag
- `go_vendor_archive create`: add missing `--no-use-module-proxy` flag to
    disable default `--use-module-proxy`.
- `go_vendor_archive create`: change default output file to `vendor.tar.bz2`
    (#7, #46)
- `go_vendor_archive create`: handle projects without any dependencies (#29)

### Fixed

- `doc config`: fix markdown syntax error
- `doc config`: remove stray backtick in archive section
- `go_vendor_license install`: properly own intermediate directories

## 0.3.0 - 2024-03-28 <a id='0.3.0'></a>

### Added

- `LICENSES`: add Copyright
- `doc`: add documentation site at
  <https://fedora.gitlab.io/sigs/go/go-vendor-tools>
- `go_vendor_license`: sort license installation filelist

### Changed

- `config archive`: make `use_module_proxy` the default
  (https://gitlab.com/fedora/sigs/go/go-vendor-tools/-/issues/25)

### Fixed

- `license_detection`: avoid double license validation
- `packaging`: fix project URLs in Python metadata

### Miscellaneous documentation changes

- `doc README`: add Copr status badge
- `doc Scenarios`: add Manually detecting licenses
- `doc Scenarios`: document generating specfiles with go2rpm
- `doc Scenarios`: flesh out manual license detection section
- `doc`: add CONTRIBUTING.md
- `doc`: add Configuration page
- `doc`: add news to mkdocs site
- `doc`: fix more em dashes to use proper unicode ligatures
- `doc`: fix sentence syntax in Scenarios section
- `docs scenarios`: add explicit section id #manually-detecting-licenses

## 0.2.0 - 2024-03-16 <a id='0.2.0'></a>

### Added

- `doc`: use unicode em dashes
- `license_detection`: add `extra_license_files` field
- `packaging`: add `NEWS.md` to `%doc`

### Changed

- `gomod`: require that the parent module has a license file

### Fixed

- `all`: remove unnecessary shebangs on non-executable files
- `doc` `Scenarios`: fix security update example command
- `doc`: add missing `%setup` `-q` flag to example specfile
- `go_vendor_license --prompt`: fix path handling
- `licensing`: fix SPDX expression simplification code

## 0.1.0 - 2024-03-09 <a id='0.1.0'></a>

### Added

- `doc`: add Contributing and Author sections
- `doc`: update `%prep` section in example specfile to use `%goprep` and remove
  existing vendor directory if it exists in the upstream sources
- `go_vendor_archive`: add support for overriding dependency versions.
- `go_vendor_archive`: allow detecting file names from specfile Sources
- `go_vendor_license report`: add `--write-config` and `--prompt` flags
- `go_vendor_license`: log which license detector is in use
- `go_vendor_license`: support automatically unpacking and inspecting archives
- `go_vendor_license`: support detecting archive to unpack and inspect from
  specfile Sources
- `license_detection`: allow dumping license data as JSON
- `license_detection`: fix handling of licenses manually specified in the
  configuration
- `licensing`: allow excluding licenses from SPDX calculation
- `packaging`: add maintainers data to python package metadata
- `packaging`: flesh out package description
- `rpm`: add `%go_vendor_license_buildrequires` macro

### Changed

- `go_vendor_archive`: move archive creation functionality into a `create`
  subcommand
- `go_vendor_archive`: run `go mod tidy` by default

### Fixed

- `all`: properly handle relative and absolute paths throughout the codebase
- `go_vendor_license`: do not print colored text to stdout when it is not a tty
- `go_vendor_license`: fix test for missing modules.txt
- `license_detection trivy`: handle when no licenses are detected
- `license_detection`: add missing `__init__.py` file
- `license_detection`: improve filtering of unwanted paths

## 0.0.1 - 2024-03-05 <a id='0.0.1'></a>

Initial release
