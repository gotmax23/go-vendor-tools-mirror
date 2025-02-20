go_vendor_license(1)

# NAME

**go_vendor_license** —  Handle licenses for vendored go projects

# GLOBAL OPTIONS

See *go_vendor_license --help* or the rendered help page at
<https://fedora.gitlab.io//sigs/go/go-vendor-tools/man/go_vendor_license/>.

# SUBCOMMANDS

## report

Main subcommand to scan for licenses.

See *go_vendor_license report --help*.

## explicit

Add manual license entry to a config file when the detector backend cannot find the
license of a file.

See
<https://fedora.gitlab.io/sigs/go/go-vendor-tools/scenarios/#manually-detecting-licenses>.

# AUTHOR

go-vendor-tools is maintained by Maxwell G and the Fedora Go SIG
<golang@lists.fedoraproject.org>.
See <https://fedora.gitlab.io/sigs/go/go-vendor-tools> for more information
about go-vendor-tools.

# SEE ALSO

*go_vendor_archive(1)*, *go-vendor-tools.toml(5)*
