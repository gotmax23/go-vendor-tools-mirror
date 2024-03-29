go_vendor_archive(1)

# NAME

**go_vendor_archive** — Create reproducible Go vendor archives

# SYNOPSIS

**go_vendor_archive** *SUBCOMMAND* *[...]*

# SUBCOMMANDS

## create
	*go_vendor_archive create* _[OPTIONS...]_ _PATH_

Reproducibly create Go vendor archives.
See *go_vendor_archive_create(1)*.

## override
	*go_vendor_archive override* _[OPTIONS...]_ _IMPORT_PATH_ _VERSION_

Create dependency overrides in *go-vendor-tools.toml(5)*.
Packagers may need to override upstream dependencies for security or
Go-compatibility purposes.
See *go_vendor_archive_override(1)*.

# AUTHOR

go-vendor-tools is maintained by Maxwell G and the Fedora Go SIG
<golang@lists.fedoraproject.org>.
See <https://fedora.gitlab.io/sigs/go/go-vendor-tools> for more information
about go-vendor-tools.

# SEE ALSO

*go_vendor_archive_create(1)*, *go_vendor_archive_override(1)*,
*go-vendor-tools.toml(5)*
