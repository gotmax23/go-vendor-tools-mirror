# Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
# SPDX-License-Identifier: MIT

# Generated by go2rpm 1.10.0
# https://github.com/junegunn/fzf
%global goipath         github.com/junegunn/fzf
Version:                0.46.1
%global tag             %{version}

%gometa -f

%global common_description %{expand:
:cherry_blossom: A command-line fuzzy finder.}

Name:           test-fzf
Release:        1%{?dist}
Summary:        :cherry_blossom: A command-line fuzzy finder

%if %{undefined el9}
SourceLicense:  MIT
%endif
License:        Apache-2.0 AND BSD-3-Clause AND MIT
URL:            %{gourl}
Source0:        %{gosource}
Source1:        fzf-%{version}-vendor.tar.xz
Source2:        expected-licenses.list

BuildRequires:  go-vendor-tools

%description %{common_description}

%prep
%autosetup -p1 -b1 %{forgesetupargs}
%goprep -ke

%generate_buildrequires
%go_vendor_license_buildrequires

%build
%dnl We don't care about building or installing the package for the purposes of
%dnl the integration test.
%dnl %gobuild -o fzf %{goipath}
%global debug_package %{nil}

%install
# Check go_vendor_license_buildrequires
(%{go_vendor_license_buildrequires -d askalono}) | tee buildrequires
test "$(cat buildrequires)" = "askalono-cli"
(%{go_vendor_license_buildrequires -d trivy}) | tee buildrequires
test "$(cat buildrequires)" = "trivy"
# Specify -n manually for testing purposes
%go_vendor_license_install -n not-fzf

%check
%go_vendor_license_check

diff -u %{S:2} licenses.list

%files -f %{go_vendor_license_filelist}
%doc doc ADVANCED.md BUILD.md CHANGELOG.md README-VIM.md README.md

%changelog
* Thu Feb 29 2024 Maxwell G <maxwell@gtmx.me> - 0.46.1-1
- Initial package
