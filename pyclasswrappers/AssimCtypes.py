'''Wrapper for address_family_numbers.h

Generated with:
/usr/local/bin/ctypesgen.py -o pyclasswrappers/AssimCtypes.py -l libclientlib.so -L ../../bin/clientlib/ -I include -I/usr/include/glib-2.0 -I/usr/lib/i386-linux-gnu/glib-2.0/include include/address_family_numbers.h include/addrframe.h include/cdp.h include/cstringframe.h include/decode_packet.h include/discovery.h include/frameformats.h include/frame.h include/frameset.h include/generic_tlv_min.h include/hblistener.h include/hbsender.h include/intframe.h include/lldp.h include/netaddr.h include/netgsource.h include/netio.h include/netioudp.h include/pcap_GSource.h include/pcap_min.h include/proj_classes.h include/projectcommon.h include/seqnoframe.h include/server_dump.h include/signframe.h include/switchdiscovery.h include/tlvhelper.h include/tlv_valuetypes.h include/unknownframe.h

Do not modify this file.
'''

__docformat__ =  'restructuredtext'

# Begin preamble

import ctypes, os, sys
from ctypes import *

_int_types = (c_int16, c_int32)
if hasattr(ctypes, 'c_int64'):
    # Some builds of ctypes apparently do not have c_int64
    # defined; it's a pretty good bet that these builds do not
    # have 64-bit pointers.
    _int_types += (c_int64,)
for t in _int_types:
    if sizeof(t) == sizeof(c_size_t):
        c_ptrdiff_t = t
del t
del _int_types

class c_void(Structure):
    # c_void_p is a buggy return type, converting to int, so
    # POINTER(None) == c_void_p is actually written as
    # POINTER(c_void), so it can be treated as a real pointer.
    _fields_ = [('dummy', c_int)]

def POINTER(obj):
    p = ctypes.POINTER(obj)

    # Convert None to a real NULL pointer to work around bugs
    # in how ctypes handles None on 64-bit platforms
    if not isinstance(p.from_param, classmethod):
        def from_param(cls, x):
            if x is None:
                return cls()
            else:
                return x
        p.from_param = classmethod(from_param)

    return p

class UserString:
    def __init__(self, seq):
        if isinstance(seq, basestring):
            self.data = seq
        elif isinstance(seq, UserString):
            self.data = seq.data[:]
        else:
            self.data = str(seq)
    def __str__(self): return str(self.data)
    def __repr__(self): return repr(self.data)
    def __int__(self): return int(self.data)
    def __long__(self): return long(self.data)
    def __float__(self): return float(self.data)
    def __complex__(self): return complex(self.data)
    def __hash__(self): return hash(self.data)

    def __cmp__(self, string):
        if isinstance(string, UserString):
            return cmp(self.data, string.data)
        else:
            return cmp(self.data, string)
    def __contains__(self, char):
        return char in self.data

    def __len__(self): return len(self.data)
    def __getitem__(self, index): return self.__class__(self.data[index])
    def __getslice__(self, start, end):
        start = max(start, 0); end = max(end, 0)
        return self.__class__(self.data[start:end])

    def __add__(self, other):
        if isinstance(other, UserString):
            return self.__class__(self.data + other.data)
        elif isinstance(other, basestring):
            return self.__class__(self.data + other)
        else:
            return self.__class__(self.data + str(other))
    def __radd__(self, other):
        if isinstance(other, basestring):
            return self.__class__(other + self.data)
        else:
            return self.__class__(str(other) + self.data)
    def __mul__(self, n):
        return self.__class__(self.data*n)
    __rmul__ = __mul__
    def __mod__(self, args):
        return self.__class__(self.data % args)

    # the following methods are defined in alphabetical order:
    def capitalize(self): return self.__class__(self.data.capitalize())
    def center(self, width, *args):
        return self.__class__(self.data.center(width, *args))
    def count(self, sub, start=0, end=sys.maxint):
        return self.data.count(sub, start, end)
    def decode(self, encoding=None, errors=None): # XXX improve this?
        if encoding:
            if errors:
                return self.__class__(self.data.decode(encoding, errors))
            else:
                return self.__class__(self.data.decode(encoding))
        else:
            return self.__class__(self.data.decode())
    def encode(self, encoding=None, errors=None): # XXX improve this?
        if encoding:
            if errors:
                return self.__class__(self.data.encode(encoding, errors))
            else:
                return self.__class__(self.data.encode(encoding))
        else:
            return self.__class__(self.data.encode())
    def endswith(self, suffix, start=0, end=sys.maxint):
        return self.data.endswith(suffix, start, end)
    def expandtabs(self, tabsize=8):
        return self.__class__(self.data.expandtabs(tabsize))
    def find(self, sub, start=0, end=sys.maxint):
        return self.data.find(sub, start, end)
    def index(self, sub, start=0, end=sys.maxint):
        return self.data.index(sub, start, end)
    def isalpha(self): return self.data.isalpha()
    def isalnum(self): return self.data.isalnum()
    def isdecimal(self): return self.data.isdecimal()
    def isdigit(self): return self.data.isdigit()
    def islower(self): return self.data.islower()
    def isnumeric(self): return self.data.isnumeric()
    def isspace(self): return self.data.isspace()
    def istitle(self): return self.data.istitle()
    def isupper(self): return self.data.isupper()
    def join(self, seq): return self.data.join(seq)
    def ljust(self, width, *args):
        return self.__class__(self.data.ljust(width, *args))
    def lower(self): return self.__class__(self.data.lower())
    def lstrip(self, chars=None): return self.__class__(self.data.lstrip(chars))
    def partition(self, sep):
        return self.data.partition(sep)
    def replace(self, old, new, maxsplit=-1):
        return self.__class__(self.data.replace(old, new, maxsplit))
    def rfind(self, sub, start=0, end=sys.maxint):
        return self.data.rfind(sub, start, end)
    def rindex(self, sub, start=0, end=sys.maxint):
        return self.data.rindex(sub, start, end)
    def rjust(self, width, *args):
        return self.__class__(self.data.rjust(width, *args))
    def rpartition(self, sep):
        return self.data.rpartition(sep)
    def rstrip(self, chars=None): return self.__class__(self.data.rstrip(chars))
    def split(self, sep=None, maxsplit=-1):
        return self.data.split(sep, maxsplit)
    def rsplit(self, sep=None, maxsplit=-1):
        return self.data.rsplit(sep, maxsplit)
    def splitlines(self, keepends=0): return self.data.splitlines(keepends)
    def startswith(self, prefix, start=0, end=sys.maxint):
        return self.data.startswith(prefix, start, end)
    def strip(self, chars=None): return self.__class__(self.data.strip(chars))
    def swapcase(self): return self.__class__(self.data.swapcase())
    def title(self): return self.__class__(self.data.title())
    def translate(self, *args):
        return self.__class__(self.data.translate(*args))
    def upper(self): return self.__class__(self.data.upper())
    def zfill(self, width): return self.__class__(self.data.zfill(width))

class MutableString(UserString):
    """mutable string objects

    Python strings are immutable objects.  This has the advantage, that
    strings may be used as dictionary keys.  If this property isn't needed
    and you insist on changing string values in place instead, you may cheat
    and use MutableString.

    But the purpose of this class is an educational one: to prevent
    people from inventing their own mutable string class derived
    from UserString and than forget thereby to remove (override) the
    __hash__ method inherited from UserString.  This would lead to
    errors that would be very hard to track down.

    A faster and better solution is to rewrite your program using lists."""
    def __init__(self, string=""):
        self.data = string
    def __hash__(self):
        raise TypeError("unhashable type (it is mutable)")
    def __setitem__(self, index, sub):
        if index < 0:
            index += len(self.data)
        if index < 0 or index >= len(self.data): raise IndexError
        self.data = self.data[:index] + sub + self.data[index+1:]
    def __delitem__(self, index):
        if index < 0:
            index += len(self.data)
        if index < 0 or index >= len(self.data): raise IndexError
        self.data = self.data[:index] + self.data[index+1:]
    def __setslice__(self, start, end, sub):
        start = max(start, 0); end = max(end, 0)
        if isinstance(sub, UserString):
            self.data = self.data[:start]+sub.data+self.data[end:]
        elif isinstance(sub, basestring):
            self.data = self.data[:start]+sub+self.data[end:]
        else:
            self.data =  self.data[:start]+str(sub)+self.data[end:]
    def __delslice__(self, start, end):
        start = max(start, 0); end = max(end, 0)
        self.data = self.data[:start] + self.data[end:]
    def immutable(self):
        return UserString(self.data)
    def __iadd__(self, other):
        if isinstance(other, UserString):
            self.data += other.data
        elif isinstance(other, basestring):
            self.data += other
        else:
            self.data += str(other)
        return self
    def __imul__(self, n):
        self.data *= n
        return self

class String(MutableString, Union):

    _fields_ = [('raw', POINTER(c_char)),
                ('data', c_char_p)]

    def __init__(self, obj=""):
        if isinstance(obj, (str, unicode, UserString)):
            self.data = str(obj)
        else:
            self.raw = obj

    def __len__(self):
        return self.data and len(self.data) or 0

    def from_param(cls, obj):
        # Convert None or 0
        if obj is None or obj == 0:
            return cls(POINTER(c_char)())

        # Convert from String
        elif isinstance(obj, String):
            return obj

        # Convert from str
        elif isinstance(obj, str):
            return cls(obj)

        # Convert from c_char_p
        elif isinstance(obj, c_char_p):
            return obj

        # Convert from POINTER(c_char)
        elif isinstance(obj, POINTER(c_char)):
            return obj

        # Convert from raw pointer
        elif isinstance(obj, int):
            return cls(cast(obj, POINTER(c_char)))

        # Convert from object
        else:
            return String.from_param(obj._as_parameter_)
    from_param = classmethod(from_param)

def ReturnString(obj, func=None, arguments=None):
    return String.from_param(obj)

# As of ctypes 1.0, ctypes does not support custom error-checking
# functions on callbacks, nor does it support custom datatypes on
# callbacks, so we must ensure that all callbacks return
# primitive datatypes.
#
# Non-primitive return values wrapped with UNCHECKED won't be
# typechecked, and will be converted to c_void_p.
def UNCHECKED(type):
    if (hasattr(type, "_type_") and isinstance(type._type_, str)
        and type._type_ != "P"):
        return type
    else:
        return c_void_p

# ctypes doesn't have direct support for variadic functions, so we have to write
# our own wrapper class
class _variadic_function(object):
    def __init__(self,func,restype,argtypes):
        self.func=func
        self.func.restype=restype
        self.argtypes=argtypes
    def _as_parameter_(self):
        # So we can pass this variadic function as a function pointer
        return self.func
    def __call__(self,*args):
        fixed_args=[]
        i=0
        for argtype in self.argtypes:
            # Typecheck what we can
            fixed_args.append(argtype.from_param(args[i]))
            i+=1
        return self.func(*fixed_args+list(args[i:]))

# End preamble

_libs = {}
_libdirs = ['../../bin/clientlib/']

# Begin loader

# ----------------------------------------------------------------------------
# Copyright (c) 2008 David James
# Copyright (c) 2006-2008 Alex Holkner
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of pyglet nor the names of its
#    contributors may be used to endorse or promote products
#    derived from this software without specific prior written
#    permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------

import os.path, re, sys, glob
import ctypes
import ctypes.util

def _environ_path(name):
    if name in os.environ:
        return os.environ[name].split(":")
    else:
        return []

class LibraryLoader(object):
    def __init__(self):
        self.other_dirs=[]

    def load_library(self,libname):
        """Given the name of a library, load it."""
        paths = self.getpaths(libname)

        for path in paths:
            if os.path.exists(path):
                return self.load(path)

        raise ImportError("%s not found." % libname)

    def load(self,path):
        """Given a path to a library, load it."""
        try:
            # Darwin requires dlopen to be called with mode RTLD_GLOBAL instead
            # of the default RTLD_LOCAL.  Without this, you end up with
            # libraries not being loadable, resulting in "Symbol not found"
            # errors
            if sys.platform == 'darwin':
                return ctypes.CDLL(path, ctypes.RTLD_GLOBAL)
            else:
                return ctypes.cdll.LoadLibrary(path)
        except OSError,e:
            raise ImportError(e)

    def getpaths(self,libname):
        """Return a list of paths where the library might be found."""
        if os.path.isabs(libname):
            yield libname
        else:
            # FIXME / TODO return '.' and os.path.dirname(__file__)
            for path in self.getplatformpaths(libname):
                yield path

            path = ctypes.util.find_library(libname)
            if path: yield path

    def getplatformpaths(self, libname):
        return []

