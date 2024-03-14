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

%if %{undefined el9}
SourceLicense:  Apache-2.0
%endif
# Misorder on purpose to make sure the license simplification logic works
License:        MPL-2.0 AND Apache-2.0 AND (Apache-2.0 AND MIT) AND BSD-2-Clause AND BSD-3-Clause AND MIT
URL:            %{gourl}
Source0:        %{gosource}
Source1:        autorestic-%{version}-vendor.tar.xz
Source2:        go-vendor-tools.toml
Source3:        expected-licenses.list

BuildRequires:  go-vendor-tools

%description %{common_description}

%prep
%goprep -A
%setup -q -T -D -a1 %{forgesetupargs}
%autopatch -p1

%generate_buildrequires
(%{go_vendor_license_buildrequires -c %{S:2}}) | tee buildrequires

%build
%global gomodulesmode GO111MODULE=on
%gobuild -o autorestic %{goipath}

%install
install -Dpm 0755 -t %{buildroot}%{_bindir} autorestic
# Explicitly specify askalono for testing purposes
%go_vendor_license_install -c %{S:2} -d askalono -D askalono_path=/usr/bin/askalono

%check
%go_vendor_license_check -c %{S:2} -d askalono -D askalono_path=/usr/bin/askalono
diff -u licenses.list %{S:3}
test "$(cat buildrequires)" = "askalono-cli"
%if %{with check}
%gocheck
%endif

%files -f %{go_vendor_license_filelist}
%doc docs CHANGELOG.md DEVELOPMENT.md README.md
%{_bindir}/autorestic

%changelog
* Thu Feb 29 2024 Maxwell G <maxwell@gtmx.me> - 1.7.11-1
- Initial package
