<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->

# go-vendor-tools

[![CI Badge](https://gitlab.com/gotmax23/go-vendor-tools/badges/main/pipeline.svg)](https://gitlab.com/gotmax23/go-vendor-tools/-/commits/main)

Tools for handling Go library vendoring in Fedora

## Contributing

See the [issue tracker] and issues marked with `help-needed`, in particular,
for places to start with.
Tickets marked with `idea` are larger changes that may require refinement or
additional discussion.
Feel free to chime in on those issues with any thoughts or if you wish to work
on a solution.
You can also search the code base for `TODO(anyone)`.

This project's unit tests, integration tests, and linters are managed by the
`noxfile.py`.
Install `nox` with `dnf install` or `pipx install`.
Run the plain `nox` to run the baseline unit tests and linters.
Run `nox -e all` to additionally run integration tests and check code coverage.

[issue tracker]: https://gitlab.com/gotmax23/go-vendor-tools/-/issues

## Author

go-vendor-tools was authored by Maxwell G and is maintained by them and the
Fedora Go SIG.

## Architecture

The Go Vendor Tools project has four main pieces:

- `go_vendor_archive` — this command creates an archive containing a Go
  `vendor/` directory for use in the specfile. The archive metadata is
  normalized so archives are reproducible.
- `go_vendor_license` — this command detects licenses within the project
  tree. It can create a license summary, a normalized SPDX expression, and
  install detected license files into a single directory for the main project
  and all vendored modules.
- RPM macros --- the package ships with RPM macros that use the
  `go_vendor_license` command to verify the `License:` tag in the specfile and
  install license files into the package's directory in /usr/share/licenses.
- `go-vendor-license.toml` — settings for the two commands and the macros are
  specified in this shared configuration file.

## Example specfile

``` spec
# Generated by go2rpm 1.11.0 (and then modified)
%bcond_without check

# https://github.com/cupcakearmy/autorestic
%global goipath         github.com/cupcakearmy/autorestic
Version:                1.7.11

%gometa -L -f

%global common_description %{expand:
Config driven, easy backup cli for restic.}

Name:           autorestic
Release:        %autorelease
Summary:        Config driven, easy backup cli for restic

# NOTE: Generated with:
#   $ go_vendor_license -C <UNPACKED ARCHIVE> report expression
License:        Apache-2.0 AND BSD-2-Clause AND BSD-3-Clause AND MIT AND MPL-2.0
URL:            %{gourl}
Source0:        %{gosource}
# NOTE: Archive created with:
#   $ go_vendor_archive create -O autorestic-%%{version}-vendor.tar.xz \
#       autorestic-%%{version}.tar.gz
# NOTE: %%{archivename} is set by %%gometa and evaluates to
# NOTE: autorestic-%%{version} here
Source1:        %{archivename}-vendor.tar.xz

# NOTE: Be sure to depend on the go-vendor-tools package for macros
BuildRequires:  go-vendor-tools

%description %{common_description}

# NOTE: %%gopkg and %%gopkgfiles are not used here!

%prep
# NOTE: Unpacks primary source archive and removes any existing vendor directory
# NOTE: in the source archive so the one we generated is used.
%goprep -A
# NOTE: Special %%setup invocation to unpack the vendor archive on top of the
# NOTE: main archive.
# NOTE: * The 1 in "-a1" selects Source1.
# NOTE: * %%{forgesetupargs} is set by %%gometa and selects the directory name
# NOTE:   in which to unpack the secondary vendor archive.
%setup -q -T -D -a1 %{forgesetupargs}
%autopatch -p1

%generate_buildrequires
# NOTE: go-vendor-tools has its own macro to generate buildrequires needed to
# NOTE: run the license detector.
%go_vendor_license_buildrequires

%build
%gobuild -o %{gobuilddir}/bin/autorestic %{goipath}

%install
# NOTE: %%go_vendor_license_install copies all license files into the package's
# NOTE: license directory.
# NOTE: This includes the main specfile's license AND all vendored modules.
%go_vendor_license_install
install -m 0755 -vd                     %{buildroot}%{_bindir}
install -m 0755 -vp %{gobuilddir}/bin/* %{buildroot}%{_bindir}/

%check
# NOTE: %%go_vendor_license_check verifies that the SPDX expression in License:
# NOTE: matches the package contents.
%go_vendor_license_check
%if %{with check}
%gocheck
%endif

# NOTE: %%{go_vendor_license_filelist} includes the license files installed by
# NOTE: %%go_vendor_license_install
%files -f %{go_vendor_license_filelist}
%{_bindir}/autorestic


%changelog
%autochangelog
```

## Scenarios

This sections contains some common scenarios that may arise when managing Go
projects.

### Security updates

Example case: CVE-2024-24786 was released in `google.golang.org/protobuf` and
fixed in `v1.33.0`. We want to update package `foo.spec` to use the new
version. The go-vendor-tools configuration is stored in `go-vendor-tools.toml`.

1. Use the `go_vendor_archive override` command to set the dependency override
   in the configuration file.

    ``` bash
    go_vendor_archive override --config go-vendor-tools.toml google.golang.org/protobuf v1.33.0
    ```

2. Use the `go_vendor_archive create` command to re-generate the configuration file.

    ``` bash
    go_vendor_archive create --config go-vendor-tools.toml foo.spec
    ```