# Darwin (Mac OS X)

class DarwinLibraryLoader(LibraryLoader):
    name_formats = ["lib%s.dylib", "lib%s.so", "lib%s.bundle", "%s.dylib",
                "%s.so", "%s.bundle", "%s"]

    def getplatformpaths(self,libname):
        if os.path.pathsep in libname:
            names = [libname]
        else:
            names = [format % libname for format in self.name_formats]

        for dir in self.getdirs(libname):
            for name in names:
                yield os.path.join(dir,name)

    def getdirs(self,libname):
        '''Implements the dylib search as specified in Apple documentation:

        http://developer.apple.com/documentation/DeveloperTools/Conceptual/
            DynamicLibraries/Articles/DynamicLibraryUsageGuidelines.html

        Before commencing the standard search, the method first checks
        the bundle's ``Frameworks`` directory if the application is running
        within a bundle (OS X .app).
        '''

        dyld_fallback_library_path = _environ_path("DYLD_FALLBACK_LIBRARY_PATH")
        if not dyld_fallback_library_path:
            dyld_fallback_library_path = [os.path.expanduser('~/lib'),
                                          '/usr/local/lib', '/usr/lib']

        dirs = []

        if '/' in libname:
            dirs.extend(_environ_path("DYLD_LIBRARY_PATH"))
        else:
            dirs.extend(_environ_path("LD_LIBRARY_PATH"))
            dirs.extend(_environ_path("DYLD_LIBRARY_PATH"))

        dirs.extend(self.other_dirs)
        dirs.append(".")
        dirs.append(os.path.dirname(__file__))

        if hasattr(sys, 'frozen') and sys.frozen == 'macosx_app':
            dirs.append(os.path.join(
                os.environ['RESOURCEPATH'],
                '..',
                'Frameworks'))

        dirs.extend(dyld_fallback_library_path)

        return dirs

# Posix

class PosixLibraryLoader(LibraryLoader):
    _ld_so_cache = None

    def _create_ld_so_cache(self):
        # Recreate search path followed by ld.so.  This is going to be
        # slow to build, and incorrect (ld.so uses ld.so.cache, which may
        # not be up-to-date).  Used only as fallback for distros without
        # /sbin/ldconfig.
        #
        # We assume the DT_RPATH and DT_RUNPATH binary sections are omitted.

        directories = []
        for name in ("LD_LIBRARY_PATH",
                     "SHLIB_PATH", # HPUX
                     "LIBPATH", # OS/2, AIX
                     "LIBRARY_PATH", # BE/OS
                    ):
            if name in os.environ:
                directories.extend(os.environ[name].split(os.pathsep))
        directories.extend(self.other_dirs)
        directories.append(".")
        directories.append(os.path.dirname(__file__))

        try: directories.extend([dir.strip() for dir in open('/etc/ld.so.conf')])
        except IOError: pass

        directories.extend(['/lib', '/usr/lib', '/lib64', '/usr/lib64'])

        cache = {}
        lib_re = re.compile(r'lib(.*)\.s[ol]')
        ext_re = re.compile(r'\.s[ol]$')
        for dir in directories:
            try:
                for path in glob.glob("%s/*.s[ol]*" % dir):
                    file = os.path.basename(path)

                    # Index by filename
                    if file not in cache:
                        cache[file] = path

                    # Index by library name
                    match = lib_re.match(file)
                    if match:
                        library = match.group(1)
                        if library not in cache:
                            cache[library] = path
            except OSError:
                pass

        self._ld_so_cache = cache

    def getplatformpaths(self, libname):
        if self._ld_so_cache is None:
            self._create_ld_so_cache()

        result = self._ld_so_cache.get(libname)
        if result: yield result

        path = ctypes.util.find_library(libname)
        if path: yield os.path.join("/lib",path)

# Windows

class _WindowsLibrary(object):
    def __init__(self, path):
        self.cdll = ctypes.cdll.LoadLibrary(path)
        self.windll = ctypes.windll.LoadLibrary(path)

    def __getattr__(self, name):
        try: return getattr(self.cdll,name)
        except AttributeError:
            try: return getattr(self.windll,name)
            except AttributeError:
                raise

class WindowsLibraryLoader(LibraryLoader):
    name_formats = ["%s.dll", "lib%s.dll", "%slib.dll"]

    def load_library(self, libname):
        try:
            result = LibraryLoader.load_library(self, libname)
        except ImportError:
            result = None
            if os.path.sep not in libname:
                for name in self.name_formats:
                    try:
                        result = getattr(ctypes.cdll, name % libname)
                        if result:
                            break
                    except WindowsError:
                        result = None
            if result is None:
                try:
                    result = getattr(ctypes.cdll, libname)
                except WindowsError:
                    result = None
            if result is None:
                raise ImportError("%s not found." % libname)
        return result

    def load(self, path):
        return _WindowsLibrary(path)

    def getplatformpaths(self, libname):
        if os.path.sep not in libname:
            for name in self.name_formats:
                dll_in_current_dir = os.path.abspath(name % libname)
                if os.path.exists(dll_in_current_dir):
                    yield dll_in_current_dir
                path = ctypes.util.find_library(name % libname)
                if path:
                    yield path

# Platform switching

# If your value of sys.platform does not appear in this dict, please contact
# the Ctypesgen maintainers.

loaderclass = {
    "darwin":   DarwinLibraryLoader,
    "cygwin":   WindowsLibraryLoader,
    "win32":    WindowsLibraryLoader
}

loader = loaderclass.get(sys.platform, PosixLibraryLoader)()

def add_library_search_dirs(other_dirs):
    loader.other_dirs = other_dirs

load_library = loader.load_library

del loaderclass

# End loader

add_library_search_dirs(['../../bin/clientlib/'])

# Begin libraries

_libs["libclientlib.so"] = load_library("libclientlib.so")

# 1 libraries
# End libraries

# No modules

guint8 = c_ubyte # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 39

guint16 = c_ushort # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 41

guint32 = c_uint # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 46

gint64 = c_longlong # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 52

guint64 = c_ulonglong # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 53

gssize = c_int # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 65

gsize = c_uint # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 66

__u_int = c_uint # /usr/include/bits/types.h: 33

__time_t = c_long # /usr/include/bits/types.h: 149

__suseconds_t = c_long # /usr/include/bits/types.h: 151

__socklen_t = c_uint # /usr/include/bits/types.h: 192

gchar = c_char # /usr/include/glib-2.0/glib/gtypes.h: 47

gint = c_int # /usr/include/glib-2.0/glib/gtypes.h: 50

gboolean = gint # /usr/include/glib-2.0/glib/gtypes.h: 51

gushort = c_ushort # /usr/include/glib-2.0/glib/gtypes.h: 54

guint = c_uint # /usr/include/glib-2.0/glib/gtypes.h: 56

gpointer = POINTER(None) # /usr/include/glib-2.0/glib/gtypes.h: 78

gconstpointer = POINTER(None) # /usr/include/glib-2.0/glib/gtypes.h: 79

GDestroyNotify = CFUNCTYPE(UNCHECKED(None), gpointer) # /usr/include/glib-2.0/glib/gtypes.h: 88

GQuark = guint32 # /usr/include/glib-2.0/glib/gquark.h: 38

# /usr/include/glib-2.0/glib/gerror.h: 36
class struct__GError(Structure):
    pass

GError = struct__GError # /usr/include/glib-2.0/glib/gerror.h: 34

struct__GError.__slots__ = [
    'domain',
    'code',
    'message',
]
struct__GError._fields_ = [
    ('domain', GQuark),
    ('code', gint),
    ('message', POINTER(gchar)),
]

# /usr/include/glib-2.0/glib/gmem.h: 71
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'g_free'):
        continue
    g_free = _lib.g_free
    g_free.argtypes = [gpointer]
    g_free.restype = None
    break

# /usr/include/glib-2.0/glib/gmem.h: 77
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'g_try_malloc'):
        continue
    g_try_malloc = _lib.g_try_malloc
    g_try_malloc.argtypes = [gsize]
    g_try_malloc.restype = gpointer
    break

# /usr/include/glib-2.0/glib/gmem.h: 78
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'g_try_malloc0'):
        continue
    g_try_malloc0 = _lib.g_try_malloc0
    g_try_malloc0.argtypes = [gsize]
    g_try_malloc0.restype = gpointer
    break

enum_anon_46 = c_int # /usr/include/glib-2.0/glib/gchecksum.h: 50

GChecksumType = enum_anon_46 # /usr/include/glib-2.0/glib/gchecksum.h: 50

# /usr/include/glib-2.0/glib/gconvert.h: 77
class struct__GIConv(Structure):
    pass

GIConv = POINTER(struct__GIConv) # /usr/include/glib-2.0/glib/gconvert.h: 77

# /usr/include/glib-2.0/glib/ghash.h: 39
class struct__GHashTable(Structure):
    pass

GHashTable = struct__GHashTable # /usr/include/glib-2.0/glib/ghash.h: 39

# /usr/include/glib-2.0/glib/gpoll.h: 90
class struct__GPollFD(Structure):
    pass

GPollFD = struct__GPollFD # /usr/include/glib-2.0/glib/gpoll.h: 61

struct__GPollFD.__slots__ = [
    'fd',
    'events',
    'revents',
]
struct__GPollFD._fields_ = [
    ('fd', gint),
    ('events', gushort),
    ('revents', gushort),
]

# /usr/include/glib-2.0/glib/gslist.h: 40
class struct__GSList(Structure):
    pass

GSList = struct__GSList # /usr/include/glib-2.0/glib/gslist.h: 38

struct__GSList.__slots__ = [
    'data',
    'next',
]
struct__GSList._fields_ = [
    ('data', gpointer),
    ('next', POINTER(GSList)),
]

# /usr/include/glib-2.0/glib/gmain.h: 39
class struct__GMainContext(Structure):
    pass

GMainContext = struct__GMainContext # /usr/include/glib-2.0/glib/gmain.h: 39

# /usr/include/glib-2.0/glib/gmain.h: 140
class struct__GSource(Structure):
    pass

GSource = struct__GSource # /usr/include/glib-2.0/glib/gmain.h: 55

# /usr/include/glib-2.0/glib/gmain.h: 56
class struct__GSourcePrivate(Structure):
    pass

GSourcePrivate = struct__GSourcePrivate # /usr/include/glib-2.0/glib/gmain.h: 56

# /usr/include/glib-2.0/glib/gmain.h: 165
class struct__GSourceCallbackFuncs(Structure):
    pass

GSourceCallbackFuncs = struct__GSourceCallbackFuncs # /usr/include/glib-2.0/glib/gmain.h: 68

# /usr/include/glib-2.0/glib/gmain.h: 177
class struct__GSourceFuncs(Structure):
    pass

GSourceFuncs = struct__GSourceFuncs # /usr/include/glib-2.0/glib/gmain.h: 115

GSourceFunc = CFUNCTYPE(UNCHECKED(gboolean), gpointer) # /usr/include/glib-2.0/glib/gmain.h: 126

struct__GSource.__slots__ = [
    'callback_data',
    'callback_funcs',
    'source_funcs',
    'ref_count',
    'context',
    'priority',
    'flags',
    'source_id',
    'poll_fds',
    'prev',
    'next',
    'name',
    'priv',
]
struct__GSource._fields_ = [
    ('callback_data', gpointer),
    ('callback_funcs', POINTER(GSourceCallbackFuncs)),
    ('source_funcs', POINTER(GSourceFuncs)),
    ('ref_count', guint),
    ('context', POINTER(GMainContext)),
    ('priority', gint),
    ('flags', guint),
    ('source_id', guint),
    ('poll_fds', POINTER(GSList)),
    ('prev', POINTER(GSource)),
    ('next', POINTER(GSource)),
    ('name', String),
    ('priv', POINTER(GSourcePrivate)),
]

