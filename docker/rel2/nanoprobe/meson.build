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
version = '2.0.0'

dirdelim = '/'
share = '/usr/share/assimilation' + dirdelim
crypto_dir = share + dirdelim + 'crypto.d'
neo4j_creds = crypto_dir + dirdelim + 'neo4j.creds'

best_practices  = share + 'best_practices'
queries  = share + 'queries'
monrules  = share + 'monrules'
notification_d = share + 'notification.d'
neo4j_creds  = share + 'neo4j.creds'
cc = meson.get_compiler('c')


glib_static = dependency('glib-2.0', static: true)
glib_shared = dependency('glib-2.0', static: false)
librt_static = cc.find_library('rt', static: true)
librt_shared = cc.find_library('rt', static: false)
shared_deps = [
    glib_shared,    # must appear before librt
    cc.find_library('libsodium', static: false),
    cc.find_library('libpcap', static: false),
    cc.find_library('libz', static: false),
    librt_shared,
]
static_deps = [
    glib_static,    # must appear before librt
    cc.find_library('libsodium', static: true),
    cc.find_library('libpcap', static: true),
    cc.find_library('libz', static: true),
    librt_static,
]

config_data = configuration_data({
    'PUBKEYSUFFIX': '".pub"',
    'PRIVATEKEYSUFFIX': '".secret"',
    'CMAADDR': '"224.0.2.5:1984"',
    'NANOLISTENADDR': '"0.0.0.0:1984"',
    'CMAUSERID': '"assimilation"',
    'CMAINITFILE': '"/etc/cma.conf"',
    # Are these header files present?
    'HAVE_UNISTD_H':    cc.has_header('unistd.h'),
    'HAVE_SYS_SOCKET_H': cc.has_header('sys/socket.h'),
    'HAVE_SYS_TYPES_H': cc.has_header('sys/types.h'),
    'HAVE_SYS_UTSNAME_H': cc.has_header('sys/utsname.h'),
    'HAVE_FCNTL_H': cc.has_header('fcntl.h'),
    'HAVE_MCHECK_H': cc.has_header('mcheck.h'),
    'HAVE_NETDB_H': cc.has_header('netdb.h'),
    'HAVE_ZLIB_H': cc.has_header('zlib.h', required: true),
    'HAVE_SODIUM_H': cc.has_header('sodium.h', required: true),

    # Are these functions present?
    'HAVE_CLOCK_GETTIME': cc.has_function('clock_gettime',
                                          dependencies: librt_static
                                          ),
    'HAVE_ENDPROTOENT': cc.has_function('endprotoent'),
    'HAVE_FCNTL': cc.has_function('fcntl'),
    'HAVE_G_GET_REAL_TIME': cc.has_function('g_get_real_time', # needs glib2 >=2.28
                                            dependencies: glib_shared),
    'HAVE_G_GET_MONOTONIC_TIME': cc.has_function('g_get_monotonic_time', # needs glib2 >=2.28
                                                dependencies: glib_shared),
    'HAVE_G_GET_ENVIRON': cc.has_function('g_get_environ', # needs glib2 >=2.28
                                          dependencies: glib_shared),
    'HAVE_GETADDRINFO': cc.has_function('getaddrinfo'),
    'HAVE_GETCOMPUTERNAME': cc.has_function('getcomputername'),
    'HAVE_GETEUID': cc.has_function('geteuid'),
    'HAVE_KILL': cc.has_function('kill'),
    'HAVE_MCHECK': cc.has_function('mcheck'),
    'HAVE_MCHECK_PEDANTIC': cc.has_function('mcheck_pedantic'),
    'HAVE_SETPGID': cc.has_function('setpgid'),
    'HAVE_SIGACTION': cc.has_function('sigaction'),
    'HAVE_UNAME': cc.has_function('uname'),
    }
)
# Things the C code needs
config_data.set_quoted('VERSION_STRING', version)
config_data.set_quoted('DIRDELIM', dirdelim)
config_data.set_quoted('DISCOVERY_DIR', share + 'discovery_agents')
config_data.set_quoted('CRYPTKEYDIR', crypto_dir)
# Things only the Python code needs
config_data.set_quoted('BPINSTALL_DIR', best_practices)
config_data.set_quoted('MONRULEINSTALL_DIR', monrules)
config_data.set_quoted('NOTIFICATION_SCRIPT_DIR', notification_d)
config_data.set_quoted('NEO4JCREDFILENAME', neo4j_creds)
config_data.set_quoted('QUERYINSTALL_DIR', queries)

# Create project_common.h from project_common.h.in
common = configure_file(input: 'include/projectcommon.h.in',
                        output: 'projectcommon.h',
                        configuration: config_data,
                        format: 'cmake',
                        )

# Generate frametypes.h and framesettypes.h using cma/frameinfo.py
prog_python = import('python').find_installation('python3')
frameinfo = find_program('cma/frameinfo.py')
frame_types = custom_target('frametypes',
                              output: ['frametypes.h'],
                              input: 'cma/frameinfo.py',
                              command: [prog_python, '@INPUT@', 'frametypes', '@OUTPUT@'],
                              )
frame_set_types = custom_target('framesettypes',
                              output: ['framesettypes.h'],
                              input: 'cma/frameinfo.py',
                              command: [prog_python, '@INPUT@', 'framesettypes', '@OUTPUT@'],
                              )

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
    frame_types,
    frame_set_types,
]
serversrc = [
    'serverlib/cdp.c',
    'serverlib/dump.c',
    'serverlib/lldp.c',
    frame_types,
    frame_set_types,
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
