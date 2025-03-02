# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Generated by go2rpm 1.10.0
# https://github.com/cupcakearmy/autorestic
%global goipath         github.com/cupcakearmy/autorestic
Version:                1.7.11

%gometa -L -f

%global common_description %{expand:
Config driven, easy backup cli for restic.}

Name:           test-autorestic
Release:        1%{?dist}
Summary:        Config driven, easy backup cli for restic

# Misorder on purpose to make sure the license simplification logic works
License:        MPL-2.0 AND Apache-2.0 AND (Apache-2.0 AND MIT) AND BSD-2-Clause AND BSD-3-Clause AND MIT
URL:            %{gourl}
Source0:        %{gosource}
Source1:        autorestic-%{version}-vendor.tar.xz
Source2:        go-vendor-tools.toml
Source3:        expected-licenses.list
Source4:        scancode_go-vendor-tools.toml

BuildRequires:  go-vendor-tools
# For %%{python3_version}
BuildRequires:  python3-devel

%description %{common_description}

%prep
%goprep -A
%setup -q -T -D -a1 %{forgesetupargs}
%autopatch -p1

%generate_buildrequires
# Explicitly specify askalono for testing purposes
(%{go_vendor_license_buildrequires -c %{S:2}}) | tee buildrequires
if [ "${NO_SCANCODE-}" != "true" ]; then
    (%{go_vendor_license_buildrequires -c %{S:4}}) | tee buildrequires2
fi

%build
%global gomodulesmode GO111MODULE=on
%gobuild -o autorestic %{goipath}

%install
install -Dpm 0755 -t %{buildroot}%{_bindir} autorestic
%go_vendor_license_install -c %{S:2}
# TODO(gotmax23): Better support for multiple license files
# (this is needed by this contrived test case and, for example, packages with multiple
# vendor archives)
if [ "${NO_SCANCODE-}" != "true" ]; then
    %global go_vendor_license_filelist licenses.list.scancode
    %go_vendor_license_install -c %{S:4}
    %global go_vendor_license_filelist licenses.list
fi

%check
%go_vendor_license_check -c %{S:2}
diff -u "%{S:3}" "$(pwd)/licenses.list"
test "$(cat buildrequires)" = "trivy"

if [ "${NO_SCANCODE-}" != "true" ]; then
    %go_vendor_license_check -c %{S:4}
    diff -u "%{S:3}" "$(pwd)/licenses.list.scancode"
    test "$(cat buildrequires2)" = "go-vendor-tools+scancode"
fi

%if %{with check}
%gocheck
%endif

%files -f %{go_vendor_license_filelist}
%doc docs CHANGELOG.md DEVELOPMENT.md README.md
%{_bindir}/autorestic

%changelog
* Thu Feb 29 2024 Maxwell G <maxwell@gtmx.me> - 1.7.11-1
- Initial package