struct__GSourceCallbackFuncs.__slots__ = [
    'ref',
    'unref',
    'get',
]
struct__GSourceCallbackFuncs._fields_ = [
    ('ref', CFUNCTYPE(UNCHECKED(None), gpointer)),
    ('unref', CFUNCTYPE(UNCHECKED(None), gpointer)),
    ('get', CFUNCTYPE(UNCHECKED(None), gpointer, POINTER(GSource), POINTER(GSourceFunc), POINTER(gpointer))),
]

GSourceDummyMarshal = CFUNCTYPE(UNCHECKED(None), ) # /usr/include/glib-2.0/glib/gmain.h: 175

struct__GSourceFuncs.__slots__ = [
    'prepare',
    'check',
    'dispatch',
    'finalize',
    'closure_callback',
    'closure_marshal',
]
struct__GSourceFuncs._fields_ = [
    ('prepare', CFUNCTYPE(UNCHECKED(gboolean), POINTER(GSource), POINTER(gint))),
    ('check', CFUNCTYPE(UNCHECKED(gboolean), POINTER(GSource))),
    ('dispatch', CFUNCTYPE(UNCHECKED(gboolean), POINTER(GSource), GSourceFunc, gpointer)),
    ('finalize', CFUNCTYPE(UNCHECKED(None), POINTER(GSource))),
    ('closure_callback', GSourceFunc),
    ('closure_marshal', GSourceDummyMarshal),
]

# /usr/include/glib-2.0/glib/gstring.h: 43
class struct__GString(Structure):
    pass

GString = struct__GString # /usr/include/glib-2.0/glib/gstring.h: 40

struct__GString.__slots__ = [
    'str',
    'len',
    'allocated_len',
]
struct__GString._fields_ = [
    ('str', POINTER(gchar)),
    ('len', gsize),
    ('allocated_len', gsize),
]

# /usr/include/glib-2.0/glib/giochannel.h: 108
class struct__GIOChannel(Structure):
    pass

GIOChannel = struct__GIOChannel # /usr/include/glib-2.0/glib/giochannel.h: 43

# /usr/include/glib-2.0/glib/giochannel.h: 142
class struct__GIOFuncs(Structure):
    pass

GIOFuncs = struct__GIOFuncs # /usr/include/glib-2.0/glib/giochannel.h: 44

enum_anon_61 = c_int # /usr/include/glib-2.0/glib/giochannel.h: 77

GIOStatus = enum_anon_61 # /usr/include/glib-2.0/glib/giochannel.h: 77

enum_anon_62 = c_int # /usr/include/glib-2.0/glib/giochannel.h: 84

GSeekType = enum_anon_62 # /usr/include/glib-2.0/glib/giochannel.h: 84

enum_anon_63 = c_int # /usr/include/glib-2.0/glib/giochannel.h: 94

GIOCondition = enum_anon_63 # /usr/include/glib-2.0/glib/giochannel.h: 94

enum_anon_64 = c_int # /usr/include/glib-2.0/glib/giochannel.h: 106

GIOFlags = enum_anon_64 # /usr/include/glib-2.0/glib/giochannel.h: 106

struct__GIOChannel.__slots__ = [
    'ref_count',
    'funcs',
    'encoding',
    'read_cd',
    'write_cd',
    'line_term',
    'line_term_len',
    'buf_size',
    'read_buf',
    'encoded_read_buf',
    'write_buf',
    'partial_write_buf',
    'use_buffer',
    'do_encode',
    'close_on_unref',
    'is_readable',
    'is_writeable',
    'is_seekable',
    'reserved1',
    'reserved2',
]
struct__GIOChannel._fields_ = [
    ('ref_count', gint),
    ('funcs', POINTER(GIOFuncs)),
    ('encoding', POINTER(gchar)),
    ('read_cd', GIConv),
    ('write_cd', GIConv),
    ('line_term', POINTER(gchar)),
    ('line_term_len', guint),
    ('buf_size', gsize),
    ('read_buf', POINTER(GString)),
    ('encoded_read_buf', POINTER(GString)),
    ('write_buf', POINTER(GString)),
    ('partial_write_buf', gchar * 6),
    ('use_buffer', guint, 1),
    ('do_encode', guint, 1),
    ('close_on_unref', guint, 1),
    ('is_readable', guint, 1),
    ('is_writeable', guint, 1),
    ('is_seekable', guint, 1),
    ('reserved1', gpointer),
    ('reserved2', gpointer),
]

struct__GIOFuncs.__slots__ = [
    'io_read',
    'io_write',
    'io_seek',
    'io_close',
    'io_create_watch',
    'io_free',
    'io_set_flags',
    'io_get_flags',
]
struct__GIOFuncs._fields_ = [
    ('io_read', CFUNCTYPE(UNCHECKED(GIOStatus), POINTER(GIOChannel), POINTER(gchar), gsize, POINTER(gsize), POINTER(POINTER(GError)))),
    ('io_write', CFUNCTYPE(UNCHECKED(GIOStatus), POINTER(GIOChannel), POINTER(gchar), gsize, POINTER(gsize), POINTER(POINTER(GError)))),
    ('io_seek', CFUNCTYPE(UNCHECKED(GIOStatus), POINTER(GIOChannel), gint64, GSeekType, POINTER(POINTER(GError)))),
    ('io_close', CFUNCTYPE(UNCHECKED(GIOStatus), POINTER(GIOChannel), POINTER(POINTER(GError)))),
    ('io_create_watch', CFUNCTYPE(UNCHECKED(POINTER(GSource)), POINTER(GIOChannel), GIOCondition)),
    ('io_free', CFUNCTYPE(UNCHECKED(None), POINTER(GIOChannel))),
    ('io_set_flags', CFUNCTYPE(UNCHECKED(GIOStatus), POINTER(GIOChannel), GIOFlags, POINTER(POINTER(GError)))),
    ('io_get_flags', CFUNCTYPE(UNCHECKED(GIOFlags), POINTER(GIOChannel))),
]

# /home/alanr/monitor/src/include/frameset.h: 27
class struct__FrameSet(Structure):
    pass

FrameSet = struct__FrameSet # include/frame.h: 18

# include/frame.h: 29
class struct__Frame(Structure):
    pass

Frame = struct__Frame # include/frame.h: 19

struct__Frame.__slots__ = [
    'type',
    'length',
    'value',
    'refcount',
    'dataspace',
    'updatedata',
    'isvalid',
    'setvalue',
    'dump',
    'valuefinalize',
    'ref',
    'unref',
    '_finalize',
]
struct__Frame._fields_ = [
    ('type', guint16),
    ('length', guint16),
    ('value', gpointer),
    ('refcount', gint),
    ('dataspace', CFUNCTYPE(UNCHECKED(gsize), POINTER(Frame))),
    ('updatedata', CFUNCTYPE(UNCHECKED(None), POINTER(Frame), gpointer, gconstpointer, POINTER(FrameSet))),
    ('isvalid', CFUNCTYPE(UNCHECKED(gboolean), POINTER(Frame), gconstpointer, gconstpointer)),
    ('setvalue', CFUNCTYPE(UNCHECKED(None), POINTER(Frame), gpointer, guint16, GDestroyNotify)),
    ('dump', CFUNCTYPE(UNCHECKED(None), POINTER(Frame), String)),
    ('valuefinalize', GDestroyNotify),
    ('ref', CFUNCTYPE(UNCHECKED(None), POINTER(Frame))),
    ('unref', CFUNCTYPE(UNCHECKED(None), POINTER(Frame))),
    ('_finalize', CFUNCTYPE(UNCHECKED(None), POINTER(Frame))),
]

# include/frame.h: 49
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frame_new'):
        continue
    frame_new = _lib.frame_new
    frame_new.argtypes = [guint16, gsize]
    frame_new.restype = POINTER(Frame)
    break

# include/frame.h: 50
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frame_tlvconstructor'):
        continue
    frame_tlvconstructor = _lib.frame_tlvconstructor
    frame_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    frame_tlvconstructor.restype = POINTER(Frame)
    break

# include/frame.h: 51
for _lib in _libs.itervalues():
    if not hasattr(_lib, '_frame_default_valuefinalize'):
        continue
    _frame_default_valuefinalize = _lib._frame_default_valuefinalize
    _frame_default_valuefinalize.argtypes = [gpointer]
    _frame_default_valuefinalize.restype = None
    break

# include/proj_classes.h: 14
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_new'):
        continue
    proj_class_new = _lib.proj_class_new
    proj_class_new.argtypes = [gsize, String]
    proj_class_new.restype = gpointer
    break

# include/proj_classes.h: 15
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_dissociate'):
        continue
    proj_class_dissociate = _lib.proj_class_dissociate
    proj_class_dissociate.argtypes = [gpointer]
    proj_class_dissociate.restype = None
    break

# include/proj_classes.h: 16
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_free'):
        continue
    proj_class_free = _lib.proj_class_free
    proj_class_free.argtypes = [gpointer]
    proj_class_free.restype = None
    break

# include/proj_classes.h: 17
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_register_object'):
        continue
    proj_class_register_object = _lib.proj_class_register_object
    proj_class_register_object.argtypes = [gpointer, String]
    proj_class_register_object.restype = None
    break

# include/proj_classes.h: 18
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_castas'):
        continue
    proj_class_castas = _lib.proj_class_castas
    proj_class_castas.argtypes = [gpointer, String]
    proj_class_castas.restype = gpointer
    break

# include/proj_classes.h: 19
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_register_subclassed'):
        continue
    proj_class_register_subclassed = _lib.proj_class_register_subclassed
    proj_class_register_subclassed.argtypes = [gpointer, String]
    proj_class_register_subclassed.restype = None
    break

# include/proj_classes.h: 20
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_quark_add_superclass_relationship'):
        continue
    proj_class_quark_add_superclass_relationship = _lib.proj_class_quark_add_superclass_relationship
    proj_class_quark_add_superclass_relationship.argtypes = [GQuark, GQuark]
    proj_class_quark_add_superclass_relationship.restype = None
    break

# include/proj_classes.h: 21
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_quark_is_a'):
        continue
    proj_class_quark_is_a = _lib.proj_class_quark_is_a
    proj_class_quark_is_a.argtypes = [GQuark, GQuark]
    proj_class_quark_is_a.restype = gboolean
    break

# include/proj_classes.h: 22
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_classname'):
        continue
    proj_class_classname = _lib.proj_class_classname
    proj_class_classname.argtypes = [gconstpointer]
    if sizeof(c_int) == sizeof(c_void_p):
        proj_class_classname.restype = ReturnString
    else:
        proj_class_classname.restype = String
        proj_class_classname.errcheck = ReturnString
    break

# include/proj_classes.h: 25
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_dump_live_objects'):
        continue
    proj_class_dump_live_objects = _lib.proj_class_dump_live_objects
    proj_class_dump_live_objects.argtypes = []
    proj_class_dump_live_objects.restype = None
    break

u_int = __u_int # /usr/include/sys/types.h: 36

# /usr/include/bits/time.h: 75
class struct_timeval(Structure):
    pass

struct_timeval.__slots__ = [
    'tv_sec',
    'tv_usec',
]
struct_timeval._fields_ = [
    ('tv_sec', __time_t),
    ('tv_usec', __suseconds_t),
]

socklen_t = __socklen_t # /usr/include/bits/socket.h: 35

sa_family_t = c_uint # /usr/include/bits/sockaddr.h: 29

in_port_t = c_uint16 # /usr/include/netinet/in.h: 97

# /usr/include/netinet/in.h: 200
class union_anon_98(Union):
    pass

union_anon_98.__slots__ = [
    '__u6_addr8',
    '__u6_addr16',
    '__u6_addr32',
]
union_anon_98._fields_ = [
    ('__u6_addr8', c_uint8 * 16),
    ('__u6_addr16', c_uint16 * 8),
    ('__u6_addr32', c_uint32 * 4),
]

# /usr/include/netinet/in.h: 198
class struct_in6_addr(Structure):
    pass

