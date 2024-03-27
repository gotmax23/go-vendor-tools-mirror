<!--
Copyright (C) 2024 Maxwell G <maxwell@gtmx.me>
SPDX-License-Identifier: MIT
-->
# Scenarios

## Generate specfile with go2rpm

Example case: You wish to package `github.com/opencontainers/runc` using
vendored dependencies.

Once support for go-vendor-tools is merged into go2rpm, you will be able to
generate a specfile with the vendor profile with the following command

1. Generate the base specfile

    ``` bash
    go2rpm --profile vendor -d --no-clean github.com/opencontainers/runc --name runc
    ```

    This command will create a `runc` directory with the specfile, the
    downloaded upstream source archive, and the vendor tarball generated with
    `go_vendor_archive`.
    `go2rpm` will also output a license report and a cummulative SPDX expression
    generated with `go_vendor_license`.
    It is the packager's responsibility to perform a basic check of the output
    and manually determine the SPDX expression for packages listed as
    incompatible.

2. Open up the specfile in an editor and replace the `License` field with the
   expression that `go2rpm` outputs.


## Security updates

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

## Manually detecting licenses {: #manually-detecting-licenses}

Example case: `go_vendor_license report` fails to detect a license
`vendor/github.com/google/shlex`. You will have to manually specify the license
in `go-vendor-tools.toml`.

1. Unpack the source and vendor archives and change into the directory.

    ``` bash
    fedpkg prep
    cd <UNPACKED ARCHIVE>
    rm -rf _build
    ```

2. Identify the module's license file and determine its SPDX identifier

    - 
        ``` bash
        ls vendor/github.com/google/shlex
        [...]
        COPYING
        [...]
        ```
    - The SPDX identifier was determined to be `Apache-2.0`.

3. Use the `go_vendor_license explicit` command to add the license entry to the
   configuration file.

    ``` bash
    go_vendor_license --config ../go-vendor-tools.toml explicit -f vendor/github.com/google/shlex/COPYING Apache-2.0
    ```

4. The configuration file should now have the following block

    ``` toml
    [[licensing.licenses]]
    path = "vendor/github.com/google/shlex/COPYING"
    sha256sum = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
    expression = "Apache-2.0"
    ```
5. You can now rerun the `go_vendor_license report` subcommand to determine the
   license expression.

    ``` bash
    go_vendor_license --config ../go-vendor-tools.toml report expression
    ```

    Fill the outputted license expression into the specfile's `License:` field.
