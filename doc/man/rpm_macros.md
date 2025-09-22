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

#### Example

```spec
%install
[...]
# Install into the main package's license directory
%go_vendor_license_install
# Or: Install into subpackage foo's license directory
%go_vendor_license_install -n %{name}-foo
```

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
# Or: Test a custom license expression
%go_vendor_license_check -c %{S:2} GPL-2.0-or-later AND MIT
```

#### Arguments

- `%*` — SPDX license expression. Defaults to `%{LICENSE}`.

### `%gocheck2`

!!! warning
    This is an experimental macro added in v0.9.0 and may move to the
    go-rpm-macros project or be subject to other breaking changes in the future.

This macro is a GO111MODULE-enabled replacement for `%gocheck` with roughly
the same interface.

The `%gocheck2` macro does not read the `%goipath` variable or support `-z`
options like `%gocheck` did.
Instead, gocheck2 honors go.mod files and reads the import path from the go.mod
file in the current directory.
Additionally, gocheck2 will find any go.mod files in subdirectories of the
current working directory and run tests for any of these "submodules" found in
the project, unless `-F` is passed.

#### Options

- `-d PATH` — Exclude the files contained in PATH *non-recursively*.
  Can be repeated.
  This accepts either an import path or a path relative to the go import path of
  the go.mod in the current directory.
  Using a full import path is recommended.
- `-t PATH` — Exclude the files contained in PATH *recursively*.
  Can be repeated.
  This accepts either an import path or a path relative to the go import path of
  the go.mod in the current directory.
  Using a full import path is recommended.
- `-s TEST_NAME_REGEX` — Skip test names that match a regex.
  This is passed to `go test -skip` and can be repeated.
  When repeated, values are joined with `|` (regex alternation operator) and
  passed on to `-skip` as a single value.
  (New in `%gocheck2`)
- `-F` — Don't find go.mod files in subdirectories. See description above.
  (New in `%gocheck2`)

#### Arguments

- `-- EXTRA_ARG...` — To pass extra arguments directly to `go test`, add them
  after a `--` separator.

#### Examples

``` spec
# Basic usage
%gocheck2

# Exclude everything under %{goipath}/e2e
# (Assumes goipath has already been defined)
%gocheck2 -t %{goipath}/e2e

# Exclude everything under the e2e directory,
assuming that CWD is the root of the current Go module.
# Using the syntax in the previous example is recommended.
%gocheck2 -t e2e

# Skip specific tests in addition to the e2e tree
%gocheck2 -t e2e -s TestSomething -s TestSomethingElse

# Skip several tests.
# The name of the ignores macro is not significant; it can be named anything.
%global ignores %{shrink:
    -s TestSomething
    -s TestSomethingElse
    -s TestSomethingElse1
    -s TestSomethingElse2
    -s TestSomethingElse3
}
%gocheck2 %{ignores}

# Pass extra arguments (-v in this case) directly to go test
%gocheck2 -- -v
```

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