struct_in6_addr.__slots__ = [
    '__in6_u',
]
struct_in6_addr._fields_ = [
    ('__in6_u', union_anon_98),
]

# /usr/include/netinet/in.h: 239
class struct_sockaddr_in6(Structure):
    pass

struct_sockaddr_in6.__slots__ = [
    'sin6_family',
    'sin6_port',
    'sin6_flowinfo',
    'sin6_addr',
    'sin6_scope_id',
]
struct_sockaddr_in6._fields_ = [
    ('sin6_family', sa_family_t),
    ('sin6_port', in_port_t),
    ('sin6_flowinfo', c_uint32),
    ('sin6_addr', struct_in6_addr),
    ('sin6_scope_id', c_uint32),
]

# include/netaddr.h: 25
class struct__NetAddr(Structure):
    pass

NetAddr = struct__NetAddr # include/netaddr.h: 18

struct__NetAddr.__slots__ = [
    'port',
    'addrtype',
    'ipv6sockaddr',
    'equal',
    'toString',
    'ref',
    'unref',
    '_finalize',
    '_addrbody',
    '_addrtype',
    '_addrlen',
    '_addrport',
    '_refcount',
]
struct__NetAddr._fields_ = [
    ('port', CFUNCTYPE(UNCHECKED(guint16), POINTER(NetAddr))),
    ('addrtype', CFUNCTYPE(UNCHECKED(guint16), POINTER(NetAddr))),
    ('ipv6sockaddr', CFUNCTYPE(UNCHECKED(struct_sockaddr_in6), POINTER(NetAddr))),
    ('equal', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetAddr), POINTER(NetAddr))),
    ('toString', CFUNCTYPE(UNCHECKED(POINTER(gchar)), POINTER(NetAddr))),
    ('ref', CFUNCTYPE(UNCHECKED(None), POINTER(NetAddr))),
    ('unref', CFUNCTYPE(UNCHECKED(None), POINTER(NetAddr))),
    ('_finalize', CFUNCTYPE(UNCHECKED(None), POINTER(NetAddr))),
    ('_addrbody', gpointer),
    ('_addrtype', guint16),
    ('_addrlen', guint16),
    ('_addrport', guint16),
    ('_refcount', guint16),
]

# include/netaddr.h: 40
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netaddr_new'):
        continue
    netaddr_new = _lib.netaddr_new
    netaddr_new.argtypes = [gsize, guint16, guint16, gconstpointer, guint16]
    netaddr_new.restype = POINTER(NetAddr)
    break

# include/netaddr.h: 41
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netaddr_sockaddr_new'):
        continue
    netaddr_sockaddr_new = _lib.netaddr_sockaddr_new
    netaddr_sockaddr_new.argtypes = [POINTER(struct_sockaddr_in6), socklen_t]
    netaddr_sockaddr_new.restype = POINTER(NetAddr)
    break

# include/netaddr.h: 42
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netaddr_macaddr_new'):
        continue
    netaddr_macaddr_new = _lib.netaddr_macaddr_new
    netaddr_macaddr_new.argtypes = [gconstpointer, guint16]
    netaddr_macaddr_new.restype = POINTER(NetAddr)
    break

# include/netaddr.h: 43
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netaddr_mac48_new'):
        continue
    netaddr_mac48_new = _lib.netaddr_mac48_new
    netaddr_mac48_new.argtypes = [gconstpointer]
    netaddr_mac48_new.restype = POINTER(NetAddr)
    break

# include/netaddr.h: 44
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netaddr_mac64_new'):
        continue
    netaddr_mac64_new = _lib.netaddr_mac64_new
    netaddr_mac64_new.argtypes = [gconstpointer]
    netaddr_mac64_new.restype = POINTER(NetAddr)
    break

# include/netaddr.h: 45
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netaddr_ipv4_new'):
        continue
    netaddr_ipv4_new = _lib.netaddr_ipv4_new
    netaddr_ipv4_new.argtypes = [gconstpointer, guint16]
    netaddr_ipv4_new.restype = POINTER(NetAddr)
    break

# include/netaddr.h: 46
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netaddr_ipv6_new'):
        continue
    netaddr_ipv6_new = _lib.netaddr_ipv6_new
    netaddr_ipv6_new.argtypes = [gconstpointer, guint16]
    netaddr_ipv6_new.restype = POINTER(NetAddr)
    break

# /home/alanr/monitor/src/include/addrframe.h: 25
class struct__AddrFrame(Structure):
    pass

AddrFrame = struct__AddrFrame # /home/alanr/monitor/src/include/addrframe.h: 18

struct__AddrFrame.__slots__ = [
    'baseclass',
    'setaddr',
    'setnetaddr',
]
struct__AddrFrame._fields_ = [
    ('baseclass', Frame),
    ('setaddr', CFUNCTYPE(UNCHECKED(None), POINTER(AddrFrame), guint16, gconstpointer, gsize)),
    ('setnetaddr', CFUNCTYPE(UNCHECKED(None), POINTER(AddrFrame), POINTER(NetAddr))),
]

# /home/alanr/monitor/src/include/addrframe.h: 31
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'addrframe_new'):
        continue
    addrframe_new = _lib.addrframe_new
    addrframe_new.argtypes = [guint16, gsize]
    addrframe_new.restype = POINTER(AddrFrame)
    break

# /home/alanr/monitor/src/include/addrframe.h: 32
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'addrframe_ipv4_new'):
        continue
    addrframe_ipv4_new = _lib.addrframe_ipv4_new
    addrframe_ipv4_new.argtypes = [guint16, gconstpointer]
    addrframe_ipv4_new.restype = POINTER(AddrFrame)
    break

# /home/alanr/monitor/src/include/addrframe.h: 33
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'addrframe_ipv6_new'):
        continue
    addrframe_ipv6_new = _lib.addrframe_ipv6_new
    addrframe_ipv6_new.argtypes = [guint16, gconstpointer]
    addrframe_ipv6_new.restype = POINTER(AddrFrame)
    break

# /home/alanr/monitor/src/include/addrframe.h: 34
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'addrframe_mac48_new'):
        continue
    addrframe_mac48_new = _lib.addrframe_mac48_new
    addrframe_mac48_new.argtypes = [guint16, gconstpointer]
    addrframe_mac48_new.restype = POINTER(AddrFrame)
    break

# /home/alanr/monitor/src/include/addrframe.h: 35
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'addrframe_mac64_new'):
        continue
    addrframe_mac64_new = _lib.addrframe_mac64_new
    addrframe_mac64_new.argtypes = [guint16, gconstpointer]
    addrframe_mac64_new.restype = POINTER(AddrFrame)
    break

# /home/alanr/monitor/src/include/addrframe.h: 36
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'addrframe_tlvconstructor'):
        continue
    addrframe_tlvconstructor = _lib.addrframe_tlvconstructor
    addrframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    addrframe_tlvconstructor.restype = POINTER(Frame)
    break

# /home/alanr/monitor/src/include/cdp.h: 54
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdp_vers'):
        continue
    get_cdp_vers = _lib.get_cdp_vers
    get_cdp_vers.argtypes = [gconstpointer, gconstpointer]
    get_cdp_vers.restype = guint8
    break

# /home/alanr/monitor/src/include/cdp.h: 55
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdp_ttl'):
        continue
    get_cdp_ttl = _lib.get_cdp_ttl
    get_cdp_ttl.argtypes = [gconstpointer, gconstpointer]
    get_cdp_ttl.restype = guint8
    break

# /home/alanr/monitor/src/include/cdp.h: 56
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdp_cksum'):
        continue
    get_cdp_cksum = _lib.get_cdp_cksum
    get_cdp_cksum.argtypes = [gconstpointer, gconstpointer]
    get_cdp_cksum.restype = guint16
    break

# /home/alanr/monitor/src/include/cdp.h: 57
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdptlv_type'):
        continue
    get_cdptlv_type = _lib.get_cdptlv_type
    get_cdptlv_type.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_type.restype = guint16
    break

# /home/alanr/monitor/src/include/cdp.h: 58
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdptlv_len'):
        continue
    get_cdptlv_len = _lib.get_cdptlv_len
    get_cdptlv_len.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_len.restype = gsize
    break

# /home/alanr/monitor/src/include/cdp.h: 59
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdptlv_vlen'):
        continue
    get_cdptlv_vlen = _lib.get_cdptlv_vlen
    get_cdptlv_vlen.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_vlen.restype = gsize
    break

# /home/alanr/monitor/src/include/cdp.h: 60
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdptlv_body'):
        continue
    get_cdptlv_body = _lib.get_cdptlv_body
    get_cdptlv_body.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_body.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/cdp.h: 61
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdptlv_first'):
        continue
    get_cdptlv_first = _lib.get_cdptlv_first
    get_cdptlv_first.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_first.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/cdp.h: 62
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdptlv_next'):
        continue
    get_cdptlv_next = _lib.get_cdptlv_next
    get_cdptlv_next.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_next.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/cdp.h: 63
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdp_chassis_id'):
        continue
    get_cdp_chassis_id = _lib.get_cdp_chassis_id
    get_cdp_chassis_id.argtypes = [gconstpointer, POINTER(gssize), gconstpointer]
    get_cdp_chassis_id.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/cdp.h: 64
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_cdp_port_id'):
        continue
    get_cdp_port_id = _lib.get_cdp_port_id
    get_cdp_port_id.argtypes = [gconstpointer, POINTER(gssize), gconstpointer]
    get_cdp_port_id.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/cdp.h: 65
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'is_valid_cdp_packet'):
        continue
    is_valid_cdp_packet = _lib.is_valid_cdp_packet
    is_valid_cdp_packet.argtypes = [gconstpointer, gconstpointer]
    is_valid_cdp_packet.restype = gboolean
    break

# /home/alanr/monitor/src/include/cstringframe.h: 23
class struct__CstringFrame(Structure):
    pass

CstringFrame = struct__CstringFrame # /home/alanr/monitor/src/include/cstringframe.h: 18

struct__CstringFrame.__slots__ = [
    'baseclass',
]
struct__CstringFrame._fields_ = [
    ('baseclass', Frame),
]

# /home/alanr/monitor/src/include/cstringframe.h: 27
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'cstringframe_new'):
        continue
    cstringframe_new = _lib.cstringframe_new
    cstringframe_new.argtypes = [guint16, gsize]
    cstringframe_new.restype = POINTER(CstringFrame)
    break

# /home/alanr/monitor/src/include/cstringframe.h: 28
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'cstringframe_tlvconstructor'):
        continue
    cstringframe_tlvconstructor = _lib.cstringframe_tlvconstructor
    cstringframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    cstringframe_tlvconstructor.restype = POINTER(Frame)
    break

# /home/alanr/monitor/src/include/decode_packet.h: 20
class struct__FrameTypeToFrame(Structure):
    pass

FrameTypeToFrame = struct__FrameTypeToFrame # /home/alanr/monitor/src/include/decode_packet.h: 15

FramePktConstructor = CFUNCTYPE(UNCHECKED(POINTER(Frame)), gconstpointer, gconstpointer) # /home/alanr/monitor/src/include/decode_packet.h: 17

struct__FrameTypeToFrame.__slots__ = [
    'frametype',
    'constructor',
]
struct__FrameTypeToFrame._fields_ = [
    ('frametype', c_int),
    ('constructor', FramePktConstructor),
]

# /home/alanr/monitor/src/include/decode_packet.h: 24
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'pktdata_to_frameset_list'):
        continue
    pktdata_to_frameset_list = _lib.pktdata_to_frameset_list
    pktdata_to_frameset_list.argtypes = [gconstpointer, gconstpointer]
    pktdata_to_frameset_list.restype = POINTER(GSList)
    break

# /home/alanr/monitor/src/include/discovery.h: 32
class struct__Discovery(Structure):
    pass

Discovery = struct__Discovery # /home/alanr/monitor/src/include/discovery.h: 30

