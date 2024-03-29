go_vendor_archive_override(1)

# NAME

*go_vendor_archive override* — Create reproducible Go vendor archives

# SYNOPSIS

*go_vendor_archive override* _[OPTIONS...]_ _IMPORT_PATH_ _VERSION_

# DESCRIPTION

Create dependency overrides in *go-vendor-tools.toml(5)*.
Packagers may need to override upstream dependencies for security or
Go-compatibility purposes.

# OPTIONS

_IMPORT_PATH_
	Go package path
_VERSION_
	Package version to use, including the *v* prefix
*--config* (required)
	Path to config file


# AUTHOR

go-vendor-tools is maintained by Maxwell G and the Fedora Go SIG
<golang@lists.fedoraproject.org>.
See <https://fedora.gitlab.io/sigs/go/go-vendor-tools> for more information
about go-vendor-tools.

# SEE ALSO

*go_vendor_archive(1)*, *go_vendor_archive_create(1)*,
*go-vendor-tools.toml(5)*

