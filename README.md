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