struct__Discovery.__slots__ = [
    'discoveryname',
    'discover',
    'finalize',
    'discoverintervalsecs',
    '_timerid',
]
struct__Discovery._fields_ = [
    ('discoveryname', CFUNCTYPE(UNCHECKED(String), POINTER(Discovery))),
    ('discover', CFUNCTYPE(UNCHECKED(gboolean), POINTER(Discovery))),
    ('finalize', CFUNCTYPE(UNCHECKED(None), POINTER(Discovery))),
    ('discoverintervalsecs', CFUNCTYPE(UNCHECKED(guint), POINTER(Discovery))),
    ('_timerid', guint),
]

# /home/alanr/monitor/src/include/discovery.h: 40
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'discovery_new'):
        continue
    discovery_new = _lib.discovery_new
    discovery_new.argtypes = [gsize]
    discovery_new.restype = POINTER(Discovery)
    break

# /home/alanr/monitor/src/include/discovery.h: 41
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'discovery_register'):
        continue
    discovery_register = _lib.discovery_register
    discovery_register.argtypes = [POINTER(Discovery)]
    discovery_register.restype = None
    break

# include/signframe.h: 27
class struct__SignFrame(Structure):
    pass

SignFrame = struct__SignFrame # include/signframe.h: 20

struct__SignFrame.__slots__ = [
    'baseclass',
    'signaturetype',
]
struct__SignFrame._fields_ = [
    ('baseclass', Frame),
    ('signaturetype', GChecksumType),
]

# include/signframe.h: 32
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'signframe_new'):
        continue
    signframe_new = _lib.signframe_new
    signframe_new.argtypes = [GChecksumType, gsize]
    signframe_new.restype = POINTER(SignFrame)
    break

# include/signframe.h: 33
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'signframe_tlvconstructor'):
        continue
    signframe_tlvconstructor = _lib.signframe_tlvconstructor
    signframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    signframe_tlvconstructor.restype = POINTER(Frame)
    break

struct__FrameSet.__slots__ = [
    'framelist',
    'packet',
    'pktend',
    'refcount',
    'fstype',
    'fsflags',
    'ref',
    'unref',
    '_finalize',
]
struct__FrameSet._fields_ = [
    ('framelist', POINTER(GSList)),
    ('packet', gpointer),
    ('pktend', gpointer),
    ('refcount', guint),
    ('fstype', guint16),
    ('fsflags', guint16),
    ('ref', CFUNCTYPE(UNCHECKED(None), POINTER(FrameSet))),
    ('unref', CFUNCTYPE(UNCHECKED(None), POINTER(FrameSet))),
    ('_finalize', CFUNCTYPE(UNCHECKED(None), POINTER(FrameSet))),
]

# /home/alanr/monitor/src/include/frameset.h: 42
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frameset_new'):
        continue
    frameset_new = _lib.frameset_new
    frameset_new.argtypes = [guint16]
    frameset_new.restype = POINTER(FrameSet)
    break

# /home/alanr/monitor/src/include/frameset.h: 43
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frameset_prepend_frame'):
        continue
    frameset_prepend_frame = _lib.frameset_prepend_frame
    frameset_prepend_frame.argtypes = [POINTER(FrameSet), POINTER(Frame)]
    frameset_prepend_frame.restype = None
    break

# /home/alanr/monitor/src/include/frameset.h: 44
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frameset_append_frame'):
        continue
    frameset_append_frame = _lib.frameset_append_frame
    frameset_append_frame.argtypes = [POINTER(FrameSet), POINTER(Frame)]
    frameset_append_frame.restype = None
    break

# /home/alanr/monitor/src/include/frameset.h: 45
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frameset_construct_packet'):
        continue
    frameset_construct_packet = _lib.frameset_construct_packet
    frameset_construct_packet.argtypes = [POINTER(FrameSet), POINTER(SignFrame), POINTER(Frame), POINTER(Frame)]
    frameset_construct_packet.restype = None
    break

# /home/alanr/monitor/src/include/frameset.h: 46
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frame_new'):
        continue
    frame_new = _lib.frame_new
    frame_new.argtypes = [guint16, gsize]
    frame_new.restype = POINTER(Frame)
    break

# /home/alanr/monitor/src/include/frameset.h: 47
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frameset_get_flags'):
        continue
    frameset_get_flags = _lib.frameset_get_flags
    frameset_get_flags.argtypes = [POINTER(FrameSet)]
    frameset_get_flags.restype = guint16
    break

# /home/alanr/monitor/src/include/frameset.h: 48
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frameset_set_flags'):
        continue
    frameset_set_flags = _lib.frameset_set_flags
    frameset_set_flags.argtypes = [POINTER(FrameSet), guint16]
    frameset_set_flags.restype = guint16
    break

# /home/alanr/monitor/src/include/frameset.h: 49
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frameset_clear_flags'):
        continue
    frameset_clear_flags = _lib.frameset_clear_flags
    frameset_clear_flags.argtypes = [POINTER(FrameSet), guint16]
    frameset_clear_flags.restype = guint16
    break

# /home/alanr/monitor/src/include/frameset.h: 50
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frame_append_to_frameset_packet'):
        continue
    frame_append_to_frameset_packet = _lib.frame_append_to_frameset_packet
    frame_append_to_frameset_packet.argtypes = [POINTER(FrameSet), POINTER(Frame), gpointer]
    frame_append_to_frameset_packet.restype = gpointer
    break

# /home/alanr/monitor/src/include/frameset.h: 51
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'frameset_dump'):
        continue
    frameset_dump = _lib.frameset_dump
    frameset_dump.argtypes = [POINTER(FrameSet)]
    frameset_dump.restype = None
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 15
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_generic_tlv_type'):
        continue
    get_generic_tlv_type = _lib.get_generic_tlv_type
    get_generic_tlv_type.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_type.restype = guint16
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 16
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_generic_tlv_len'):
        continue
    get_generic_tlv_len = _lib.get_generic_tlv_len
    get_generic_tlv_len.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_len.restype = guint16
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 17
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_generic_tlv_value'):
        continue
    get_generic_tlv_value = _lib.get_generic_tlv_value
    get_generic_tlv_value.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_value.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 18
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_generic_tlv_nonconst_value'):
        continue
    get_generic_tlv_nonconst_value = _lib.get_generic_tlv_nonconst_value
    get_generic_tlv_nonconst_value.argtypes = [gpointer, gconstpointer]
    get_generic_tlv_nonconst_value.restype = gpointer
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 19
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_generic_tlv_totalsize'):
        continue
    get_generic_tlv_totalsize = _lib.get_generic_tlv_totalsize
    get_generic_tlv_totalsize.argtypes = [gsize]
    get_generic_tlv_totalsize.restype = guint16
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 20
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'is_valid_generic_tlv_packet'):
        continue
    is_valid_generic_tlv_packet = _lib.is_valid_generic_tlv_packet
    is_valid_generic_tlv_packet.argtypes = [gconstpointer, gconstpointer]
    is_valid_generic_tlv_packet.restype = gboolean
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 21
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_generic_tlv_first'):
        continue
    get_generic_tlv_first = _lib.get_generic_tlv_first
    get_generic_tlv_first.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_first.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 22
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_generic_tlv_next'):
        continue
    get_generic_tlv_next = _lib.get_generic_tlv_next
    get_generic_tlv_next.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_next.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 23
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'find_next_generic_tlv_type'):
        continue
    find_next_generic_tlv_type = _lib.find_next_generic_tlv_type
    find_next_generic_tlv_type.argtypes = [gconstpointer, guint16, gconstpointer]
    find_next_generic_tlv_type.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 24
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'set_generic_tlv_type'):
        continue
    set_generic_tlv_type = _lib.set_generic_tlv_type
    set_generic_tlv_type.argtypes = [gpointer, guint16, gconstpointer]
    set_generic_tlv_type.restype = None
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 25
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'set_generic_tlv_len'):
        continue
    set_generic_tlv_len = _lib.set_generic_tlv_len
    set_generic_tlv_len.argtypes = [gpointer, guint16, gconstpointer]
    set_generic_tlv_len.restype = None
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 26
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'set_generic_tlv_value'):
        continue
    set_generic_tlv_value = _lib.set_generic_tlv_value
    set_generic_tlv_value.argtypes = [gpointer, POINTER(None), guint16, gconstpointer]
    set_generic_tlv_value.restype = None
    break

# include/netio.h: 28
class struct__NetIO(Structure):
    pass

NetIO = struct__NetIO # include/netio.h: 23

struct__NetIO.__slots__ = [
    'giosock',
    '_signframe',
    '_cryptframe',
    '_compressframe',
    '_maxpktsize',
    'bindaddr',
    'getfd',
    'getmaxpktsize',
    'setmaxpktsize',
    'sendaframeset',
    'sendframesets',
    'recvframesets',
    'signframe',
    'cryptframe',
    'compressframe',
    'set_signframe',
    'set_cryptframe',
    'set_compressframe',
    'finalize',
]
struct__NetIO._fields_ = [
    ('giosock', POINTER(GIOChannel)),
    ('_signframe', POINTER(SignFrame)),
    ('_cryptframe', POINTER(Frame)),
    ('_compressframe', POINTER(Frame)),
    ('_maxpktsize', gint),
    ('bindaddr', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO), POINTER(NetAddr))),
    ('getfd', CFUNCTYPE(UNCHECKED(gint), POINTER(NetIO))),
    ('getmaxpktsize', CFUNCTYPE(UNCHECKED(gsize), POINTER(NetIO))),
    ('setmaxpktsize', CFUNCTYPE(UNCHECKED(gsize), POINTER(NetIO), gsize)),
    ('sendaframeset', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), POINTER(NetAddr), POINTER(FrameSet))),
    ('sendframesets', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), POINTER(NetAddr), POINTER(GSList))),
    ('recvframesets', CFUNCTYPE(UNCHECKED(POINTER(GSList)), POINTER(NetIO), POINTER(POINTER(NetAddr)))),
    ('signframe', CFUNCTYPE(UNCHECKED(POINTER(SignFrame)), POINTER(NetIO))),
    ('cryptframe', CFUNCTYPE(UNCHECKED(POINTER(Frame)), POINTER(NetIO))),
    ('compressframe', CFUNCTYPE(UNCHECKED(POINTER(Frame)), POINTER(NetIO))),
    ('set_signframe', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), POINTER(SignFrame))),
    ('set_cryptframe', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), POINTER(Frame))),
    ('set_compressframe', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), POINTER(Frame))),
    ('finalize', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO))),
]

# include/netio.h: 82
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netio_new'):
        continue
    netio_new = _lib.netio_new
    netio_new.argtypes = [gsize]
    netio_new.restype = POINTER(NetIO)
    break

# include/netgsource.h: 36
class struct__NetGSource(Structure):
    pass

NetGSource = struct__NetGSource # include/netgsource.h: 24

NetGSourceDispatch = CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetGSource), POINTER(FrameSet), POINTER(NetAddr), gpointer) # include/netgsource.h: 27

struct__NetGSource.__slots__ = [
    'baseclass',
    '_gfd',
    '_socket',
    '_gsourceid',
    '_userdata',
    '_gsfuncs',
    '_netio',
    '_dispatchers',
    '_finalize',
    'addDispatch',
]
struct__NetGSource._fields_ = [
    ('baseclass', GSource),
    ('_gfd', GPollFD),
    ('_socket', c_int),
    ('_gsourceid', gint),
    ('_userdata', gpointer),
    ('_gsfuncs', POINTER(GSourceFuncs)),
    ('_netio', POINTER(NetIO)),
    ('_dispatchers', POINTER(GHashTable)),
    ('_finalize', GDestroyNotify),
    ('addDispatch', CFUNCTYPE(UNCHECKED(None), POINTER(NetGSource), guint16, NetGSourceDispatch)),
]

# include/netgsource.h: 48
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netgsource_new'):
        continue
    netgsource_new = _lib.netgsource_new
    netgsource_new.argtypes = [POINTER(NetIO), GDestroyNotify, gint, gboolean, POINTER(GMainContext), gsize, gpointer]
    netgsource_new.restype = POINTER(NetGSource)
    break

# /home/alanr/monitor/src/include/hblistener.h: 31
class struct__HbListener(Structure):
    pass

HbListener = struct__HbListener # /home/alanr/monitor/src/include/hblistener.h: 19

enum_anon_99 = c_int # /home/alanr/monitor/src/include/hblistener.h: 24

