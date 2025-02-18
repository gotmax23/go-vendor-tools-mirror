go_vendor_archive_create(1)

# NAME

*go_vendor_archive create* — Create reproducible Go vendor archives

# SYNOPSIS

*go_vendor_archive create* _[OPTIONS...]_ _PATH_

# OPTIONS

_PATH_
	Path for which to create a vendor archive.

	Can be one of the following:

	. Go source tree with a *go.mod* file
	. Path to a (compressed) tar archive
	. Path to a specfile. *SOURCE0* will automatically be unpacked.

*--config* _PATH_
	Path to config file
*--write-config*
	After creating the archive, write out a config file based on the CLI
	options
*-O* _OUTPUT_, *--output* _OUTPUT_
	Output path for the vendored tarball.
	When _PATH_ is a specfile (and python3-specfile is installed),
	the name of *SOURCE1* will be used as the
	output if one is not explicitly specified.
	Otherwise, *./vendor.tar.bz2* is the default.
*-p* / *--use-module-proxy*, *--no-use-module-proxy*
	Whether to use the Google Go module proxy.
	Defaults to *true* or whatever is set in *go-vendor-tools.toml*.
*-I*, *--idempotent*
	Only generate archive if _OUTPUT_ does not already exist
*--compression* _COMPRESSION TYPE_
	Compression type, such as _tar_ (uncompressed), _gz_, _bz2_, or _zstd_.
	By default, the compression type is detected based on _OUTPUT_'s
	extension.
*--compresslevel* _COMPRESSLEVEL_ (int)
	Compression level as an integer for compression algorithms that support
	the setting

# AUTHOR

go-vendor-tools is maintained by Maxwell G and the Fedora Go SIG
<golang@lists.fedoraproject.org>.
See <https://fedora.gitlab.io/sigs/go/go-vendor-tools> for more information
about go-vendor-tools.

# SEE ALSO

*go_vendor_archive(1)*, *go_vendor_archive_override(1)*,
*go-vendor-tools.toml(5)*
