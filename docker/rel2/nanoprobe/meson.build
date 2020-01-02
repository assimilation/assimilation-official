# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
#
# We build nanoprobe semi-statically:
# $ ldd nanoprobe
#	linux-vdso.so.1 (0x00007ffe8a8da000)
#	libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x00007f81a9024000)
#	libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f81a8c33000)
#	/lib64/ld-linux-x86-64.so.2 (0x00007f81a95b7000)
#
# We build libassimilationclient.so as a shared library so the CMA can load it dynamically.
# libassimilationclient.a:  current ar archive
# libassimilationclient.so: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV),
#                           dynamically linked,
#                           BuildID[sha1]=7dda6904186cada790484d6a6132d7e44cd3c2b4,
#                           with debug_info, not stripped
#
#
project('assimilation', 'c')
glib_static = dependency('glib-2.0', static: true)
glib_shared = dependency('glib-2.0', static: false)
shared_deps = [
    glib_shared,    # must appear before librt
    meson.get_compiler('c').find_library('libsodium', static: false),
    meson.get_compiler('c').find_library('libpcap', static: false),
    meson.get_compiler('c').find_library('libz', static: false),
    meson.get_compiler('c').find_library('rt', static: true),
]
static_deps = [
    glib_static,    # must appear before librt
    meson.get_compiler('c').find_library('libsodium', static: true),
    meson.get_compiler('c').find_library('libpcap', static: true),
    meson.get_compiler('c').find_library('libz', static: true),
    meson.get_compiler('c').find_library('rt', static: true),
]
include_dirs = include_directories('include')
clientsrc = [
    'clientlib/addrframe.c',
    'clientlib/arpdiscovery.c',
    'clientlib/assimobj.c',
    'clientlib/authlistener.c',
    'clientlib/cdp_min.c',
    'clientlib/childprocess.c',
    'clientlib/cmalib.c',
    'clientlib/compressframe.c',
    'clientlib/configcontext.c',
    'clientlib/cryptcurve25519.c',
    'clientlib/cryptframe.c',
    'clientlib/cstringframe.c',
    'clientlib/discovery.c',
    'clientlib/frame.c',
    'clientlib/frameset.c',
    'clientlib/fsprotocol.c',
    'clientlib/fsqueue.c',
    'clientlib/generic_tlv_min.c',
    'clientlib/gmainfd.c',
    'clientlib/hblistener.c',
    'clientlib/hbsender.c',
    'clientlib/intframe.c',
    'clientlib/ipportframe.c',
    'clientlib/jsondiscovery.c',
    'clientlib/listener.c',
    'clientlib/lldp_min.c',
    'clientlib/logsourcefd.c',
    'clientlib/misc.c',
    'clientlib/nanoprobe.c',
    'clientlib/netaddr.c',
    'clientlib/netgsource.c',
    'clientlib/netio.c',
    'clientlib/netioudp.c',
    'clientlib/nvpairframe.c',
    'clientlib/packetdecoder.c',
    'clientlib/pcap_GSource.c',
    'clientlib/pcap_min.c',
    'clientlib/proj_classes.c',
    'clientlib/reliableudp.c',
    'clientlib/replacement_funs.c',
    'clientlib/resourcecmd.c',
    'clientlib/resourcelsb.c',
    'clientlib/resourcenagios.c',
    'clientlib/resourceocf.c',
    'clientlib/resourcequeue.c',
    'clientlib/seqnoframe.c',
    'clientlib/signframe.c',
    'clientlib/switchdiscovery.c',
    'clientlib/tlvhelper.c',
    'clientlib/unknownframe.c',
]
serversrc = [
    'serverlib/cdp.c',
    'serverlib/dump.c',
    'serverlib/lldp.c',
]
include_dirs = 'include'
nanoprobe_sources = [serversrc, 'nanoprobe/nanomain.c']
static_clientlib = build_target('assimilationclient',
                    clientsrc,
                    target_type: 'static_library',
                    dependencies: static_deps,
                    include_directories: include_dirs
                    )
shared_clientlib = build_target('assimilationclient',
                    clientsrc,
                    target_type: 'shared_library',
                    dependencies: shared_deps,
                    include_directories: include_dirs
                    )
executable('nanoprobe',
    sources: nanoprobe_sources,
    dependencies: static_deps,
    link_with: static_clientlib,
    include_directories: include_dirs,
)
pkgconfig = import('pkgconfig')
pkgconfig.generate(libraries: [shared_deps, shared_clientlib],
                   subdirs: include_dirs,
                   name: 'libassimilationclient',
                   filebase: 'assimilationclient',
                   description: 'Assimilation client library'
                   )