HbPacketsBeingReceived = 1 # /home/alanr/monitor/src/include/hblistener.h: 24

HbPacketsTimedOut = 2 # /home/alanr/monitor/src/include/hblistener.h: 24

HbNodeStatus = enum_anon_99 # /home/alanr/monitor/src/include/hblistener.h: 24

struct__HbListener.__slots__ = [
    'ref',
    'unref',
    '_finalize',
    'get_deadtime',
    'set_deadtime',
    'get_warntime',
    'set_warntime',
    '_expected_interval',
    '_warn_interval',
    'nexttime',
    'warntime',
    '_refcount',
    'listenaddr',
    'status',
]
struct__HbListener._fields_ = [
    ('ref', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener))),
    ('unref', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener))),
    ('_finalize', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener))),
    ('get_deadtime', CFUNCTYPE(UNCHECKED(guint64), POINTER(HbListener))),
    ('set_deadtime', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64)),
    ('get_warntime', CFUNCTYPE(UNCHECKED(guint64), POINTER(HbListener))),
    ('set_warntime', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64)),
    ('_expected_interval', guint64),
    ('_warn_interval', guint64),
    ('nexttime', guint64),
    ('warntime', guint64),
    ('_refcount', c_int),
    ('listenaddr', POINTER(NetAddr)),
    ('status', HbNodeStatus),
]

# /home/alanr/monitor/src/include/hblistener.h: 49
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hblistener_new'):
        continue
    hblistener_new = _lib.hblistener_new
    hblistener_new.argtypes = [POINTER(NetAddr), gsize]
    hblistener_new.restype = POINTER(HbListener)
    break

# /home/alanr/monitor/src/include/hblistener.h: 50
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hblistener_unlisten'):
        continue
    hblistener_unlisten = _lib.hblistener_unlisten
    hblistener_unlisten.argtypes = [POINTER(NetAddr)]
    hblistener_unlisten.restype = None
    break

# /home/alanr/monitor/src/include/hblistener.h: 51
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hblistener_set_deadtime_callback'):
        continue
    hblistener_set_deadtime_callback = _lib.hblistener_set_deadtime_callback
    hblistener_set_deadtime_callback.argtypes = [CFUNCTYPE(UNCHECKED(None), POINTER(HbListener))]
    hblistener_set_deadtime_callback.restype = None
    break

# /home/alanr/monitor/src/include/hblistener.h: 52
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hblistener_set_warntime_callback'):
        continue
    hblistener_set_warntime_callback = _lib.hblistener_set_warntime_callback
    hblistener_set_warntime_callback.argtypes = [CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64)]
    hblistener_set_warntime_callback.restype = None
    break

# /home/alanr/monitor/src/include/hblistener.h: 53
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hblistener_set_comealive_callback'):
        continue
    hblistener_set_comealive_callback = _lib.hblistener_set_comealive_callback
    hblistener_set_comealive_callback.argtypes = [CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64)]
    hblistener_set_comealive_callback.restype = None
    break

# /home/alanr/monitor/src/include/hblistener.h: 54
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hblistener_set_martian_callback'):
        continue
    hblistener_set_martian_callback = _lib.hblistener_set_martian_callback
    hblistener_set_martian_callback.argtypes = [CFUNCTYPE(UNCHECKED(None), POINTER(NetAddr))]
    hblistener_set_martian_callback.restype = None
    break

# /home/alanr/monitor/src/include/hblistener.h: 55
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hblistener_netgsource_dispatch'):
        continue
    hblistener_netgsource_dispatch = _lib.hblistener_netgsource_dispatch
    hblistener_netgsource_dispatch.argtypes = [POINTER(NetGSource), POINTER(FrameSet), POINTER(NetAddr), gpointer]
    hblistener_netgsource_dispatch.restype = gboolean
    break

# /home/alanr/monitor/src/include/hbsender.h: 26
class struct__HbSender(Structure):
    pass

HbSender = struct__HbSender # /home/alanr/monitor/src/include/hbsender.h: 20

struct__HbSender.__slots__ = [
    'ref',
    'unref',
    '_finalize',
    '_expected_interval',
    '_outmethod',
    '_sendaddr',
    '_refcount',
    'timeout_source',
]
struct__HbSender._fields_ = [
    ('ref', CFUNCTYPE(UNCHECKED(None), POINTER(HbSender))),
    ('unref', CFUNCTYPE(UNCHECKED(None), POINTER(HbSender))),
    ('_finalize', CFUNCTYPE(UNCHECKED(None), POINTER(HbSender))),
    ('_expected_interval', guint64),
    ('_outmethod', POINTER(NetIO)),
    ('_sendaddr', POINTER(NetAddr)),
    ('_refcount', c_int),
    ('timeout_source', guint),
]

# /home/alanr/monitor/src/include/hbsender.h: 38
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hbsender_new'):
        continue
    hbsender_new = _lib.hbsender_new
    hbsender_new.argtypes = [POINTER(NetAddr), POINTER(NetIO), guint, gsize]
    hbsender_new.restype = POINTER(HbSender)
    break

# /home/alanr/monitor/src/include/hbsender.h: 39
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'hbsender_stopsend'):
        continue
    hbsender_stopsend = _lib.hbsender_stopsend
    hbsender_stopsend.argtypes = [POINTER(NetAddr)]
    hbsender_stopsend.restype = None
    break

# /home/alanr/monitor/src/include/intframe.h: 27
class struct__IntFrame(Structure):
    pass

IntFrame = struct__IntFrame # /home/alanr/monitor/src/include/intframe.h: 23

struct__IntFrame.__slots__ = [
    'baseclass',
    'intlength',
    'getint',
    'setint',
    '_value',
]
struct__IntFrame._fields_ = [
    ('baseclass', Frame),
    ('intlength', CFUNCTYPE(UNCHECKED(c_int), POINTER(IntFrame))),
    ('getint', CFUNCTYPE(UNCHECKED(guint64), POINTER(IntFrame))),
    ('setint', CFUNCTYPE(UNCHECKED(None), POINTER(IntFrame), guint64)),
    ('_value', guint64),
]

# /home/alanr/monitor/src/include/intframe.h: 35
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'intframe_new'):
        continue
    intframe_new = _lib.intframe_new
    intframe_new.argtypes = [guint16, c_int]
    intframe_new.restype = POINTER(IntFrame)
    break

# /home/alanr/monitor/src/include/intframe.h: 36
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'intframe_tlvconstructor'):
        continue
    intframe_tlvconstructor = _lib.intframe_tlvconstructor
    intframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    intframe_tlvconstructor.restype = POINTER(Frame)
    break

# /home/alanr/monitor/src/include/lldp.h: 107
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldp_chassis_id_type'):
        continue
    get_lldp_chassis_id_type = _lib.get_lldp_chassis_id_type
    get_lldp_chassis_id_type.argtypes = [gconstpointer, gconstpointer]
    get_lldp_chassis_id_type.restype = c_uint
    break

# /home/alanr/monitor/src/include/lldp.h: 108
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldp_chassis_id'):
        continue
    get_lldp_chassis_id = _lib.get_lldp_chassis_id
    get_lldp_chassis_id.argtypes = [gconstpointer, POINTER(gssize), gconstpointer]
    get_lldp_chassis_id.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/lldp.h: 109
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldp_port_id'):
        continue
    get_lldp_port_id = _lib.get_lldp_port_id
    get_lldp_port_id.argtypes = [gconstpointer, POINTER(gssize), gconstpointer]
    get_lldp_port_id.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/lldp.h: 110
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldp_port_id_type'):
        continue
    get_lldp_port_id_type = _lib.get_lldp_port_id_type
    get_lldp_port_id_type.argtypes = [gconstpointer, gconstpointer]
    get_lldp_port_id_type.restype = c_uint
    break

# /home/alanr/monitor/src/include/lldp.h: 112
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldptlv_type'):
        continue
    get_lldptlv_type = _lib.get_lldptlv_type
    get_lldptlv_type.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_type.restype = guint8
    break

# /home/alanr/monitor/src/include/lldp.h: 113
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldptlv_len'):
        continue
    get_lldptlv_len = _lib.get_lldptlv_len
    get_lldptlv_len.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_len.restype = gsize
    break

# /home/alanr/monitor/src/include/lldp.h: 114
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldptlv_first'):
        continue
    get_lldptlv_first = _lib.get_lldptlv_first
    get_lldptlv_first.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_first.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/lldp.h: 115
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldptlv_next'):
        continue
    get_lldptlv_next = _lib.get_lldptlv_next
    get_lldptlv_next.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_next.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/lldp.h: 116
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldptlv_body'):
        continue
    get_lldptlv_body = _lib.get_lldptlv_body
    get_lldptlv_body.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_body.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/lldp.h: 117
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'find_next_lldptlv_type'):
        continue
    find_next_lldptlv_type = _lib.find_next_lldptlv_type
    find_next_lldptlv_type.argtypes = [gconstpointer, c_uint, gconstpointer]
    find_next_lldptlv_type.restype = gconstpointer
    break

# /home/alanr/monitor/src/include/lldp.h: 118
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'is_valid_lldp_packet'):
        continue
    is_valid_lldp_packet = _lib.is_valid_lldp_packet
    is_valid_lldp_packet.argtypes = [gconstpointer, gconstpointer]
    is_valid_lldp_packet.restype = gboolean
    break

# /home/alanr/monitor/src/include/netioudp.h: 26
class struct__NetIOudp(Structure):
    pass

NetIOudp = struct__NetIOudp # /home/alanr/monitor/src/include/netioudp.h: 21

struct__NetIOudp.__slots__ = [
    'baseclass',
    '_finalize',
]
struct__NetIOudp._fields_ = [
    ('baseclass', NetIO),
    ('_finalize', GDestroyNotify),
]

# /home/alanr/monitor/src/include/netioudp.h: 30
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'netioudp_new'):
        continue
    netioudp_new = _lib.netioudp_new
    netioudp_new.argtypes = [gsize]
    netioudp_new.restype = POINTER(NetIOudp)
    break

bpf_u_int32 = u_int # /usr/include/pcap/bpf.h: 68

# /usr/include/pcap/pcap.h: 81
class struct_pcap(Structure):
    pass

pcap_t = struct_pcap # /usr/include/pcap/pcap.h: 81

# /usr/include/pcap/pcap.h: 161
class struct_pcap_pkthdr(Structure):
    pass

struct_pcap_pkthdr.__slots__ = [
    'ts',
    'caplen',
    'len',
]
struct_pcap_pkthdr._fields_ = [
    ('ts', struct_timeval),
    ('caplen', bpf_u_int32),
    ('len', bpf_u_int32),
]

# include/pcap_min.h: 32
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'create_pcap_listener'):
        continue
    create_pcap_listener = _lib.create_pcap_listener
    create_pcap_listener.argtypes = [String, gboolean, c_uint]
    create_pcap_listener.restype = POINTER(pcap_t)
    break

# /home/alanr/monitor/src/include/pcap_GSource.h: 23
class struct__GSource_pcap(Structure):
    pass

GSource_pcap_t = struct__GSource_pcap # /home/alanr/monitor/src/include/pcap_GSource.h: 18

struct__GSource_pcap.__slots__ = [
    'gs',
    'gfd',
    'capture',
    'capturefd',
    'capturedev',
    'listenmask',
    'gsourceid',
    'userdata',
    'dispatch',
    'destroynote',
]
struct__GSource_pcap._fields_ = [
    ('gs', GSource),
    ('gfd', GPollFD),
    ('capture', POINTER(pcap_t)),
    ('capturefd', c_int),
    ('capturedev', String),
    ('listenmask', c_uint),
    ('gsourceid', gint),
    ('userdata', gpointer),
    ('dispatch', CFUNCTYPE(UNCHECKED(gboolean), POINTER(GSource_pcap_t), POINTER(pcap_t), gconstpointer, gconstpointer, POINTER(struct_pcap_pkthdr), String, gpointer)),
    ('destroynote', GDestroyNotify),
]

