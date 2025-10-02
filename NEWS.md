<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->

# NEWS

## 0.9.0 - 2025-10-02 <a id='0.9.0'></a>

### Added

- **Add `%gocheck2` helper as module-enabled `%gocheck` alternative (!58).**
  This addresses a major blocker preventing packagers from migrating their
  packages to use modules mode (`%global gomodulesmode GO111MODULE=on`).
  `%gocheck2` mostly preserves `%gocheck`'s behavior but also has functionality
  to skip individual tests (removing the need to maintain complex awk pipelines
  to add `t.Skip()` invocations to test functions).
  See the [gocheck2 documentation] for more information.
  Note that this is an experimental macro and may move to the go-rpm-macros
  project or be subject to other breaking changes in the future.
- license: allow `--autofill` when `--prompt` is not passed. This is useful for
  non-interactive usage of `go_vendor_archive`.
- Use the `tarfile.tar_filter` to unpack tar archives (#84).
- Add additional license file search patterns.

[gocheck2 documentation]: https://fedora.gitlab.io/sigs/go/go-vendor-tools/man/rpm_macros/#gocheck2

### Changed

- Make zstarfile dependency optional. The helper functions we use from zstarfile
  are now vendored. zstarfile is still pulled in via the `all` extra
  (or the `go-vendor-tools+all` RPM package), and it will be used to
  unpack `tar.zst` and `tar.lz4` archives if it's available.

### Removed

- Remove support for unpacking zip archives in `go_vendor_archive`.
  `go_vendor_license` has never supported zip archives and `go_vendor_archive`
  also only supports writing vendor archives as tar files, so adding extra
  complexity to keep zip archive support in this one place and also work around
  changes to the Python `tarfile` module was not deemed worthwhile.

## 0.8.0 - 2025-07-17 <a id='0.8.0'></a>

### Added

- **Add support for EPEL 9 and EPEL 10**
- Add support for non-root level go.mod paths (#60)
- archive: include go.mod and go.sum in go.work mode
- license: include `Li[cs]ense.*` glob when scanning for license files
- license: simplify manual license expressions from configuration
- license: implement [`--autofill` functionality][autofill]
- license: support `$NO_COLOR` and `$FORCE_COLOR` standards

[autofill]: https://fedora.gitlab.io/sigs/go/go-vendor-tools/man/go_vendor_license/#options_1

### Changed

- rpm: include full license breakdown in macro
- license: askalono is the new default backend and scancode-toolkit is used to autofill
  licenses that askalono couldn't detect (when `--autofill` is enabled, which
  will be the new default in go2rpm).

### Fixed

- license: improve handling of invalid license keys to print a proper error
  instead of raising an unhandled exception

## 0.7.0 - 2025-03-23 <a id='0.7.0'></a>

### Release summary

This is a pretty big release, consisting of several months of work.
There are no major breaking changes to the CLI or RPM macro interfaces,
but there are many improvements to the internal code.
These changes may result in:

- Additional errors due to undetected licenses that need to be manually
  specified (affects packages using the trivy backend)

- Changes to the generated License expression due to `LICENSE.docs` files in
  dependencies no longer being included in license detection (mainly affects
  packages using the askalono backend)

You can fix these errors by running the following command which will prompt for
any missing licenses and then update the License tag in the specfile if needed
(using the new `--update-spec` flag).

```bash
go_vendor_license --config go-vendor-tools.toml --path *.spec report --prompt --update-spec
```

### Added

**general:**

- Add dependency on `specfile` library.
  This dependency is technically optional (guarded by a `try:`/`except ImportError:`),
  so downstreams can patch the dependencies to remove this if need be.
- Add `scancode` python extra

**docs:**

- Add meta tag for site description
- Add `go_vendor_license` markdown docs
- Add manpage for `go_vendor_license`
- Document RPM macros
- config: document `pre_commands` and `post_commands`
- Enable search

**`go_vendor_license`:**

- Add `--update-spec` and `--verify-spec` flags to update or verify `License`
  tag of an existing specfile.
  This adds a dependency on `specfile`.
- Allow running `%go_vendor_license_install` without pulling in license detector
  backends.
  This only applies to the `askalono` and `scancode` backends.
- Implement `%go_vendor_license_check_disable` to disable license checking on a
  package- or distribution-wide level.
  This allows cutting out license detector dependencies so specfiles can still
  build when those are unpackaged (e.g., scancode on EPEL).
- Add support for REUSE-style `LICENSES` directory to license detection backend
  code.
- Add support for askalono `--multiple` flag via [`detector_config`][detector_config].
  This is not enabled by default, as multiple mode is apparently buggy and
  causes some previously detected licenses to no longer be detected.

[detector_config]: https://fedora.gitlab.io/sigs/go/go-vendor-tools/config/#detector_config-mapping-of-string-to-string

**packaging:**

- Run full test suite in `%check`

### Changed

**`go_vendor_license`:**

- Use consistent method to find license files for both `scancode` and
  `askalono`. This may cause some small changes to license expressions detected
  by the `askalono` backend.
- Exclude `LICENSE.docs` files from vendored dependencies when detecting
  licenses.
  The documentation from dependencies are not included in the compiled binary
  and thus do not affect the license and should not be included in the
  calculated expression.
  This helps avoid situations where CC licenses that are approved for
  documentation and not code end up in the License tag and cause extra work for
  packagers.
- `go_vendor_license_install` now errors when invalid license overrides exist in
  the configuration file.
- While the schema for the `--write-json` report is undocumented, note that the
  `scancode_license_data` key in the scancode license report has changed from a
  list of dictionaries to a dictionary mapping path names to the scancode
  license dictionary.
- trivy: verify all license files found by searching the filesystem that trivy
  does not detect itself are marked as undetected.
- trivy: exclude .sh files from license map
  (https://gitlab.com/fedora/sigs/go/go-vendor-tools/-/issues/65).
- Require `AUTHORS`, `NOTICE`, and `PATENTS` files to be uppercased.
  This prevents files like `notice.go` being included in the license detection.

### Fixed

**docs:**

- README: remove incorrect Fedora EPEL reference

**`go_vendor_archive`:**

- archive create: don't leave empty archive file if creation fails

**`go_vendor_license`**:

- `--prompt` should imply `--write-config`.
  Otherwise, the information from prompting is thrown away.
- `--verify` (and the newly added `--verify-spec`) no longer error if the existing
  `License` tag in the specfile cannot be parsed as a valid expression.
  It just fails verification.
- `LicenseRef-Scancode-Public-Domain` is now normalized to
  `LicenseRef-Fedora-Public-Domain`.
- scancode: properly handle undetected licenses. Previously, scancode would
  return None for undetected licenses and this would cause tracebacks.

### Removed

**docs:**

- Remove outdated example specfile.
  This is now covered by go2rpm.

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
