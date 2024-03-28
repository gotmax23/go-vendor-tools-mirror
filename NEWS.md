<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->

# NEWS

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