# /home/alanr/monitor/src/include/pcap_GSource.h: 44
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'g_source_pcap_new'):
        continue
    g_source_pcap_new = _lib.g_source_pcap_new
    g_source_pcap_new.argtypes = [String, c_uint, CFUNCTYPE(UNCHECKED(gboolean), POINTER(GSource_pcap_t), POINTER(pcap_t), gconstpointer, gconstpointer, POINTER(struct_pcap_pkthdr), String, gpointer), GDestroyNotify, gint, gboolean, POINTER(GMainContext), gsize, gpointer]
    g_source_pcap_new.restype = POINTER(GSource)
    break

# /home/alanr/monitor/src/include/pcap_GSource.h: 62
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'construct_pcap_frameset'):
        continue
    construct_pcap_frameset = _lib.construct_pcap_frameset
    construct_pcap_frameset.argtypes = [guint16, gconstpointer, gconstpointer, POINTER(struct_pcap_pkthdr), String]
    construct_pcap_frameset.restype = POINTER(FrameSet)
    break

# /home/alanr/monitor/src/include/pcap_min.h: 32
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'create_pcap_listener'):
        continue
    create_pcap_listener = _lib.create_pcap_listener
    create_pcap_listener.argtypes = [String, gboolean, c_uint]
    create_pcap_listener.restype = POINTER(pcap_t)
    break

# /home/alanr/monitor/src/include/proj_classes.h: 14
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_new'):
        continue
    proj_class_new = _lib.proj_class_new
    proj_class_new.argtypes = [gsize, String]
    proj_class_new.restype = gpointer
    break

# /home/alanr/monitor/src/include/proj_classes.h: 15
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_dissociate'):
        continue
    proj_class_dissociate = _lib.proj_class_dissociate
    proj_class_dissociate.argtypes = [gpointer]
    proj_class_dissociate.restype = None
    break

# /home/alanr/monitor/src/include/proj_classes.h: 16
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_free'):
        continue
    proj_class_free = _lib.proj_class_free
    proj_class_free.argtypes = [gpointer]
    proj_class_free.restype = None
    break

# /home/alanr/monitor/src/include/proj_classes.h: 17
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_register_object'):
        continue
    proj_class_register_object = _lib.proj_class_register_object
    proj_class_register_object.argtypes = [gpointer, String]
    proj_class_register_object.restype = None
    break

# /home/alanr/monitor/src/include/proj_classes.h: 18
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_castas'):
        continue
    proj_class_castas = _lib.proj_class_castas
    proj_class_castas.argtypes = [gpointer, String]
    proj_class_castas.restype = gpointer
    break

# /home/alanr/monitor/src/include/proj_classes.h: 19
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_register_subclassed'):
        continue
    proj_class_register_subclassed = _lib.proj_class_register_subclassed
    proj_class_register_subclassed.argtypes = [gpointer, String]
    proj_class_register_subclassed.restype = None
    break

# /home/alanr/monitor/src/include/proj_classes.h: 20
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_quark_add_superclass_relationship'):
        continue
    proj_class_quark_add_superclass_relationship = _lib.proj_class_quark_add_superclass_relationship
    proj_class_quark_add_superclass_relationship.argtypes = [GQuark, GQuark]
    proj_class_quark_add_superclass_relationship.restype = None
    break

# /home/alanr/monitor/src/include/proj_classes.h: 21
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_quark_is_a'):
        continue
    proj_class_quark_is_a = _lib.proj_class_quark_is_a
    proj_class_quark_is_a.argtypes = [GQuark, GQuark]
    proj_class_quark_is_a.restype = gboolean
    break

# /home/alanr/monitor/src/include/proj_classes.h: 22
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_classname'):
        continue
    proj_class_classname = _lib.proj_class_classname
    proj_class_classname.argtypes = [gconstpointer]
    if sizeof(c_int) == sizeof(c_void_p):
        proj_class_classname.restype = ReturnString
    else:
        proj_class_classname.restype = String
        proj_class_classname.errcheck = ReturnString
    break

# /home/alanr/monitor/src/include/proj_classes.h: 25
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'proj_class_dump_live_objects'):
        continue
    proj_class_dump_live_objects = _lib.proj_class_dump_live_objects
    proj_class_dump_live_objects.argtypes = []
    proj_class_dump_live_objects.restype = None
    break

# /home/alanr/monitor/src/include/seqnoframe.h: 25
class struct__SeqnoFrame(Structure):
    pass

SeqnoFrame = struct__SeqnoFrame # /home/alanr/monitor/src/include/seqnoframe.h: 18

struct__SeqnoFrame.__slots__ = [
    'baseclass',
    'getreqid',
    'getqid',
    'setreqid',
    'setqid',
    '_reqid',
    '_qid',
]
struct__SeqnoFrame._fields_ = [
    ('baseclass', Frame),
    ('getreqid', CFUNCTYPE(UNCHECKED(guint64), POINTER(SeqnoFrame))),
    ('getqid', CFUNCTYPE(UNCHECKED(guint16), POINTER(SeqnoFrame))),
    ('setreqid', CFUNCTYPE(UNCHECKED(None), POINTER(SeqnoFrame), guint64)),
    ('setqid', CFUNCTYPE(UNCHECKED(None), POINTER(SeqnoFrame), guint16)),
    ('_reqid', guint64),
    ('_qid', guint16),
]

# /home/alanr/monitor/src/include/seqnoframe.h: 34
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'seqnoframe_new'):
        continue
    seqnoframe_new = _lib.seqnoframe_new
    seqnoframe_new.argtypes = [guint16, c_int]
    seqnoframe_new.restype = POINTER(SeqnoFrame)
    break

# /home/alanr/monitor/src/include/seqnoframe.h: 35
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'seqnoframe_tlvconstructor'):
        continue
    seqnoframe_tlvconstructor = _lib.seqnoframe_tlvconstructor
    seqnoframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    seqnoframe_tlvconstructor.restype = POINTER(Frame)
    break

bool_t = c_int # /home/alanr/monitor/src/include/server_dump.h: 10

# /home/alanr/monitor/src/include/server_dump.h: 11
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'dump_cdp_packet'):
        continue
    dump_cdp_packet = _lib.dump_cdp_packet
    dump_cdp_packet.argtypes = [POINTER(None), POINTER(None)]
    dump_cdp_packet.restype = None
    break

# /home/alanr/monitor/src/include/server_dump.h: 12
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'dump_lldp_packet'):
        continue
    dump_lldp_packet = _lib.dump_lldp_packet
    dump_lldp_packet.argtypes = [POINTER(None), POINTER(None)]
    dump_lldp_packet.restype = None
    break

# /home/alanr/monitor/src/include/server_dump.h: 13
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'is_all_ascii'):
        continue
    is_all_ascii = _lib.is_all_ascii
    is_all_ascii.argtypes = [POINTER(None), POINTER(None)]
    is_all_ascii.restype = bool_t
    break

# /home/alanr/monitor/src/include/server_dump.h: 14
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'dump_mem'):
        continue
    dump_mem = _lib.dump_mem
    dump_mem.argtypes = [POINTER(None), POINTER(None)]
    dump_mem.restype = None
    break

# include/pcap_min.h: 32
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'create_pcap_listener'):
        continue
    create_pcap_listener = _lib.create_pcap_listener
    create_pcap_listener.argtypes = [String, gboolean, c_uint]
    create_pcap_listener.restype = POINTER(pcap_t)
    break

# include/pcap_GSource.h: 44
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'g_source_pcap_new'):
        continue
    g_source_pcap_new = _lib.g_source_pcap_new
    g_source_pcap_new.argtypes = [String, c_uint, CFUNCTYPE(UNCHECKED(gboolean), POINTER(GSource_pcap_t), POINTER(pcap_t), gconstpointer, gconstpointer, POINTER(struct_pcap_pkthdr), String, gpointer), GDestroyNotify, gint, gboolean, POINTER(GMainContext), gsize, gpointer]
    g_source_pcap_new.restype = POINTER(GSource)
    break

# include/pcap_GSource.h: 62
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'construct_pcap_frameset'):
        continue
    construct_pcap_frameset = _lib.construct_pcap_frameset
    construct_pcap_frameset.argtypes = [guint16, gconstpointer, gconstpointer, POINTER(struct_pcap_pkthdr), String]
    construct_pcap_frameset.restype = POINTER(FrameSet)
    break

# /home/alanr/monitor/src/include/switchdiscovery.h: 23
class struct__SwitchDiscovery(Structure):
    pass

SwitchDiscovery = struct__SwitchDiscovery # /home/alanr/monitor/src/include/switchdiscovery.h: 21

struct__SwitchDiscovery.__slots__ = [
    'baseclass',
    'source',
    'finalize',
    'switchid',
    'switchidlen',
    'portid',
    'portidlen',
]
struct__SwitchDiscovery._fields_ = [
    ('baseclass', Discovery),
    ('source', POINTER(GSource)),
    ('finalize', CFUNCTYPE(UNCHECKED(None), POINTER(Discovery))),
    ('switchid', gpointer),
    ('switchidlen', gssize),
    ('portid', gpointer),
    ('portidlen', gssize),
]

# /home/alanr/monitor/src/include/switchdiscovery.h: 33
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'switchdiscovery_new'):
        continue
    switchdiscovery_new = _lib.switchdiscovery_new
    switchdiscovery_new.argtypes = [gsize, String, guint, gint, POINTER(GMainContext)]
    switchdiscovery_new.restype = POINTER(SwitchDiscovery)
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 14
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_get_guint8'):
        continue
    tlv_get_guint8 = _lib.tlv_get_guint8
    tlv_get_guint8.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint8.restype = guint8
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 15
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_get_guint16'):
        continue
    tlv_get_guint16 = _lib.tlv_get_guint16
    tlv_get_guint16.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint16.restype = guint16
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 16
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_get_guint24'):
        continue
    tlv_get_guint24 = _lib.tlv_get_guint24
    tlv_get_guint24.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint24.restype = guint32
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 17
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_get_guint32'):
        continue
    tlv_get_guint32 = _lib.tlv_get_guint32
    tlv_get_guint32.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint32.restype = guint32
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 18
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_get_guint64'):
        continue
    tlv_get_guint64 = _lib.tlv_get_guint64
    tlv_get_guint64.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint64.restype = guint64
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 19
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_set_guint8'):
        continue
    tlv_set_guint8 = _lib.tlv_set_guint8
    tlv_set_guint8.argtypes = [POINTER(None), guint8, POINTER(None)]
    tlv_set_guint8.restype = None
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 20
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_set_guint16'):
        continue
    tlv_set_guint16 = _lib.tlv_set_guint16
    tlv_set_guint16.argtypes = [POINTER(None), guint16, POINTER(None)]
    tlv_set_guint16.restype = None
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 21
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_set_guint24'):
        continue
    tlv_set_guint24 = _lib.tlv_set_guint24
    tlv_set_guint24.argtypes = [POINTER(None), guint32, POINTER(None)]
    tlv_set_guint24.restype = None
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 22
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_set_guint32'):
        continue
    tlv_set_guint32 = _lib.tlv_set_guint32
    tlv_set_guint32.argtypes = [POINTER(None), guint32, POINTER(None)]
    tlv_set_guint32.restype = None
    break

# /home/alanr/monitor/src/include/tlvhelper.h: 23
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'tlv_set_guint64'):
        continue
    tlv_set_guint64 = _lib.tlv_set_guint64
    tlv_set_guint64.argtypes = [POINTER(None), guint64, POINTER(None)]
    tlv_set_guint64.restype = None
    break

# /home/alanr/monitor/src/include/unknownframe.h: 22
class struct__UnknownFrame(Structure):
    pass

UnknownFrame = struct__UnknownFrame # /home/alanr/monitor/src/include/unknownframe.h: 16

struct__UnknownFrame.__slots__ = [
    'baseclass',
]
struct__UnknownFrame._fields_ = [
    ('baseclass', Frame),
]

# /home/alanr/monitor/src/include/unknownframe.h: 26
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'unknownframe_new'):
        continue
    unknownframe_new = _lib.unknownframe_new
    unknownframe_new.argtypes = [guint16]
    unknownframe_new.restype = POINTER(UnknownFrame)
    break

