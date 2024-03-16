# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT
# License text: https://spdx.org/licenses/MIT

%global forgeurl https://gitlab.com/gotmax23/go-vendor-tools
%define tag v%{version}

Name:           go-vendor-tools
Version:        0.2.0
%forgemeta
Release:        1%{?dist}
Summary:        Tools for handling Go library vendoring in Fedora

# BSD-3-Clause: src/go_vendor_tools/archive.py
License:        MIT AND BSD-3-Clause
URL:            %{forgeurl}
Source0:        %{forgesource}

BuildArch:      noarch

BuildRequires:  python3-devel

Recommends:     (askalono-cli or trivy)


%description
go-vendor-tools provides tools and macros for handling Go library vendoring in
Fedora.


%prep
%autosetup -p1 %{forgesetupargs}


%generate_buildrequires
%pyproject_buildrequires -x test


%build
%pyproject_wheel


%install
%pyproject_install
# TODO(anyone): Use -l flag once supported by EL 9.
%pyproject_save_files go_vendor_tools

install -Dpm 0644 rpm/macros.go_vendor_tools -t %{buildroot}%{_rpmmacrodir}


%check
%pytest


%files -f %{pyproject_files}
%doc README.md
%doc NEWS.md
%license LICENSES/*
%{_bindir}/go_vendor*
%{_rpmmacrodir}/macros.go_vendor_tools

%pyproject_extras_subpkg -n go-vendor-tools all

%changelog
* Sat Mar 16 2024 Maxwell G <maxwell@gtmx.me> - 0.2.0-1
- Release 0.2.0.

* Sat Mar 09 2024 Maxwell G <maxwell@gtmx.me> - 0.1.0-1
- Release 0.1.0.

* Tue Mar 05 2024 Maxwell G <maxwell@gtmx.me> - 0.0.1-1
- Release 0.0.1.
