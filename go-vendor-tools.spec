# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT
# License text: https://spdx.org/licenses/MIT

Name:           go-vendor-tools
Version:        0.0.1
Release:        1%{?dist}
Summary:        Tools for handling Go library vendoring in Fedora

License:        MIT
URL:            https://sr.ht/~gotmax23/go-vendor-tools
%global furl    https://git.sr.ht/~gotmax23/go-vendor-tools
Source0:        %{furl}/refs/download/v%{version}/go-vendor-tools-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  gnupg2
BuildRequires:  python3-devel

Requires:       (askalono-cli or trivy)


%description
Tools for handling Go library vendoring in Fedora


%prep
%autosetup -p1


%generate_buildrequires
%pyproject_buildrequires -x test


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files go_vendor_tools

install -Dpm 0644 rpm/macros.go_vendor_tools -t %{buildroot}%{_rpmmacrodir}


%check
%pytest


%files -f %{pyproject_files}
%doc README.md
%license LICENSES/*
%{_bindir}/go_vendor*
%{_rpmmacrodir}/macros.go_vendor_tools

%pyproject_extras_subpkg -n go-vendor-tools all

%changelog