# /home/alanr/monitor/src/include/unknownframe.h: 27
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'unknownframe_tlvconstructor'):
        continue
    unknownframe_tlvconstructor = _lib.unknownframe_tlvconstructor
    unknownframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    unknownframe_tlvconstructor.restype = POINTER(Frame)
    break

# /home/alanr/monitor/src/include/address_family_numbers.h: 23
try:
    ADDR_FAMILY_IPV4 = 1
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 24
try:
    ADDR_FAMILY_IPV6 = 2
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 25
try:
    ADDR_FAMILY_NSAP = 3
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 26
try:
    ADDR_FAMILY_HDLC = 4
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 27
try:
    ADDR_FAMILY_BBN1822 = 5
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 28
try:
    ADDR_FAMILY_802 = 6
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 29
try:
    ADDR_FAMILY_E163 = 7
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 30
try:
    ADDR_FAMILY_E164 = 8
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 31
try:
    ADDR_FAMILY_F69 = 9
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 32
try:
    ADDR_FAMILY_X121 = 10
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 33
try:
    ADDR_FAMILY_IPX = 11
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 34
try:
    ADDR_FAMILY_APPLETALK = 12
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 35
try:
    ADDR_FAMILY_DECNET = 13
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 36
try:
    ADDR_FAMILY_BANYANVINES = 14
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 37
try:
    ADDR_FAMILY_E164_NSAP = 15
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 38
try:
    ADDR_FAMILY_DNS = 16
except:
    pass

# include/frame.h: 48
try:
    FRAME_INITSIZE = 4
except:
    pass

# include/projectcommon.h: 13
def DIMOF(a):
    return (sizeof(a) / sizeof((a [0])))

# include/projectcommon.h: 14
def MALLOC0(nbytes):
    return (g_try_malloc0 (nbytes))

# include/projectcommon.h: 15
def MALLOC(nbytes):
    return (g_try_malloc (nbytes))

# include/projectcommon.h: 18
def FREE(m):
    return (g_free (m))

# include/projectcommon.h: 21
try:
    FMT_64BIT = '%ll'
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 19
try:
    CDP_TLV_DEVID = 1
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 21
try:
    CDP_TLV_ADDRESS = 2
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 22
try:
    CDP_TLV_PORTID = 3
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 24
try:
    CDP_TLV_CAPS = 4
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 25
try:
    CDP_TLV_VERS = 5
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 26
try:
    CDP_TLV_PLATFORM = 6
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 27
try:
    CDP_TLV_IPPREFIX = 7
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 28
try:
    CDP_TLV_HELLO = 8
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 29
try:
    CDP_TLV_VTPDOMAIN = 9
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 30
try:
    CDP_TLV_NATIVEVLAN = 10
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 31
try:
    CDP_TLV_DUPLEX = 11
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 32
try:
    CDP_TLV_APPLID = 14
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 33
try:
    CDP_TLV_POWER = 16
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 45
try:
    CDP_CAPMASK_ROUTER = 1
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 46
try:
    CDP_CAPMASK_TBBRIDGE = 2
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 47
try:
    CDP_CAPMASK_SPBRIDGE = 4
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 48
try:
    CDP_CAPMASK_SWITCH = 8
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 49
try:
    CDP_CAPMASK_HOST = 16
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 50
try:
    CDP_CAPMASK_IGMPFILTER = 32
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 51
try:
    CDP_CAPMASK_REPEATER = 64
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 49
try:
    FRAMETYPE_END = 0
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 67
try:
    FRAMETYPE_SIG = 1
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 84
try:
    FRAMETYPE_CRYPT = 2
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 103
try:
    FRAMETYPE_COMPRESS = 3
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 124
try:
    FRAMETYPE_REQID = 4
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 144
try:
    FRAMETYPE_REPLYID = 5
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 159
try:
    FRAMETYPE_PKTDATA = 6
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 175
try:
    FRAMETYPE_WALLCLOCK = 7
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 189
try:
    FRAMETYPE_INTERFACE = 8
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 207
try:
    FRAMETYPE_IPADDR = 9
except:
    pass

# /home/alanr/monitor/src/include/frameformats.h: 226
try:
    FRAMETYPE_MACADDR = 9
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 39
try:
    FRAMESET_INITSIZE = 6
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 57
try:
    FRAMESETTYPE_NONEOFTHEABOVE = 0
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 58
try:
    FRAMESETTYPE_HEARTBEAT = 1
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 59
try:
    FRAMESETTYPE_NAK = 2
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 60
try:
    FRAMESETTYPE_PING = 3
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 61
try:
    FRAMESETTYPE_PONG = 4
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 63
try:
    FRAMESETTYPE_HBDEAD = 16
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 64
try:
    FRAMESETTYPE_CLIENTCONFIG = 17
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 65
try:
    FRAMESETTYPE_SWDISCOVER = 18
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 66
try:
    FRAMESETTYPE_LOCALNETDISCOVER = 19
except:
    pass

# /home/alanr/monitor/src/include/frameset.h: 67
try:
    FRAMESETTYPE_ARPDISCOVER = 20
except:
    pass

# /home/alanr/monitor/src/include/hblistener.h: 47
try:
    DEFAULT_DEADTIME = 60
except:
    pass

# /home/alanr/monitor/src/include/hbsender.h: 36
try:
    DEFAULT_DEADTIME = 60
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 22
try:
    LLDP_INVAL = 65535
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 29
try:
    LLDP_TLV_END = 0
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 30
try:
    LLDP_TLV_CHID = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 31
try:
    LLDP_TLV_PID = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 32
try:
    LLDP_TLV_TTL = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 33
try:
    LLDP_TLV_PORT_DESCR = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 34
try:
    LLDP_TLV_SYS_NAME = 5
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 35
try:
    LLDP_TLV_SYS_DESCR = 6
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 36
try:
    LLDP_TLV_SYS_CAPS = 7
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 37
try:
    LLDP_TLV_ORG_SPECIFIC = 127
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 45
try:
    LLDP_CHIDTYPE_COMPONENT = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 47
try:
    LLDP_CHIDTYPE_ALIAS = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 48
try:
    LLDP_CHIDTYPE_PORT = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 50
try:
    LLDP_CHIDTYPE_MACADDR = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 51
try:
    LLDP_CHIDTYPE_NETADDR = 5
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 52
try:
    LLDP_CHIDTYPE_IFNAME = 6
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 53
try:
    LLDP_CHIDTYPE_LOCAL = 7
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 61
try:
    LLDP_PIDTYPE_ALIAS = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 62
try:
    LLDP_PIDTYPE_COMPONENT = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 64
try:
    LLDP_PIDTYPE_MACADDR = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 65
try:
    LLDP_PIDTYPE_NETADDR = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 66
try:
    LLDP_PIDTYPE_IFNAME = 5
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 67
try:
    LLDP_PIDTYPE_CIRCUITID = 6
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 68
try:
    LLDP_PIDTYPE_LOCAL = 7
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 75
try:
    LLDP_CAPMASK_REPEATER = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 76
try:
    LLDP_CAPMASK_BRIDGE = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 77
try:
    LLDP_CAPMASK_WLAN_AP = 8
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 78
try:
    LLDP_CAPMASK_ROUTER = 16
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 79
try:
    LLDP_CAPMASK_PHONE = 32
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 80
try:
    LLDP_CAPMASK_DOCSIS = 64
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 81
try:
    LLDP_CAPMASK_STATION = 128
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 89
try:
    LLDP_ORG802_1_VLAN_PVID = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 90
try:
    LLDP_ORG802_1_VLAN_PORTPROTO = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 91
try:
    LLDP_ORG802_1_VLAN_NAME = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 92
try:
    LLDP_ORG802_1_VLAN_PROTOID = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 100
try:
    LLDP_ORG802_3_PHY_CONFIG = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 101
try:
    LLDP_ORG802_3_POWERVIAMDI = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 102
try:
    LLDP_ORG802_3_LINKAGG = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 103
try:
    LLDP_ORG802_3_MTU = 4
except:
    pass

# include/pcap_min.h: 27
try:
    ENABLE_LLDP = 1
except:
    pass

# include/pcap_min.h: 29
try:
    ENABLE_CDP = 2
except:
    pass

# /home/alanr/monitor/src/include/pcap_min.h: 27
try:
    ENABLE_LLDP = 1
except:
    pass

# /home/alanr/monitor/src/include/pcap_min.h: 29
try:
    ENABLE_CDP = 2
except:
    pass

# include/pcap_min.h: 27
try:
    ENABLE_LLDP = 1
except:
    pass

# include/pcap_min.h: 29
try:
    ENABLE_CDP = 2
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 20
try:
    TLV_DTYPE_BINARY = 1
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 21
try:
    TLV_DTYPE_UINT8 = 2
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 22
try:
    TLV_DTYPE_UINT16 = 3
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 23
try:
    TLV_DTYPE_UINT32 = 4
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 24
try:
    TLV_DTYPE_UINT64 = 5
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 25
try:
    TLV_DTYPE_OUI = 6
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 26
try:
    TLV_DTYPE_MACADDR = 7
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 27
try:
    TLV_DTYPE_IPV4ADDR = 8
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 28
try:
    TLV_DTYPE_IPV6ADDR = 9
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 29
try:
    TLV_DTYPE_GENADDR = 10
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 30
try:
    TLV_DTYPE_LLCHASSIS = 11
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 31
try:
    TLV_DTYPE_LLPORTID = 12
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 32
try:
    TLV_DTYPE_LLCAPS = 13
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 33
try:
    TLV_DTYPE_LLMGMTADDR = 14
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 34
try:
    TLV_DTYPE_LL8021_VLANID = 15
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 35
try:
    TLV_DTYPE_LL8021_PPVLANID = 16
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 36
try:
    TLV_DTYPE_LL8021_VLANNAME = 17
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 37
try:
    TLV_DTYPE_LL8021_PROTOID = 18
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 38
try:
    TLV_DTYPE_LL8023_MACPHY = 19
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 39
try:
    TLV_DTYPE_LL8023_POWER = 20
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 40
try:
    TLV_DTYPE_LL8023_LINKAGGR = 21
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 41
try:
    TLV_DTYPE_LL8023_MTU = 22
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 42
try:
    TLV_DTYPE_FSTYPE = 23
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 43
try:
    TLV_DTYPE_FSFLAGS = 24
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 44
try:
    TLV_DTYPE_FRAMETYPE = 25
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 45
try:
    TLV_DTYPE_FR_REQTYPE = 26
except:
    pass

_FrameSet = struct__FrameSet # /home/alanr/monitor/src/include/frameset.h: 27

_Frame = struct__Frame # include/frame.h: 29

_NetAddr = struct__NetAddr # include/netaddr.h: 25

_AddrFrame = struct__AddrFrame # /home/alanr/monitor/src/include/addrframe.h: 25

_CstringFrame = struct__CstringFrame # /home/alanr/monitor/src/include/cstringframe.h: 23

_FrameTypeToFrame = struct__FrameTypeToFrame # /home/alanr/monitor/src/include/decode_packet.h: 20

_Discovery = struct__Discovery # /home/alanr/monitor/src/include/discovery.h: 32

_SignFrame = struct__SignFrame # include/signframe.h: 27

_NetIO = struct__NetIO # include/netio.h: 28

_NetGSource = struct__NetGSource # include/netgsource.h: 36

_HbListener = struct__HbListener # /home/alanr/monitor/src/include/hblistener.h: 31

_HbSender = struct__HbSender # /home/alanr/monitor/src/include/hbsender.h: 26

_IntFrame = struct__IntFrame # /home/alanr/monitor/src/include/intframe.h: 27

_NetIOudp = struct__NetIOudp # /home/alanr/monitor/src/include/netioudp.h: 26

_GSource_pcap = struct__GSource_pcap # /home/alanr/monitor/src/include/pcap_GSource.h: 23

_SeqnoFrame = struct__SeqnoFrame # /home/alanr/monitor/src/include/seqnoframe.h: 25

_SwitchDiscovery = struct__SwitchDiscovery # /home/alanr/monitor/src/include/switchdiscovery.h: 23

_UnknownFrame = struct__UnknownFrame # /home/alanr/monitor/src/include/unknownframe.h: 22

# No inserted files

