# RPM Macros

`go-vendor-tools` ships with RPM macros that use the go_vendor_license command to
verify the License: tag in the specfile and install license files into the
package's directory in `/usr/share/licenses`.

!!! note
    In this document, the macro `%{S:2}` will be used to represent the path to
    the `go-vendor-tools.toml` file.
    In the go2rpm specfile template, this file is always included as `Source2`.

## Callable macros

### Shared options

All callable macros accept the following flags, unless otherwise noted.
See the [go_vendor_license](./go_vendor_license.md) documentation for more
information on each flag.

- `-c`: Specify path to `go-vendor-tools.toml` configuration file
- `-d`:  Choose a specific license detector backend
- `-D` : Specify detector settings as `KEY=VALUE` pairs.

### `%go_vendor_license_buildrequires`

Generate requirements needed for the selected license backend.

#### Example

``` spec
%generate_buildrequires
%go_vendor_license_buildrequires -c %{S:2}
```

### `%go_vendor_license_install`

Install all license files of both the main package and vendored sources into
the package's license directory.

This default license directory is `%{_defaultlicensedir}/NAME` where `NAME`
is the name of the main package.
`NAME` can be overridden when the license files need to be installed into a
subpackage's license directory by passing `-n`.

#### Options

In addition to the shared options:

- `-n` — name of the subdirectory of `/usr/share/licenses/`. Defaults to `%{NAME}`.

### `%{go_vendor_license_filelist}`

This macro contains a path to the filelist created by
`%go_vendor_license_install` that contains all license files.

#### Example

``` spec
%files -f %{go_vendor_license_filelist}
```

### `%go_vendor_license_check`

Ensure the license expression is equivalent to what the go_vendor_licenses tool
expects.
By default, the macro will compare the value of `%{LICENSE}`, the value of the
`License:` tag of the main package.
This can be customized by passing a custom license expression.

#### Example

``` spec
%check
%go_vendor_license_check -c %{S:2}
# Test a custom license expression
%go_vendor_license_check -c %{S:2} GPL-2.0-or-later AND MIT
```

#### Arguments

- `%*` — SPDX license expression. Defaults to `%{LICENSE}`.

## Variable macros

### `%__go_vendor_license`

Path to the `go_vendor_license` binary.
You shouldn't need to touch this.

### `%go_vendor_license_check_disable`

!!! info
    Added in v0.7.0

Set this macro to `1` to disable `%go_vendor_license_check` (it will expand to
nothing in this mode) and make sure that `%go_vendor_license_buildrequires` only
installs the dependencies for `%go_vendor_license_install`.

This can be used in a conditional with the scancode backend which is not
available in EPEL or on 32-bit systems.

#### Example

`go2rpm` includes the following when scancode is enabled to disable license
checking on if license checking has been disabled globally, on RHEL, or on i386:

``` spec
# scancode has a lot of dependencies, so it can be disabled for a faster build
# or when its deps are unavailable.
%if %{defined rhel} || "%{_arch}" == "i386"
%global go_vendor_license_check_disable 1
%endif
```
