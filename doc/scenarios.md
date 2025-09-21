<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->

<!-- pyml disable-num-lines 111 code-block-style -->

# Scenarios

## Generate specfile with go2rpm {: #generate-go2rpm}

Example case: You wish to package `github.com/opencontainers/runc` using
vendored dependencies.

go2rpm versions 1.12.0 and later ship with a `vendor` profile that integrates
with go-vendor-tools.

1. Generate the base specfile

    ```bash
    go2rpm --profile vendor -d github.com/opencontainers/runc --name runc
    ```

    This command will create a `runc` directory with the specfile, the
    downloaded upstream source archive, and the vendor tarball generated with
    `go_vendor_archive`.
    `go2rpm` will also output a license report and a cumulative SPDX expression
    generated with `go_vendor_license` and then update the License tag in the specfile.
    It is the packager's responsibility to perform a basic check of the output
    and ensure adherence to the Fedora Licensing Guidelines,
    including ensuring that all keys in the `License` tag are allowed licenses
    in Fedora.

1. Fill in missing license expressions.
    The `go2rpm` command above will prompt the packager to fill in any missing
    license expressions and then update the generated `go-vendor-tools.toml` file.
    For each license file that the license detector failed to match,
    the packager can either enter the license expression or enter `EXCLUDE` to
    add an entry to `go-vendor-tools.toml` to exclude that file from license
    detection.

    !!! note
        The `EXCLUDE` option was added in v0.7.0.

1. Ensure that the final license only includes licenses allowed under the Fedora
   Licensing Guidelines.

## Security updates {: #security-updates}

Example case: CVE-2024-24786 was released in `google.golang.org/protobuf` and
fixed in `v1.33.0`. We want to update package `foo.spec` to use the new
version. The go-vendor-tools configuration is stored in `go-vendor-tools.toml`.

1. Use the `go_vendor_archive override` command to set the dependency override
    in the configuration file.

    ```bash
    go_vendor_archive override --config go-vendor-tools.toml google.golang.org/protobuf v1.33.0
    ```

1. Use the `go_vendor_archive create` command to re-generate the configuration file.

    ```bash
    go_vendor_archive create --config go-vendor-tools.toml foo.spec
    ```

## Manually detecting licenses {: #manually-detecting-licenses}

Example case: `go_vendor_license report` fails to detect a license
`vendor/github.com/google/shlex`. You will have to manually specify the license
in `go-vendor-tools.toml`.

1. Unpack the source and vendor archives and change into the directory.

    ```bash
    fedpkg prep
    cd <UNPACKED ARCHIVE>
    rm -rf _build
    ```

1. Identify the module's license file and determine its SPDX identifier

    - First, check the module directory for a license file

        ```bash
        ls vendor/github.com/google/shlex
        [...]
        COPYING
        [...]
        ```

    - The SPDX identifier was determined to be `Apache-2.0`.

1. Use the `go_vendor_license explicit` command to add the license entry to the
    configuration file.

    ```bash
    go_vendor_license --config ../go-vendor-tools.toml explicit -f vendor/github.com/google/shlex/COPYING Apache-2.0
    ```

1. The configuration file should now have the following block

    ```toml
    [[licensing.licenses]]
    path = "vendor/github.com/google/shlex/COPYING"
    sha256sum = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
    expression = "Apache-2.0"
    ```

1. You can now rerun the `go_vendor_license report` subcommand to determine the
    license expression.

    ```bash
    go_vendor_license --config ../go-vendor-tools.toml report expression
    ```

    Fill the outputted license expression into the specfile's `License:` field.

## Manually update specfile for new upstream version {: #manual-update}

Example case: Upstream has released version 1.10.1 of foo.
go2rpm was used to generate the original specfile using vendored dependencies.
`go-vendor-tools.toml` is the configuration file for `go_vendor_archive`.

!!! tip
    Consider [re-generating a new specfile with `go2rpm`](#generate-go2rpm)
    instead of updating an existing one to pick up go2rpm template
    improvements.

1. In the project directory containing `foo.spec` and `go-vendor-tools.toml`,
    update the Version to 1.10.1 in the spec file.

1. Retrieve the new v1.10.1 source archive from upstream.

    ```bash
    spectool -g foo.spec
    ```

1. Generate the vendor archive from the v1.10.1 source archive.

    ```bash
    go_vendor_archive create --config go-vendor-tools.toml foo.spec
    ```

    or

    ```bash
    go_vendor_archive create -c go-vendor-tools.toml foo.spec
    ```

1. Verify the license expression in the specfile.

    ```bash
    go_vendor_license --config go-vendor-tools.toml --path foo.spec \
        report --update-spec --prompt --autofill=auto
    ```

    or

    ```bash
    go_vendor_license -c go-vendor-tools.toml -C foo.spec \
        report --update-spec --prompt --autofill=auto
    ```

    This command will perform a license scan, prompt for any licenses the
    selected license backend cannot detect, and autofill any that can be
    automatically detected using a secondary license backend.
    Make sure to double check any changes and ensure that all keys in the
    `License` tag are allowed licenses in Fedora.

    Alternatively, you may use the `--verify-spec` argument to fail
    if there have been any changes from the `License` tag specified in the
    specfile.
    This approach is recommended when using Packit or another automated
    mechanism to update packages.

    ```bash
    go_vendor_license --config go-vendor-tools.toml --path foo.spec report --verify-spec
    ```

    This command will error out if the detected license expression has changed
    so that the package maintainer can double check the changes and update the
    `License:` tag in the specfile.

1. Continue with your normal package update workflow, preform a test build, and
   upload the new sources to the lookaside cache.
