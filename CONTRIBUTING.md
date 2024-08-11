<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->

# Contributing

## What issues can I work on?

See the [issue tracker] and issues marked with `help-wanted`, in particular,
for places to start with.
Tickets marked with `idea` are larger changes that may require refinement or
additional discussion.
Feel free to chime in on those issues with any thoughts or if you wish to work
on a solution.
You can also search the code base for `TODO(anyone)`.

## How do I run unit tests?

This project's unit tests, integration tests, and linters are managed by the
`noxfile.py`.
Install `nox` with `dnf install` or `pipx install`.
Run the plain `nox` to run the baseline unit tests and linters.
Run `nox -e all` to additionally run integration tests and check code coverage.

## How do I test go-vendor-tools locally?

``` bash
sudo dnf copr enable @go-sig/go-vendor-tools-dev
sudo dnf upgrade go-vendor-tools go2rpm
```

## How do I test go-vendor-tools in mock?

``` bash
copr mock-config @go-sig/go-vendor-tools fedora-rawhide-x86_64
fedpkg --release rawhide mockbuild
```

[issue tracker]: https://gitlab.com/gotmax23/go-vendor-tools/-/issues
