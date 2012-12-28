'''Wrapper for address_family_numbers.h

Generated with:
/usr/local/bin/ctypesgen.py --cpp=gcc -E -D__signed__=signed -o AssimCtypes.py -I../include -L ../../bin/clientlib -L /home/alanr/monitor/bin/clientlib -l libassimilationclientlib.so -I/usr/include/glib-2.0 -I/usr/lib/i386-linux-gnu/glib-2.0/include -L /usr/lib/i386-linux-gnu -lglib-2.0 ../include/address_family_numbers.h ../include/addrframe.h ../include/assimobj.h ../include/authlistener.h ../include/cdp.h ../include/cmalib.h ../include/compressframe.h ../include/configcontext.h ../include/cryptframe.h ../include/cstringframe.h ../include/discovery.h ../include/frame.h ../include/frameset.h ../include/framesettypes.h ../include/frametypes.h ../include/fsprotocol.h ../include/fsqueue.h ../include/generic_tlv_min.h ../include/hblistener.h ../include/hbsender.h ../include/intframe.h ../include/ipportframe.h ../include/jsondiscovery.h ../include/listener.h ../include/lldp.h ../include/misc.h ../include/nanoprobe.h ../include/netaddr.h ../include/netgsource.h ../include/netio.h ../include/netioudp.h ../include/nvpairframe.h ../include/packetdecoder.h ../include/pcap_GSource.h ../include/pcap_min.h ../include/proj_classes.h ../include/projectcommon.h ../include/reliableudp.h ../include/seqnoframe.h ../include/server_dump.h ../include/signframe.h ../include/switchdiscovery.h ../include/tlvhelper.h ../include/tlv_valuetypes.h ../include/unknownframe.h /usr/include/glib-2.0/glib/gslist.h

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
_libdirs = ['../../bin/clientlib', '/home/alanr/monitor/bin/clientlib', '/usr/lib/i386-linux-gnu']

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

add_library_search_dirs(['../../bin/clientlib', '/home/alanr/monitor/bin/clientlib', '/usr/lib/i386-linux-gnu'])

# Begin libraries

_libs["libassimilationclientlib.so"] = load_library("libassimilationclientlib.so")
_libs["glib-2.0"] = load_library("glib-2.0")

# 2 libraries
# End libraries

# No modules

NULL = None # <built-in>

guint8 = c_ubyte # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 39

guint16 = c_ushort # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 41

guint32 = c_uint # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 46

gint64 = c_longlong # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 52

guint64 = c_ulonglong # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 53

gssize = c_int # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 65

gsize = c_uint # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 66

GPid = c_int # /usr/lib/i386-linux-gnu/glib-2.0/include/glibconfig.h: 231

__u_char = c_ubyte # /usr/include/i386-linux-gnu/bits/types.h: 31

__u_short = c_uint # /usr/include/i386-linux-gnu/bits/types.h: 32

__u_int = c_uint # /usr/include/i386-linux-gnu/bits/types.h: 33

__time_t = c_long # /usr/include/i386-linux-gnu/bits/types.h: 149

__suseconds_t = c_long # /usr/include/i386-linux-gnu/bits/types.h: 151

__socklen_t = c_uint # /usr/include/i386-linux-gnu/bits/types.h: 192

gchar = c_char # /usr/include/glib-2.0/glib/gtypes.h: 47

gint = c_int # /usr/include/glib-2.0/glib/gtypes.h: 50

gboolean = gint # /usr/include/glib-2.0/glib/gtypes.h: 51

gushort = c_ushort # /usr/include/glib-2.0/glib/gtypes.h: 54

guint = c_uint # /usr/include/glib-2.0/glib/gtypes.h: 56

gpointer = POINTER(None) # /usr/include/glib-2.0/glib/gtypes.h: 78

gconstpointer = POINTER(None) # /usr/include/glib-2.0/glib/gtypes.h: 79

GCompareFunc = CFUNCTYPE(UNCHECKED(gint), gconstpointer, gconstpointer) # /usr/include/glib-2.0/glib/gtypes.h: 81

GCompareDataFunc = CFUNCTYPE(UNCHECKED(gint), gconstpointer, gconstpointer, gpointer) # /usr/include/glib-2.0/glib/gtypes.h: 83

GDestroyNotify = CFUNCTYPE(UNCHECKED(None), gpointer) # /usr/include/glib-2.0/glib/gtypes.h: 88

GFunc = CFUNCTYPE(UNCHECKED(None), gpointer, gpointer) # /usr/include/glib-2.0/glib/gtypes.h: 89

GQuark = guint32 # /usr/include/glib-2.0/glib/gquark.h: 38

# /usr/include/glib-2.0/glib/gerror.h: 45
class struct__GError(Structure):
    pass

GError = struct__GError # /usr/include/glib-2.0/glib/gerror.h: 43

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
if hasattr(_libs['libassimilationclientlib.so'], 'g_free'):
    g_free = _libs['libassimilationclientlib.so'].g_free
    g_free.argtypes = [gpointer]
    g_free.restype = None

# /usr/include/glib-2.0/glib/gmem.h: 77
if hasattr(_libs['libassimilationclientlib.so'], 'g_try_malloc'):
    g_try_malloc = _libs['libassimilationclientlib.so'].g_try_malloc
    g_try_malloc.argtypes = [gsize]
    g_try_malloc.restype = gpointer

# /usr/include/glib-2.0/glib/gmem.h: 78
if hasattr(_libs['libassimilationclientlib.so'], 'g_try_malloc0'):
    g_try_malloc0 = _libs['libassimilationclientlib.so'].g_try_malloc0
    g_try_malloc0.argtypes = [gsize]
    g_try_malloc0.restype = gpointer

# /usr/include/glib-2.0/glib/glist.h: 40
class struct__GList(Structure):
    pass

GList = struct__GList # /usr/include/glib-2.0/glib/glist.h: 38

struct__GList.__slots__ = [
    'data',
    'next',
    'prev',
]
struct__GList._fields_ = [
    ('data', gpointer),
    ('next', POINTER(GList)),
    ('prev', POINTER(GList)),
]

enum_anon_48 = c_int # /usr/include/glib-2.0/glib/gchecksum.h: 50

G_CHECKSUM_MD5 = 0 # /usr/include/glib-2.0/glib/gchecksum.h: 50

G_CHECKSUM_SHA1 = (G_CHECKSUM_MD5 + 1) # /usr/include/glib-2.0/glib/gchecksum.h: 50

G_CHECKSUM_SHA256 = (G_CHECKSUM_SHA1 + 1) # /usr/include/glib-2.0/glib/gchecksum.h: 50

GChecksumType = enum_anon_48 # /usr/include/glib-2.0/glib/gchecksum.h: 50

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

# /usr/include/glib-2.0/glib/gslist.h: 48
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_alloc'):
    g_slist_alloc = _libs['libassimilationclientlib.so'].g_slist_alloc
    g_slist_alloc.argtypes = []
    g_slist_alloc.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 49
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_free'):
    g_slist_free = _libs['libassimilationclientlib.so'].g_slist_free
    g_slist_free.argtypes = [POINTER(GSList)]
    g_slist_free.restype = None

# /usr/include/glib-2.0/glib/gslist.h: 50
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_free_1'):
    g_slist_free_1 = _libs['libassimilationclientlib.so'].g_slist_free_1
    g_slist_free_1.argtypes = [POINTER(GSList)]
    g_slist_free_1.restype = None

# /usr/include/glib-2.0/glib/gslist.h: 52
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_free_full'):
    g_slist_free_full = _libs['libassimilationclientlib.so'].g_slist_free_full
    g_slist_free_full.argtypes = [POINTER(GSList), GDestroyNotify]
    g_slist_free_full.restype = None

# /usr/include/glib-2.0/glib/gslist.h: 54
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_append'):
    g_slist_append = _libs['libassimilationclientlib.so'].g_slist_append
    g_slist_append.argtypes = [POINTER(GSList), gpointer]
    g_slist_append.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 56
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_prepend'):
    g_slist_prepend = _libs['libassimilationclientlib.so'].g_slist_prepend
    g_slist_prepend.argtypes = [POINTER(GSList), gpointer]
    g_slist_prepend.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 58
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_insert'):
    g_slist_insert = _libs['libassimilationclientlib.so'].g_slist_insert
    g_slist_insert.argtypes = [POINTER(GSList), gpointer, gint]
    g_slist_insert.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 61
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_insert_sorted'):
    g_slist_insert_sorted = _libs['libassimilationclientlib.so'].g_slist_insert_sorted
    g_slist_insert_sorted.argtypes = [POINTER(GSList), gpointer, GCompareFunc]
    g_slist_insert_sorted.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 64
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_insert_sorted_with_data'):
    g_slist_insert_sorted_with_data = _libs['libassimilationclientlib.so'].g_slist_insert_sorted_with_data
    g_slist_insert_sorted_with_data.argtypes = [POINTER(GSList), gpointer, GCompareDataFunc, gpointer]
    g_slist_insert_sorted_with_data.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 68
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_insert_before'):
    g_slist_insert_before = _libs['libassimilationclientlib.so'].g_slist_insert_before
    g_slist_insert_before.argtypes = [POINTER(GSList), POINTER(GSList), gpointer]
    g_slist_insert_before.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 71
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_concat'):
    g_slist_concat = _libs['libassimilationclientlib.so'].g_slist_concat
    g_slist_concat.argtypes = [POINTER(GSList), POINTER(GSList)]
    g_slist_concat.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 73
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_remove'):
    g_slist_remove = _libs['libassimilationclientlib.so'].g_slist_remove
    g_slist_remove.argtypes = [POINTER(GSList), gconstpointer]
    g_slist_remove.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 75
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_remove_all'):
    g_slist_remove_all = _libs['libassimilationclientlib.so'].g_slist_remove_all
    g_slist_remove_all.argtypes = [POINTER(GSList), gconstpointer]
    g_slist_remove_all.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 77
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_remove_link'):
    g_slist_remove_link = _libs['libassimilationclientlib.so'].g_slist_remove_link
    g_slist_remove_link.argtypes = [POINTER(GSList), POINTER(GSList)]
    g_slist_remove_link.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 79
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_delete_link'):
    g_slist_delete_link = _libs['libassimilationclientlib.so'].g_slist_delete_link
    g_slist_delete_link.argtypes = [POINTER(GSList), POINTER(GSList)]
    g_slist_delete_link.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 81
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_reverse'):
    g_slist_reverse = _libs['libassimilationclientlib.so'].g_slist_reverse
    g_slist_reverse.argtypes = [POINTER(GSList)]
    g_slist_reverse.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 82
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_copy'):
    g_slist_copy = _libs['libassimilationclientlib.so'].g_slist_copy
    g_slist_copy.argtypes = [POINTER(GSList)]
    g_slist_copy.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 83
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_nth'):
    g_slist_nth = _libs['libassimilationclientlib.so'].g_slist_nth
    g_slist_nth.argtypes = [POINTER(GSList), guint]
    g_slist_nth.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 85
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_find'):
    g_slist_find = _libs['libassimilationclientlib.so'].g_slist_find
    g_slist_find.argtypes = [POINTER(GSList), gconstpointer]
    g_slist_find.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 87
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_find_custom'):
    g_slist_find_custom = _libs['libassimilationclientlib.so'].g_slist_find_custom
    g_slist_find_custom.argtypes = [POINTER(GSList), gconstpointer, GCompareFunc]
    g_slist_find_custom.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 90
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_position'):
    g_slist_position = _libs['libassimilationclientlib.so'].g_slist_position
    g_slist_position.argtypes = [POINTER(GSList), POINTER(GSList)]
    g_slist_position.restype = gint

# /usr/include/glib-2.0/glib/gslist.h: 92
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_index'):
    g_slist_index = _libs['libassimilationclientlib.so'].g_slist_index
    g_slist_index.argtypes = [POINTER(GSList), gconstpointer]
    g_slist_index.restype = gint

# /usr/include/glib-2.0/glib/gslist.h: 94
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_last'):
    g_slist_last = _libs['libassimilationclientlib.so'].g_slist_last
    g_slist_last.argtypes = [POINTER(GSList)]
    g_slist_last.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 95
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_length'):
    g_slist_length = _libs['libassimilationclientlib.so'].g_slist_length
    g_slist_length.argtypes = [POINTER(GSList)]
    g_slist_length.restype = guint

# /usr/include/glib-2.0/glib/gslist.h: 96
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_foreach'):
    g_slist_foreach = _libs['libassimilationclientlib.so'].g_slist_foreach
    g_slist_foreach.argtypes = [POINTER(GSList), GFunc, gpointer]
    g_slist_foreach.restype = None

# /usr/include/glib-2.0/glib/gslist.h: 99
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_sort'):
    g_slist_sort = _libs['libassimilationclientlib.so'].g_slist_sort
    g_slist_sort.argtypes = [POINTER(GSList), GCompareFunc]
    g_slist_sort.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 101
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_sort_with_data'):
    g_slist_sort_with_data = _libs['libassimilationclientlib.so'].g_slist_sort_with_data
    g_slist_sort_with_data.argtypes = [POINTER(GSList), GCompareDataFunc, gpointer]
    g_slist_sort_with_data.restype = POINTER(GSList)

# /usr/include/glib-2.0/glib/gslist.h: 104
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_nth_data'):
    g_slist_nth_data = _libs['libassimilationclientlib.so'].g_slist_nth_data
    g_slist_nth_data.argtypes = [POINTER(GSList), guint]
    g_slist_nth_data.restype = gpointer

# /usr/include/glib-2.0/glib/gslist.h: 110
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_push_allocator'):
    g_slist_push_allocator = _libs['libassimilationclientlib.so'].g_slist_push_allocator
    g_slist_push_allocator.argtypes = [gpointer]
    g_slist_push_allocator.restype = None

# /usr/include/glib-2.0/glib/gslist.h: 111
if hasattr(_libs['libassimilationclientlib.so'], 'g_slist_pop_allocator'):
    g_slist_pop_allocator = _libs['libassimilationclientlib.so'].g_slist_pop_allocator
    g_slist_pop_allocator.argtypes = []
    g_slist_pop_allocator.restype = None

# /usr/include/glib-2.0/glib/gmain.h: 39
class struct__GMainContext(Structure):
    pass

GMainContext = struct__GMainContext # /usr/include/glib-2.0/glib/gmain.h: 39

# /usr/include/glib-2.0/glib/gmain.h: 150
class struct__GSource(Structure):
    pass

GSource = struct__GSource # /usr/include/glib-2.0/glib/gmain.h: 55

# /usr/include/glib-2.0/glib/gmain.h: 56
class struct__GSourcePrivate(Structure):
    pass

GSourcePrivate = struct__GSourcePrivate # /usr/include/glib-2.0/glib/gmain.h: 56

# /usr/include/glib-2.0/glib/gmain.h: 175
class struct__GSourceCallbackFuncs(Structure):
    pass

GSourceCallbackFuncs = struct__GSourceCallbackFuncs # /usr/include/glib-2.0/glib/gmain.h: 68

# /usr/include/glib-2.0/glib/gmain.h: 193
class struct__GSourceFuncs(Structure):
    pass

GSourceFuncs = struct__GSourceFuncs # /usr/include/glib-2.0/glib/gmain.h: 115

GSourceFunc = CFUNCTYPE(UNCHECKED(gboolean), gpointer) # /usr/include/glib-2.0/glib/gmain.h: 136

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

GSourceDummyMarshal = CFUNCTYPE(UNCHECKED(None), ) # /usr/include/glib-2.0/glib/gmain.h: 191

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

# /usr/include/glib-2.0/glib/gstring.h: 55
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

enum_anon_64 = c_int # /usr/include/glib-2.0/glib/giochannel.h: 77

GIOStatus = enum_anon_64 # /usr/include/glib-2.0/glib/giochannel.h: 77

enum_anon_65 = c_int # /usr/include/glib-2.0/glib/giochannel.h: 84

GSeekType = enum_anon_65 # /usr/include/glib-2.0/glib/giochannel.h: 84

enum_anon_66 = c_int # /usr/include/glib-2.0/glib/giochannel.h: 94

GIOCondition = enum_anon_66 # /usr/include/glib-2.0/glib/giochannel.h: 94

enum_anon_67 = c_int # /usr/include/glib-2.0/glib/giochannel.h: 106

GIOFlags = enum_anon_67 # /usr/include/glib-2.0/glib/giochannel.h: 106

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

# /usr/include/glib-2.0/glib/gqueue.h: 49
class struct__GQueue(Structure):
    pass

GQueue = struct__GQueue # /usr/include/glib-2.0/glib/gqueue.h: 38

struct__GQueue.__slots__ = [
    'head',
    'tail',
    'length',
]
struct__GQueue._fields_ = [
    ('head', POINTER(GList)),
    ('tail', POINTER(GList)),
    ('length', guint),
]

# ../include/assimobj.h: 49
class struct__AssimObj(Structure):
    pass

AssimObj = struct__AssimObj # ../include/assimobj.h: 47

struct__AssimObj.__slots__ = [
    '_refcount',
    '_finalize',
    'ref',
    'unref',
    'toString',
]
struct__AssimObj._fields_ = [
    ('_refcount', c_int),
    ('_finalize', CFUNCTYPE(UNCHECKED(None), POINTER(AssimObj))),
    ('ref', CFUNCTYPE(UNCHECKED(None), gpointer)),
    ('unref', CFUNCTYPE(UNCHECKED(None), gpointer)),
    ('toString', CFUNCTYPE(UNCHECKED(POINTER(gchar)), gconstpointer)),
]

# ../include/assimobj.h: 60
if hasattr(_libs['libassimilationclientlib.so'], 'assimobj_new'):
    assimobj_new = _libs['libassimilationclientlib.so'].assimobj_new
    assimobj_new.argtypes = [guint]
    assimobj_new.restype = POINTER(AssimObj)

# ../include/assimobj.h: 61
if hasattr(_libs['libassimilationclientlib.so'], '_assimobj_finalize'):
    _assimobj_finalize = _libs['libassimilationclientlib.so']._assimobj_finalize
    _assimobj_finalize.argtypes = [POINTER(AssimObj)]
    _assimobj_finalize.restype = None

# ../include/assimobj.h: 62
try:
    badfree = (gboolean).in_dll(_libs['libassimilationclientlib.so'], 'badfree')
except:
    pass

# ../include/proj_classes.h: 28
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_new'):
    proj_class_new = _libs['libassimilationclientlib.so'].proj_class_new
    proj_class_new.argtypes = [gsize, String]
    proj_class_new.restype = gpointer

# ../include/proj_classes.h: 29
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_dissociate'):
    proj_class_dissociate = _libs['libassimilationclientlib.so'].proj_class_dissociate
    proj_class_dissociate.argtypes = [gpointer]
    proj_class_dissociate.restype = None

# ../include/proj_classes.h: 30
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_free'):
    proj_class_free = _libs['libassimilationclientlib.so'].proj_class_free
    proj_class_free.argtypes = [gpointer]
    proj_class_free.restype = None

# ../include/proj_classes.h: 31
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_register_object'):
    proj_class_register_object = _libs['libassimilationclientlib.so'].proj_class_register_object
    proj_class_register_object.argtypes = [gpointer, String]
    proj_class_register_object.restype = None

# ../include/proj_classes.h: 32
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_is_a'):
    proj_class_is_a = _libs['libassimilationclientlib.so'].proj_class_is_a
    proj_class_is_a.argtypes = [gconstpointer, String]
    proj_class_is_a.restype = gboolean

# ../include/proj_classes.h: 33
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_castas'):
    proj_class_castas = _libs['libassimilationclientlib.so'].proj_class_castas
    proj_class_castas.argtypes = [gpointer, String]
    proj_class_castas.restype = gpointer

# ../include/proj_classes.h: 34
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_castasconst'):
    proj_class_castasconst = _libs['libassimilationclientlib.so'].proj_class_castasconst
    proj_class_castasconst.argtypes = [gconstpointer, String]
    proj_class_castasconst.restype = gconstpointer

# ../include/proj_classes.h: 35
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_register_subclassed'):
    proj_class_register_subclassed = _libs['libassimilationclientlib.so'].proj_class_register_subclassed
    proj_class_register_subclassed.argtypes = [gpointer, String]
    proj_class_register_subclassed.restype = gpointer

# ../include/proj_classes.h: 36
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_quark_add_superclass_relationship'):
    proj_class_quark_add_superclass_relationship = _libs['libassimilationclientlib.so'].proj_class_quark_add_superclass_relationship
    proj_class_quark_add_superclass_relationship.argtypes = [GQuark, GQuark]
    proj_class_quark_add_superclass_relationship.restype = None

# ../include/proj_classes.h: 37
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_quark_is_a'):
    proj_class_quark_is_a = _libs['libassimilationclientlib.so'].proj_class_quark_is_a
    proj_class_quark_is_a.argtypes = [GQuark, GQuark]
    proj_class_quark_is_a.restype = gboolean

# ../include/proj_classes.h: 38
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_classname'):
    proj_class_classname = _libs['libassimilationclientlib.so'].proj_class_classname
    proj_class_classname.argtypes = [gconstpointer]
    if sizeof(c_int) == sizeof(c_void_p):
        proj_class_classname.restype = ReturnString
    else:
        proj_class_classname.restype = String
        proj_class_classname.errcheck = ReturnString

# ../include/proj_classes.h: 39
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_register_debug_counter'):
    proj_class_register_debug_counter = _libs['libassimilationclientlib.so'].proj_class_register_debug_counter
    proj_class_register_debug_counter.argtypes = [String, POINTER(guint)]
    proj_class_register_debug_counter.restype = None

# ../include/proj_classes.h: 40
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_incr_debug'):
    proj_class_incr_debug = _libs['libassimilationclientlib.so'].proj_class_incr_debug
    proj_class_incr_debug.argtypes = [String]
    proj_class_incr_debug.restype = None

# ../include/proj_classes.h: 41
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_decr_debug'):
    proj_class_decr_debug = _libs['libassimilationclientlib.so'].proj_class_decr_debug
    proj_class_decr_debug.argtypes = [String]
    proj_class_decr_debug.restype = None

# ../include/proj_classes.h: 42
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_debug_dump'):
    proj_class_debug_dump = _libs['libassimilationclientlib.so'].proj_class_debug_dump
    proj_class_debug_dump.argtypes = [String, POINTER(AssimObj), String]
    proj_class_debug_dump.restype = None

# ../include/proj_classes.h: 44
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_dump_live_objects'):
    proj_class_dump_live_objects = _libs['libassimilationclientlib.so'].proj_class_dump_live_objects
    proj_class_dump_live_objects.argtypes = []
    proj_class_dump_live_objects.restype = None

# ../include/proj_classes.h: 45
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_live_object_count'):
    proj_class_live_object_count = _libs['libassimilationclientlib.so'].proj_class_live_object_count
    proj_class_live_object_count.argtypes = []
    proj_class_live_object_count.restype = guint32

# ../include/proj_classes.h: 46
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_max_object_count'):
    proj_class_max_object_count = _libs['libassimilationclientlib.so'].proj_class_max_object_count
    proj_class_max_object_count.argtypes = []
    proj_class_max_object_count.restype = guint32

# ../include/proj_classes.h: 47
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_finalize_sys'):
    proj_class_finalize_sys = _libs['libassimilationclientlib.so'].proj_class_finalize_sys
    proj_class_finalize_sys.argtypes = []
    proj_class_finalize_sys.restype = None

# ../include/frameset.h: 43
class struct__FrameSet(Structure):
    pass

FrameSet = struct__FrameSet # ../include/frame.h: 31

# ../include/frame.h: 42
class struct__Frame(Structure):
    pass

Frame = struct__Frame # ../include/frame.h: 32

struct__Frame.__slots__ = [
    'baseclass',
    'type',
    'length',
    'value',
    'dataspace',
    'updatedata',
    'isvalid',
    'setvalue',
    'dump',
    'valuefinalize',
]
struct__Frame._fields_ = [
    ('baseclass', AssimObj),
    ('type', guint16),
    ('length', guint16),
    ('value', gpointer),
    ('dataspace', CFUNCTYPE(UNCHECKED(gsize), POINTER(Frame))),
    ('updatedata', CFUNCTYPE(UNCHECKED(None), POINTER(Frame), gpointer, gconstpointer, POINTER(FrameSet))),
    ('isvalid', CFUNCTYPE(UNCHECKED(gboolean), POINTER(Frame), gconstpointer, gconstpointer)),
    ('setvalue', CFUNCTYPE(UNCHECKED(None), POINTER(Frame), gpointer, guint16, GDestroyNotify)),
    ('dump', CFUNCTYPE(UNCHECKED(None), POINTER(Frame), String)),
    ('valuefinalize', GDestroyNotify),
]

# ../include/frame.h: 59
if hasattr(_libs['libassimilationclientlib.so'], 'frame_new'):
    frame_new = _libs['libassimilationclientlib.so'].frame_new
    frame_new.argtypes = [guint16, gsize]
    frame_new.restype = POINTER(Frame)

# ../include/frame.h: 60
if hasattr(_libs['libassimilationclientlib.so'], 'frame_tlvconstructor'):
    frame_tlvconstructor = _libs['libassimilationclientlib.so'].frame_tlvconstructor
    frame_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    frame_tlvconstructor.restype = POINTER(Frame)

# ../include/frame.h: 61
if hasattr(_libs['libassimilationclientlib.so'], 'frame_default_valuefinalize'):
    frame_default_valuefinalize = _libs['libassimilationclientlib.so'].frame_default_valuefinalize
    frame_default_valuefinalize.argtypes = [gpointer]
    frame_default_valuefinalize.restype = None

u_char = __u_char # /usr/include/i386-linux-gnu/sys/types.h: 34

u_short = __u_short # /usr/include/i386-linux-gnu/sys/types.h: 35

u_int = __u_int # /usr/include/i386-linux-gnu/sys/types.h: 36

# /usr/include/i386-linux-gnu/bits/time.h: 75
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

socklen_t = __socklen_t # /usr/include/i386-linux-gnu/bits/socket.h: 35

sa_family_t = c_uint # /usr/include/i386-linux-gnu/bits/sockaddr.h: 29

# /usr/include/i386-linux-gnu/bits/socket.h: 178
class struct_sockaddr(Structure):
    pass

struct_sockaddr.__slots__ = [
    'sa_family',
    'sa_data',
]
struct_sockaddr._fields_ = [
    ('sa_family', sa_family_t),
    ('sa_data', c_char * 14),
]

in_port_t = c_uint16 # /usr/include/netinet/in.h: 97

in_addr_t = c_uint32 # /usr/include/netinet/in.h: 141

# /usr/include/netinet/in.h: 142
class struct_in_addr(Structure):
    pass

struct_in_addr.__slots__ = [
    's_addr',
]
struct_in_addr._fields_ = [
    ('s_addr', in_addr_t),
]

# /usr/include/netinet/in.h: 200
class union_anon_101(Union):
    pass

union_anon_101.__slots__ = [
    '__u6_addr8',
    '__u6_addr16',
    '__u6_addr32',
]
union_anon_101._fields_ = [
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
    ('__in6_u', union_anon_101),
]

# /usr/include/netinet/in.h: 225
class struct_sockaddr_in(Structure):
    pass

struct_sockaddr_in.__slots__ = [
    'sin_family',
    'sin_port',
    'sin_addr',
    'sin_zero',
]
struct_sockaddr_in._fields_ = [
    ('sin_family', sa_family_t),
    ('sin_port', in_port_t),
    ('sin_addr', struct_in_addr),
    ('sin_zero', c_ubyte * (((sizeof(struct_sockaddr) - sizeof(c_uint)) - sizeof(in_port_t)) - sizeof(struct_in_addr))),
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

# ../include/netaddr.h: 43
class struct__NetAddr(Structure):
    pass

NetAddr = struct__NetAddr # ../include/netaddr.h: 36

struct__NetAddr.__slots__ = [
    'baseclass',
    'setport',
    'port',
    'addrtype',
    'ismcast',
    'islocal',
    'ipv6sockaddr',
    'ipv4sockaddr',
    'equal',
    'hash',
    'canonStr',
    'toIPv6',
    '_addrbody',
    '_addrtype',
    '_addrlen',
    '_addrport',
]
struct__NetAddr._fields_ = [
    ('baseclass', AssimObj),
    ('setport', CFUNCTYPE(UNCHECKED(None), POINTER(NetAddr), guint16)),
    ('port', CFUNCTYPE(UNCHECKED(guint16), POINTER(NetAddr))),
    ('addrtype', CFUNCTYPE(UNCHECKED(guint16), POINTER(NetAddr))),
    ('ismcast', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetAddr))),
    ('islocal', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetAddr))),
    ('ipv6sockaddr', CFUNCTYPE(UNCHECKED(struct_sockaddr_in6), POINTER(NetAddr))),
    ('ipv4sockaddr', CFUNCTYPE(UNCHECKED(struct_sockaddr_in), POINTER(NetAddr))),
    ('equal', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetAddr), POINTER(NetAddr))),
    ('hash', CFUNCTYPE(UNCHECKED(guint), POINTER(NetAddr))),
    ('canonStr', CFUNCTYPE(UNCHECKED(String), POINTER(NetAddr))),
    ('toIPv6', CFUNCTYPE(UNCHECKED(POINTER(NetAddr)), POINTER(NetAddr))),
    ('_addrbody', gpointer),
    ('_addrtype', guint16),
    ('_addrlen', guint16),
    ('_addrport', guint16),
]

# ../include/netaddr.h: 63
if hasattr(_libs['libassimilationclientlib.so'], 'netaddr_new'):
    netaddr_new = _libs['libassimilationclientlib.so'].netaddr_new
    netaddr_new.argtypes = [gsize, guint16, guint16, gconstpointer, guint16]
    netaddr_new.restype = POINTER(NetAddr)

# ../include/netaddr.h: 64
if hasattr(_libs['libassimilationclientlib.so'], 'netaddr_sockaddr_new'):
    netaddr_sockaddr_new = _libs['libassimilationclientlib.so'].netaddr_sockaddr_new
    netaddr_sockaddr_new.argtypes = [POINTER(struct_sockaddr_in6), socklen_t]
    netaddr_sockaddr_new.restype = POINTER(NetAddr)

# ../include/netaddr.h: 65
if hasattr(_libs['libassimilationclientlib.so'], 'netaddr_macaddr_new'):
    netaddr_macaddr_new = _libs['libassimilationclientlib.so'].netaddr_macaddr_new
    netaddr_macaddr_new.argtypes = [gconstpointer, guint16]
    netaddr_macaddr_new.restype = POINTER(NetAddr)

# ../include/netaddr.h: 66
if hasattr(_libs['libassimilationclientlib.so'], 'netaddr_mac48_new'):
    netaddr_mac48_new = _libs['libassimilationclientlib.so'].netaddr_mac48_new
    netaddr_mac48_new.argtypes = [gconstpointer]
    netaddr_mac48_new.restype = POINTER(NetAddr)

# ../include/netaddr.h: 67
if hasattr(_libs['libassimilationclientlib.so'], 'netaddr_mac64_new'):
    netaddr_mac64_new = _libs['libassimilationclientlib.so'].netaddr_mac64_new
    netaddr_mac64_new.argtypes = [gconstpointer]
    netaddr_mac64_new.restype = POINTER(NetAddr)

# ../include/netaddr.h: 68
if hasattr(_libs['libassimilationclientlib.so'], 'netaddr_ipv4_new'):
    netaddr_ipv4_new = _libs['libassimilationclientlib.so'].netaddr_ipv4_new
    netaddr_ipv4_new.argtypes = [gconstpointer, guint16]
    netaddr_ipv4_new.restype = POINTER(NetAddr)

# ../include/netaddr.h: 69
if hasattr(_libs['libassimilationclientlib.so'], 'netaddr_ipv6_new'):
    netaddr_ipv6_new = _libs['libassimilationclientlib.so'].netaddr_ipv6_new
    netaddr_ipv6_new.argtypes = [gconstpointer, guint16]
    netaddr_ipv6_new.restype = POINTER(NetAddr)

# ../include/netaddr.h: 70
if hasattr(_libs['libassimilationclientlib.so'], 'netaddr_string_new'):
    netaddr_string_new = _libs['libassimilationclientlib.so'].netaddr_string_new
    netaddr_string_new.argtypes = [String]
    netaddr_string_new.restype = POINTER(NetAddr)

# /home/alanr/monitor/src/include/addrframe.h: 38
class struct__AddrFrame(Structure):
    pass

AddrFrame = struct__AddrFrame # /home/alanr/monitor/src/include/addrframe.h: 31

struct__AddrFrame.__slots__ = [
    'baseclass',
    '_addr',
    '_basefinal',
    'setaddr',
    'setnetaddr',
    'getnetaddr',
    'setport',
]
struct__AddrFrame._fields_ = [
    ('baseclass', Frame),
    ('_addr', POINTER(NetAddr)),
    ('_basefinal', CFUNCTYPE(UNCHECKED(None), POINTER(AssimObj))),
    ('setaddr', CFUNCTYPE(UNCHECKED(None), POINTER(AddrFrame), guint16, gconstpointer, gsize)),
    ('setnetaddr', CFUNCTYPE(UNCHECKED(None), POINTER(AddrFrame), POINTER(NetAddr))),
    ('getnetaddr', CFUNCTYPE(UNCHECKED(POINTER(NetAddr)), POINTER(AddrFrame))),
    ('setport', CFUNCTYPE(UNCHECKED(None), POINTER(AddrFrame), guint16)),
]

# /home/alanr/monitor/src/include/addrframe.h: 48
if hasattr(_libs['libassimilationclientlib.so'], 'addrframe_new'):
    addrframe_new = _libs['libassimilationclientlib.so'].addrframe_new
    addrframe_new.argtypes = [guint16, gsize]
    addrframe_new.restype = POINTER(AddrFrame)

# /home/alanr/monitor/src/include/addrframe.h: 49
if hasattr(_libs['libassimilationclientlib.so'], 'addrframe_ipv4_new'):
    addrframe_ipv4_new = _libs['libassimilationclientlib.so'].addrframe_ipv4_new
    addrframe_ipv4_new.argtypes = [guint16, gconstpointer]
    addrframe_ipv4_new.restype = POINTER(AddrFrame)

# /home/alanr/monitor/src/include/addrframe.h: 50
if hasattr(_libs['libassimilationclientlib.so'], 'addrframe_ipv6_new'):
    addrframe_ipv6_new = _libs['libassimilationclientlib.so'].addrframe_ipv6_new
    addrframe_ipv6_new.argtypes = [guint16, gconstpointer]
    addrframe_ipv6_new.restype = POINTER(AddrFrame)

# /home/alanr/monitor/src/include/addrframe.h: 51
if hasattr(_libs['libassimilationclientlib.so'], 'addrframe_mac48_new'):
    addrframe_mac48_new = _libs['libassimilationclientlib.so'].addrframe_mac48_new
    addrframe_mac48_new.argtypes = [guint16, gconstpointer]
    addrframe_mac48_new.restype = POINTER(AddrFrame)

# /home/alanr/monitor/src/include/addrframe.h: 52
if hasattr(_libs['libassimilationclientlib.so'], 'addrframe_mac64_new'):
    addrframe_mac64_new = _libs['libassimilationclientlib.so'].addrframe_mac64_new
    addrframe_mac64_new.argtypes = [guint16, gconstpointer]
    addrframe_mac64_new.restype = POINTER(AddrFrame)

# /home/alanr/monitor/src/include/addrframe.h: 53
if hasattr(_libs['libassimilationclientlib.so'], 'addrframe_tlvconstructor'):
    addrframe_tlvconstructor = _libs['libassimilationclientlib.so'].addrframe_tlvconstructor
    addrframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    addrframe_tlvconstructor.restype = POINTER(Frame)

# ../include/signframe.h: 40
class struct__SignFrame(Structure):
    pass

SignFrame = struct__SignFrame # ../include/signframe.h: 33

struct__SignFrame.__slots__ = [
    'baseclass',
    'signaturetype',
]
struct__SignFrame._fields_ = [
    ('baseclass', Frame),
    ('signaturetype', GChecksumType),
]

# ../include/signframe.h: 45
if hasattr(_libs['libassimilationclientlib.so'], 'signframe_new'):
    signframe_new = _libs['libassimilationclientlib.so'].signframe_new
    signframe_new.argtypes = [GChecksumType, gsize]
    signframe_new.restype = POINTER(SignFrame)

# ../include/signframe.h: 46
if hasattr(_libs['libassimilationclientlib.so'], 'signframe_tlvconstructor'):
    signframe_tlvconstructor = _libs['libassimilationclientlib.so'].signframe_tlvconstructor
    signframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    signframe_tlvconstructor.restype = POINTER(Frame)

# ../include/seqnoframe.h: 42
class struct__SeqnoFrame(Structure):
    pass

SeqnoFrame = struct__SeqnoFrame # ../include/seqnoframe.h: 34

struct__SeqnoFrame.__slots__ = [
    'baseclass',
    'getreqid',
    'setreqid',
    'getqid',
    'setqid',
    'getsessionid',
    'equal',
    'compare',
    '_reqid',
    '_sessionid',
    '_qid',
]
struct__SeqnoFrame._fields_ = [
    ('baseclass', Frame),
    ('getreqid', CFUNCTYPE(UNCHECKED(guint64), POINTER(SeqnoFrame))),
    ('setreqid', CFUNCTYPE(UNCHECKED(None), POINTER(SeqnoFrame), guint64)),
    ('getqid', CFUNCTYPE(UNCHECKED(guint16), POINTER(SeqnoFrame))),
    ('setqid', CFUNCTYPE(UNCHECKED(None), POINTER(SeqnoFrame), guint16)),
    ('getsessionid', CFUNCTYPE(UNCHECKED(guint32), POINTER(SeqnoFrame))),
    ('equal', CFUNCTYPE(UNCHECKED(c_int), POINTER(SeqnoFrame), POINTER(SeqnoFrame))),
    ('compare', CFUNCTYPE(UNCHECKED(c_int), POINTER(SeqnoFrame), POINTER(SeqnoFrame))),
    ('_reqid', guint64),
    ('_sessionid', guint32),
    ('_qid', guint16),
]

# ../include/seqnoframe.h: 55
if hasattr(_libs['libassimilationclientlib.so'], 'seqnoframe_new'):
    seqnoframe_new = _libs['libassimilationclientlib.so'].seqnoframe_new
    seqnoframe_new.argtypes = [guint16, c_int]
    seqnoframe_new.restype = POINTER(SeqnoFrame)

# ../include/seqnoframe.h: 56
if hasattr(_libs['libassimilationclientlib.so'], 'seqnoframe_new_init'):
    seqnoframe_new_init = _libs['libassimilationclientlib.so'].seqnoframe_new_init
    seqnoframe_new_init.argtypes = [guint16, guint64, guint16]
    seqnoframe_new_init.restype = POINTER(SeqnoFrame)

# ../include/seqnoframe.h: 57
if hasattr(_libs['libassimilationclientlib.so'], 'seqnoframe_tlvconstructor'):
    seqnoframe_tlvconstructor = _libs['libassimilationclientlib.so'].seqnoframe_tlvconstructor
    seqnoframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    seqnoframe_tlvconstructor.restype = POINTER(Frame)

struct__FrameSet.__slots__ = [
    'baseclass',
    'framelist',
    'packet',
    'pktend',
    'fstype',
    'fsflags',
    '_seqframe',
    'getseqno',
]
struct__FrameSet._fields_ = [
    ('baseclass', AssimObj),
    ('framelist', POINTER(GSList)),
    ('packet', gpointer),
    ('pktend', gpointer),
    ('fstype', guint16),
    ('fsflags', guint16),
    ('_seqframe', POINTER(SeqnoFrame)),
    ('getseqno', CFUNCTYPE(UNCHECKED(POINTER(SeqnoFrame)), POINTER(FrameSet))),
]

# ../include/frameset.h: 56
if hasattr(_libs['libassimilationclientlib.so'], 'frameset_new'):
    frameset_new = _libs['libassimilationclientlib.so'].frameset_new
    frameset_new.argtypes = [guint16]
    frameset_new.restype = POINTER(FrameSet)

# ../include/frameset.h: 57
if hasattr(_libs['libassimilationclientlib.so'], 'frameset_prepend_frame'):
    frameset_prepend_frame = _libs['libassimilationclientlib.so'].frameset_prepend_frame
    frameset_prepend_frame.argtypes = [POINTER(FrameSet), POINTER(Frame)]
    frameset_prepend_frame.restype = None

# ../include/frameset.h: 58
if hasattr(_libs['libassimilationclientlib.so'], 'frameset_append_frame'):
    frameset_append_frame = _libs['libassimilationclientlib.so'].frameset_append_frame
    frameset_append_frame.argtypes = [POINTER(FrameSet), POINTER(Frame)]
    frameset_append_frame.restype = None

# ../include/frameset.h: 59
if hasattr(_libs['libassimilationclientlib.so'], 'frameset_construct_packet'):
    frameset_construct_packet = _libs['libassimilationclientlib.so'].frameset_construct_packet
    frameset_construct_packet.argtypes = [POINTER(FrameSet), POINTER(SignFrame), POINTER(Frame), POINTER(Frame)]
    frameset_construct_packet.restype = None

# ../include/frameset.h: 60
if hasattr(_libs['libassimilationclientlib.so'], 'frame_new'):
    frame_new = _libs['libassimilationclientlib.so'].frame_new
    frame_new.argtypes = [guint16, gsize]
    frame_new.restype = POINTER(Frame)

# ../include/frameset.h: 61
if hasattr(_libs['libassimilationclientlib.so'], 'frameset_get_flags'):
    frameset_get_flags = _libs['libassimilationclientlib.so'].frameset_get_flags
    frameset_get_flags.argtypes = [POINTER(FrameSet)]
    frameset_get_flags.restype = guint16

# ../include/frameset.h: 62
if hasattr(_libs['libassimilationclientlib.so'], 'frameset_set_flags'):
    frameset_set_flags = _libs['libassimilationclientlib.so'].frameset_set_flags
    frameset_set_flags.argtypes = [POINTER(FrameSet), guint16]
    frameset_set_flags.restype = guint16

# ../include/frameset.h: 63
if hasattr(_libs['libassimilationclientlib.so'], 'frameset_clear_flags'):
    frameset_clear_flags = _libs['libassimilationclientlib.so'].frameset_clear_flags
    frameset_clear_flags.argtypes = [POINTER(FrameSet), guint16]
    frameset_clear_flags.restype = guint16

# ../include/frameset.h: 64
if hasattr(_libs['libassimilationclientlib.so'], 'frame_append_to_frameset_packet'):
    frame_append_to_frameset_packet = _libs['libassimilationclientlib.so'].frame_append_to_frameset_packet
    frame_append_to_frameset_packet.argtypes = [POINTER(FrameSet), POINTER(Frame), gpointer]
    frame_append_to_frameset_packet.restype = gpointer

# ../include/frameset.h: 65
if hasattr(_libs['libassimilationclientlib.so'], 'frameset_dump'):
    frameset_dump = _libs['libassimilationclientlib.so'].frameset_dump
    frameset_dump.argtypes = [POINTER(FrameSet)]
    frameset_dump.restype = None

# ../include/configcontext.h: 70
class struct__ConfigContext(Structure):
    pass

ConfigContext = struct__ConfigContext # ../include/configcontext.h: 42

enum_ConfigValType = c_int # ../include/configcontext.h: 44

CFG_EEXIST = 0 # ../include/configcontext.h: 44

CFG_NULL = (CFG_EEXIST + 1) # ../include/configcontext.h: 44

CFG_BOOL = (CFG_NULL + 1) # ../include/configcontext.h: 44

CFG_INT64 = (CFG_BOOL + 1) # ../include/configcontext.h: 44

CFG_STRING = (CFG_INT64 + 1) # ../include/configcontext.h: 44

CFG_FLOAT = (CFG_STRING + 1) # ../include/configcontext.h: 44

CFG_ARRAY = (CFG_FLOAT + 1) # ../include/configcontext.h: 44

CFG_CFGCTX = (CFG_ARRAY + 1) # ../include/configcontext.h: 44

CFG_NETADDR = (CFG_CFGCTX + 1) # ../include/configcontext.h: 44

CFG_FRAME = (CFG_NETADDR + 1) # ../include/configcontext.h: 44

# ../include/configcontext.h: 57
class struct__ConfigValue(Structure):
    pass

ConfigValue = struct__ConfigValue # ../include/configcontext.h: 56

# ../include/configcontext.h: 59
class union_anon_102(Union):
    pass

union_anon_102.__slots__ = [
    'intvalue',
    'floatvalue',
    'arrayvalue',
    'strvalue',
    'cfgctxvalue',
    'addrvalue',
    'framevalue',
]
union_anon_102._fields_ = [
    ('intvalue', gint64),
    ('floatvalue', c_double),
    ('arrayvalue', POINTER(GSList)),
    ('strvalue', String),
    ('cfgctxvalue', POINTER(ConfigContext)),
    ('addrvalue', POINTER(NetAddr)),
    ('framevalue', POINTER(Frame)),
]

struct__ConfigValue.__slots__ = [
    'valtype',
    'u',
]
struct__ConfigValue._fields_ = [
    ('valtype', enum_ConfigValType),
    ('u', union_anon_102),
]

struct__ConfigContext.__slots__ = [
    'baseclass',
    '_values',
    'getint',
    'setint',
    'getbool',
    'setbool',
    'getdouble',
    'setdouble',
    'getarray',
    'setarray',
    'getstring',
    'setstring',
    'getframe',
    'setframe',
    'getaddr',
    'setaddr',
    'getconfig',
    'setconfig',
    'gettype',
    'keys',
]
struct__ConfigContext._fields_ = [
    ('baseclass', AssimObj),
    ('_values', POINTER(GHashTable)),
    ('getint', CFUNCTYPE(UNCHECKED(gint), POINTER(ConfigContext), String)),
    ('setint', CFUNCTYPE(UNCHECKED(None), POINTER(ConfigContext), String, gint)),
    ('getbool', CFUNCTYPE(UNCHECKED(gboolean), POINTER(ConfigContext), String)),
    ('setbool', CFUNCTYPE(UNCHECKED(None), POINTER(ConfigContext), String, gboolean)),
    ('getdouble', CFUNCTYPE(UNCHECKED(c_double), POINTER(ConfigContext), String)),
    ('setdouble', CFUNCTYPE(UNCHECKED(None), POINTER(ConfigContext), String, c_double)),
    ('getarray', CFUNCTYPE(UNCHECKED(POINTER(GSList)), POINTER(ConfigContext), String)),
    ('setarray', CFUNCTYPE(UNCHECKED(None), POINTER(ConfigContext), String, POINTER(GSList))),
    ('getstring', CFUNCTYPE(UNCHECKED(String), POINTER(ConfigContext), String)),
    ('setstring', CFUNCTYPE(UNCHECKED(None), POINTER(ConfigContext), String, String)),
    ('getframe', CFUNCTYPE(UNCHECKED(POINTER(Frame)), POINTER(ConfigContext), String)),
    ('setframe', CFUNCTYPE(UNCHECKED(None), POINTER(ConfigContext), String, POINTER(Frame))),
    ('getaddr', CFUNCTYPE(UNCHECKED(POINTER(NetAddr)), POINTER(ConfigContext), String)),
    ('setaddr', CFUNCTYPE(UNCHECKED(None), POINTER(ConfigContext), String, POINTER(NetAddr))),
    ('getconfig', CFUNCTYPE(UNCHECKED(POINTER(ConfigContext)), POINTER(ConfigContext), String)),
    ('setconfig', CFUNCTYPE(UNCHECKED(None), POINTER(ConfigContext), String, POINTER(ConfigContext))),
    ('gettype', CFUNCTYPE(UNCHECKED(enum_ConfigValType), POINTER(ConfigContext), String)),
    ('keys', CFUNCTYPE(UNCHECKED(POINTER(GSList)), POINTER(ConfigContext))),
]

# ../include/configcontext.h: 93
if hasattr(_libs['libassimilationclientlib.so'], 'configcontext_new'):
    configcontext_new = _libs['libassimilationclientlib.so'].configcontext_new
    configcontext_new.argtypes = [gsize]
    configcontext_new.restype = POINTER(ConfigContext)

# ../include/configcontext.h: 94
if hasattr(_libs['libassimilationclientlib.so'], 'configcontext_new_JSON_string'):
    configcontext_new_JSON_string = _libs['libassimilationclientlib.so'].configcontext_new_JSON_string
    configcontext_new_JSON_string.argtypes = [String]
    configcontext_new_JSON_string.restype = POINTER(ConfigContext)

# ../include/listener.h: 41
class struct__Listener(Structure):
    pass

Listener = struct__Listener # ../include/listener.h: 33

# ../include/packetdecoder.h: 37
class struct__FrameTypeToFrame(Structure):
    pass

FrameTypeToFrame = struct__FrameTypeToFrame # ../include/packetdecoder.h: 32

FramePktConstructor = CFUNCTYPE(UNCHECKED(POINTER(Frame)), gconstpointer, gconstpointer) # ../include/packetdecoder.h: 34

struct__FrameTypeToFrame.__slots__ = [
    'frametype',
    'constructor',
]
struct__FrameTypeToFrame._fields_ = [
    ('frametype', c_int),
    ('constructor', FramePktConstructor),
]

# ../include/packetdecoder.h: 44
class struct__PacketDecoder(Structure):
    pass

PacketDecoder = struct__PacketDecoder # ../include/packetdecoder.h: 43

struct__PacketDecoder.__slots__ = [
    'baseclass',
    '_pfinalize',
    '_framemaplen',
    '_framemap',
    '_maxframetype',
    '_frametypemap',
    'pktdata_to_framesetlist',
]
struct__PacketDecoder._fields_ = [
    ('baseclass', AssimObj),
    ('_pfinalize', CFUNCTYPE(UNCHECKED(None), POINTER(AssimObj))),
    ('_framemaplen', c_int),
    ('_framemap', POINTER(FrameTypeToFrame)),
    ('_maxframetype', c_int),
    ('_frametypemap', POINTER(FramePktConstructor)),
    ('pktdata_to_framesetlist', CFUNCTYPE(UNCHECKED(POINTER(GSList)), POINTER(PacketDecoder), gconstpointer, gconstpointer)),
]

# ../include/packetdecoder.h: 54
if hasattr(_libs['libassimilationclientlib.so'], 'packetdecoder_new'):
    packetdecoder_new = _libs['libassimilationclientlib.so'].packetdecoder_new
    packetdecoder_new.argtypes = [guint, POINTER(FrameTypeToFrame), gint]
    packetdecoder_new.restype = POINTER(PacketDecoder)

# ../include/netio.h: 44
class struct__NetIO(Structure):
    pass

NetIO = struct__NetIO # ../include/netio.h: 39

struct__NetIO.__slots__ = [
    'baseclass',
    'giosock',
    '_maxpktsize',
    '_configinfo',
    '_decoder',
    '_signframe',
    '_cryptframe',
    '_compressframe',
    '_rcvloss',
    '_xmitloss',
    '_shouldlosepkts',
    'input_queued',
    'bindaddr',
    'boundaddr',
    'mcastjoin',
    'setmcast_ttl',
    'getfd',
    'setblockio',
    'getmaxpktsize',
    'setmaxpktsize',
    'sendaframeset',
    'sendframesets',
    'recvframesets',
    'sendareliablefs',
    'sendreliablefs',
    'ackmessage',
    'supportsreliable',
    'closeconn',
    'signframe',
    'cryptframe',
    'compressframe',
    'setpktloss',
    'enablepktloss',
]
struct__NetIO._fields_ = [
    ('baseclass', AssimObj),
    ('giosock', POINTER(GIOChannel)),
    ('_maxpktsize', gint),
    ('_configinfo', POINTER(ConfigContext)),
    ('_decoder', POINTER(PacketDecoder)),
    ('_signframe', POINTER(SignFrame)),
    ('_cryptframe', POINTER(Frame)),
    ('_compressframe', POINTER(Frame)),
    ('_rcvloss', c_double),
    ('_xmitloss', c_double),
    ('_shouldlosepkts', gboolean),
    ('input_queued', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO))),
    ('bindaddr', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO), POINTER(NetAddr), gboolean)),
    ('boundaddr', CFUNCTYPE(UNCHECKED(POINTER(NetAddr)), POINTER(NetIO))),
    ('mcastjoin', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO), POINTER(NetAddr), POINTER(NetAddr))),
    ('setmcast_ttl', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO), guint8)),
    ('getfd', CFUNCTYPE(UNCHECKED(gint), POINTER(NetIO))),
    ('setblockio', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), gboolean)),
    ('getmaxpktsize', CFUNCTYPE(UNCHECKED(gsize), POINTER(NetIO))),
    ('setmaxpktsize', CFUNCTYPE(UNCHECKED(gsize), POINTER(NetIO), gsize)),
    ('sendaframeset', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), POINTER(NetAddr), POINTER(FrameSet))),
    ('sendframesets', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), POINTER(NetAddr), POINTER(GSList))),
    ('recvframesets', CFUNCTYPE(UNCHECKED(POINTER(GSList)), POINTER(NetIO), POINTER(POINTER(NetAddr)))),
    ('sendareliablefs', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO), POINTER(NetAddr), guint16, POINTER(FrameSet))),
    ('sendreliablefs', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO), POINTER(NetAddr), guint16, POINTER(GSList))),
    ('ackmessage', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO), POINTER(NetAddr), POINTER(FrameSet))),
    ('supportsreliable', CFUNCTYPE(UNCHECKED(gboolean), POINTER(NetIO))),
    ('closeconn', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), guint16, POINTER(NetAddr))),
    ('signframe', CFUNCTYPE(UNCHECKED(POINTER(SignFrame)), POINTER(NetIO))),
    ('cryptframe', CFUNCTYPE(UNCHECKED(POINTER(Frame)), POINTER(NetIO))),
    ('compressframe', CFUNCTYPE(UNCHECKED(POINTER(Frame)), POINTER(NetIO))),
    ('setpktloss', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), c_double, c_double)),
    ('enablepktloss', CFUNCTYPE(UNCHECKED(None), POINTER(NetIO), gboolean)),
]

# ../include/netio.h: 149
if hasattr(_libs['libassimilationclientlib.so'], 'netio_new'):
    netio_new = _libs['libassimilationclientlib.so'].netio_new
    netio_new.argtypes = [gsize, POINTER(ConfigContext), POINTER(PacketDecoder)]
    netio_new.restype = POINTER(NetIO)

# ../include/netio.h: 151
if hasattr(_libs['libassimilationclientlib.so'], 'netio_is_dual_ipv4v6_stack'):
    netio_is_dual_ipv4v6_stack = _libs['libassimilationclientlib.so'].netio_is_dual_ipv4v6_stack
    netio_is_dual_ipv4v6_stack.argtypes = []
    netio_is_dual_ipv4v6_stack.restype = gboolean

# ../include/netgsource.h: 43
class struct__NetGSource(Structure):
    pass

NetGSource = struct__NetGSource # ../include/netgsource.h: 34

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
    'sendaframeset',
    'sendframesets',
    'addListener',
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
    ('sendaframeset', CFUNCTYPE(UNCHECKED(None), POINTER(NetGSource), POINTER(NetAddr), POINTER(FrameSet))),
    ('sendframesets', CFUNCTYPE(UNCHECKED(None), POINTER(NetGSource), POINTER(NetAddr), POINTER(GSList))),
    ('addListener', CFUNCTYPE(UNCHECKED(None), POINTER(NetGSource), guint16, POINTER(Listener))),
]

# ../include/netgsource.h: 57
if hasattr(_libs['libassimilationclientlib.so'], 'netgsource_new'):
    netgsource_new = _libs['libassimilationclientlib.so'].netgsource_new
    netgsource_new.argtypes = [POINTER(NetIO), GDestroyNotify, gint, gboolean, POINTER(GMainContext), gsize, gpointer]
    netgsource_new.restype = POINTER(NetGSource)

struct__Listener.__slots__ = [
    'baseclass',
    'config',
    'transport',
    'got_frameset',
    'associate',
    'dissociate',
]
struct__Listener._fields_ = [
    ('baseclass', AssimObj),
    ('config', POINTER(ConfigContext)),
    ('transport', POINTER(NetGSource)),
    ('got_frameset', CFUNCTYPE(UNCHECKED(gboolean), POINTER(Listener), POINTER(FrameSet), POINTER(NetAddr))),
    ('associate', CFUNCTYPE(UNCHECKED(None), POINTER(Listener), POINTER(NetGSource))),
    ('dissociate', CFUNCTYPE(UNCHECKED(None), POINTER(Listener))),
]

# ../include/listener.h: 54
if hasattr(_libs['libassimilationclientlib.so'], 'listener_new'):
    listener_new = _libs['libassimilationclientlib.so'].listener_new
    listener_new.argtypes = [POINTER(ConfigContext), gsize]
    listener_new.restype = POINTER(Listener)

# /home/alanr/monitor/src/include/authlistener.h: 41
class struct__AuthListener(Structure):
    pass

AuthListener = struct__AuthListener # /home/alanr/monitor/src/include/authlistener.h: 31

# /home/alanr/monitor/src/include/authlistener.h: 50
class struct__ObeyFrameSetTypeMap(Structure):
    pass

ObeyFrameSetTypeMap = struct__ObeyFrameSetTypeMap # /home/alanr/monitor/src/include/authlistener.h: 36

struct__AuthListener.__slots__ = [
    'baseclass',
    'actionmap',
    'autoack',
]
struct__AuthListener._fields_ = [
    ('baseclass', Listener),
    ('actionmap', POINTER(GHashTable)),
    ('autoack', gboolean),
]

AuthListenerAction = CFUNCTYPE(UNCHECKED(None), POINTER(AuthListener), POINTER(FrameSet), POINTER(NetAddr)) # /home/alanr/monitor/src/include/authlistener.h: 48

struct__ObeyFrameSetTypeMap.__slots__ = [
    'framesettype',
    'action',
]
struct__ObeyFrameSetTypeMap._fields_ = [
    ('framesettype', c_int),
    ('action', AuthListenerAction),
]

# /home/alanr/monitor/src/include/authlistener.h: 57
if hasattr(_libs['libassimilationclientlib.so'], 'authlistener_new'):
    authlistener_new = _libs['libassimilationclientlib.so'].authlistener_new
    authlistener_new.argtypes = [gsize, POINTER(ObeyFrameSetTypeMap), POINTER(ConfigContext), gboolean]
    authlistener_new.restype = POINTER(AuthListener)

# /home/alanr/monitor/src/include/cdp.h: 68
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdp_vers'):
    get_cdp_vers = _libs['libassimilationclientlib.so'].get_cdp_vers
    get_cdp_vers.argtypes = [gconstpointer, gconstpointer]
    get_cdp_vers.restype = guint8

# /home/alanr/monitor/src/include/cdp.h: 69
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdp_ttl'):
    get_cdp_ttl = _libs['libassimilationclientlib.so'].get_cdp_ttl
    get_cdp_ttl.argtypes = [gconstpointer, gconstpointer]
    get_cdp_ttl.restype = guint8

# /home/alanr/monitor/src/include/cdp.h: 70
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdp_cksum'):
    get_cdp_cksum = _libs['libassimilationclientlib.so'].get_cdp_cksum
    get_cdp_cksum.argtypes = [gconstpointer, gconstpointer]
    get_cdp_cksum.restype = guint16

# /home/alanr/monitor/src/include/cdp.h: 71
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdptlv_type'):
    get_cdptlv_type = _libs['libassimilationclientlib.so'].get_cdptlv_type
    get_cdptlv_type.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_type.restype = guint16

# /home/alanr/monitor/src/include/cdp.h: 72
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdptlv_len'):
    get_cdptlv_len = _libs['libassimilationclientlib.so'].get_cdptlv_len
    get_cdptlv_len.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_len.restype = gsize

# /home/alanr/monitor/src/include/cdp.h: 73
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdptlv_vlen'):
    get_cdptlv_vlen = _libs['libassimilationclientlib.so'].get_cdptlv_vlen
    get_cdptlv_vlen.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_vlen.restype = gsize

# /home/alanr/monitor/src/include/cdp.h: 74
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdptlv_body'):
    get_cdptlv_body = _libs['libassimilationclientlib.so'].get_cdptlv_body
    get_cdptlv_body.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_body.restype = gconstpointer

# /home/alanr/monitor/src/include/cdp.h: 75
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdptlv_first'):
    get_cdptlv_first = _libs['libassimilationclientlib.so'].get_cdptlv_first
    get_cdptlv_first.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_first.restype = gconstpointer

# /home/alanr/monitor/src/include/cdp.h: 76
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdptlv_next'):
    get_cdptlv_next = _libs['libassimilationclientlib.so'].get_cdptlv_next
    get_cdptlv_next.argtypes = [gconstpointer, gconstpointer]
    get_cdptlv_next.restype = gconstpointer

# /home/alanr/monitor/src/include/cdp.h: 77
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdp_chassis_id'):
    get_cdp_chassis_id = _libs['libassimilationclientlib.so'].get_cdp_chassis_id
    get_cdp_chassis_id.argtypes = [gconstpointer, POINTER(gssize), gconstpointer]
    get_cdp_chassis_id.restype = gconstpointer

# /home/alanr/monitor/src/include/cdp.h: 78
if hasattr(_libs['libassimilationclientlib.so'], 'get_cdp_port_id'):
    get_cdp_port_id = _libs['libassimilationclientlib.so'].get_cdp_port_id
    get_cdp_port_id.argtypes = [gconstpointer, POINTER(gssize), gconstpointer]
    get_cdp_port_id.restype = gconstpointer

# /home/alanr/monitor/src/include/cdp.h: 79
if hasattr(_libs['libassimilationclientlib.so'], 'is_valid_cdp_packet'):
    is_valid_cdp_packet = _libs['libassimilationclientlib.so'].is_valid_cdp_packet
    is_valid_cdp_packet.argtypes = [gconstpointer, gconstpointer]
    is_valid_cdp_packet.restype = gboolean

# /home/alanr/monitor/src/include/cdp.h: 80
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'enable_cdp_packets'):
        continue
    enable_cdp_packets = _lib.enable_cdp_packets
    enable_cdp_packets.argtypes = [gboolean]
    enable_cdp_packets.restype = gboolean
    break

# /home/alanr/monitor/src/include/cmalib.h: 31
if hasattr(_libs['libassimilationclientlib.so'], 'create_sendexpecthb'):
    create_sendexpecthb = _libs['libassimilationclientlib.so'].create_sendexpecthb
    create_sendexpecthb.argtypes = [POINTER(ConfigContext), guint16, POINTER(NetAddr), c_int]
    create_sendexpecthb.restype = POINTER(FrameSet)

# /home/alanr/monitor/src/include/cmalib.h: 32
if hasattr(_libs['libassimilationclientlib.so'], 'create_setconfig'):
    create_setconfig = _libs['libassimilationclientlib.so'].create_setconfig
    create_setconfig.argtypes = [POINTER(ConfigContext)]
    create_setconfig.restype = POINTER(FrameSet)

# /home/alanr/monitor/src/include/compressframe.h: 33
class struct__CompressFrame(Structure):
    pass

CompressFrame = struct__CompressFrame # /home/alanr/monitor/src/include/compressframe.h: 30

struct__CompressFrame.__slots__ = [
    'baseclass',
    'compression_method',
]
struct__CompressFrame._fields_ = [
    ('baseclass', Frame),
    ('compression_method', guint16),
]

# /home/alanr/monitor/src/include/compressframe.h: 38
if hasattr(_libs['libassimilationclientlib.so'], 'compressframe_new'):
    compressframe_new = _libs['libassimilationclientlib.so'].compressframe_new
    compressframe_new.argtypes = [guint16, guint16]
    compressframe_new.restype = POINTER(CompressFrame)

# /home/alanr/monitor/src/include/compressframe.h: 39
if hasattr(_libs['libassimilationclientlib.so'], 'compressframe_tlvconstructor'):
    compressframe_tlvconstructor = _libs['libassimilationclientlib.so'].compressframe_tlvconstructor
    compressframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    compressframe_tlvconstructor.restype = POINTER(Frame)

# /home/alanr/monitor/src/include/cryptframe.h: 33
class struct__CryptFrame(Structure):
    pass

CryptFrame = struct__CryptFrame # /home/alanr/monitor/src/include/cryptframe.h: 30

struct__CryptFrame.__slots__ = [
    'baseclass',
    'encryption_method',
    'encryption_key_info',
]
struct__CryptFrame._fields_ = [
    ('baseclass', Frame),
    ('encryption_method', c_int),
    ('encryption_key_info', POINTER(None)),
]

# /home/alanr/monitor/src/include/cryptframe.h: 39
if hasattr(_libs['libassimilationclientlib.so'], 'cryptframe_new'):
    cryptframe_new = _libs['libassimilationclientlib.so'].cryptframe_new
    cryptframe_new.argtypes = [guint16, guint16, POINTER(None)]
    cryptframe_new.restype = POINTER(CryptFrame)

# /home/alanr/monitor/src/include/cryptframe.h: 40
if hasattr(_libs['libassimilationclientlib.so'], 'cryptframe_tlvconstructor'):
    cryptframe_tlvconstructor = _libs['libassimilationclientlib.so'].cryptframe_tlvconstructor
    cryptframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    cryptframe_tlvconstructor.restype = POINTER(Frame)

# /home/alanr/monitor/src/include/cstringframe.h: 35
class struct__CstringFrame(Structure):
    pass

CstringFrame = struct__CstringFrame # /home/alanr/monitor/src/include/cstringframe.h: 30

struct__CstringFrame.__slots__ = [
    'baseclass',
]
struct__CstringFrame._fields_ = [
    ('baseclass', Frame),
]

# /home/alanr/monitor/src/include/cstringframe.h: 39
if hasattr(_libs['libassimilationclientlib.so'], 'cstringframe_new'):
    cstringframe_new = _libs['libassimilationclientlib.so'].cstringframe_new
    cstringframe_new.argtypes = [guint16, gsize]
    cstringframe_new.restype = POINTER(CstringFrame)

# /home/alanr/monitor/src/include/cstringframe.h: 40
if hasattr(_libs['libassimilationclientlib.so'], 'cstringframe_tlvconstructor'):
    cstringframe_tlvconstructor = _libs['libassimilationclientlib.so'].cstringframe_tlvconstructor
    cstringframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    cstringframe_tlvconstructor.restype = POINTER(Frame)

# /home/alanr/monitor/src/include/discovery.h: 47
class struct__Discovery(Structure):
    pass

Discovery = struct__Discovery # /home/alanr/monitor/src/include/discovery.h: 45

struct__Discovery.__slots__ = [
    'baseclass',
    'instancename',
    'flushcache',
    'discover',
    'discoverintervalsecs',
    'reportcount',
    'discovercount',
    '_instancename',
    '_timerid',
    '_iosource',
    '_config',
    '_sentyet',
]
struct__Discovery._fields_ = [
    ('baseclass', AssimObj),
    ('instancename', CFUNCTYPE(UNCHECKED(String), POINTER(Discovery))),
    ('flushcache', CFUNCTYPE(UNCHECKED(None), POINTER(Discovery))),
    ('discover', CFUNCTYPE(UNCHECKED(gboolean), POINTER(Discovery))),
    ('discoverintervalsecs', CFUNCTYPE(UNCHECKED(guint), POINTER(Discovery))),
    ('reportcount', guint64),
    ('discovercount', guint64),
    ('_instancename', String),
    ('_timerid', guint),
    ('_iosource', POINTER(NetGSource)),
    ('_config', POINTER(ConfigContext)),
    ('_sentyet', gboolean),
]

# /home/alanr/monitor/src/include/discovery.h: 66
if hasattr(_libs['libassimilationclientlib.so'], 'discovery_new'):
    discovery_new = _libs['libassimilationclientlib.so'].discovery_new
    discovery_new.argtypes = [String, POINTER(NetGSource), POINTER(ConfigContext), gsize]
    discovery_new.restype = POINTER(Discovery)

# /home/alanr/monitor/src/include/discovery.h: 67
if hasattr(_libs['libassimilationclientlib.so'], 'discovery_register'):
    discovery_register = _libs['libassimilationclientlib.so'].discovery_register
    discovery_register.argtypes = [POINTER(Discovery)]
    discovery_register.restype = None

# /home/alanr/monitor/src/include/discovery.h: 68
if hasattr(_libs['libassimilationclientlib.so'], 'discovery_unregister_all'):
    discovery_unregister_all = _libs['libassimilationclientlib.so'].discovery_unregister_all
    discovery_unregister_all.argtypes = []
    discovery_unregister_all.restype = None

# /home/alanr/monitor/src/include/discovery.h: 69
if hasattr(_libs['libassimilationclientlib.so'], 'discovery_unregister'):
    discovery_unregister = _libs['libassimilationclientlib.so'].discovery_unregister
    discovery_unregister.argtypes = [String]
    discovery_unregister.restype = None

# ../include/fsqueue.h: 45
class struct__FsQueue(Structure):
    pass

FsQueue = struct__FsQueue # ../include/fsqueue.h: 37

struct__FsQueue.__slots__ = [
    'baseclass',
    '_nextseqno',
    '_sessionid',
    '_maxqlen',
    '_curqlen',
    '_q',
    '_destaddr',
    '_qid',
    'isready',
    'enq',
    'inqsorted',
    'qhead',
    'deq',
    'ackthrough',
    'flush',
    'flush1',
    'qlen',
    'setmaxqlen',
    'getmaxqlen',
    'hasqspace1',
    'hasqspace',
]
struct__FsQueue._fields_ = [
    ('baseclass', AssimObj),
    ('_nextseqno', guint64),
    ('_sessionid', guint32),
    ('_maxqlen', guint),
    ('_curqlen', guint),
    ('_q', POINTER(GQueue)),
    ('_destaddr', POINTER(NetAddr)),
    ('_qid', guint16),
    ('isready', gboolean),
    ('enq', CFUNCTYPE(UNCHECKED(gboolean), POINTER(FsQueue), POINTER(FrameSet))),
    ('inqsorted', CFUNCTYPE(UNCHECKED(gboolean), POINTER(FsQueue), POINTER(FrameSet))),
    ('qhead', CFUNCTYPE(UNCHECKED(POINTER(FrameSet)), POINTER(FsQueue))),
    ('deq', CFUNCTYPE(UNCHECKED(POINTER(FrameSet)), POINTER(FsQueue))),
    ('ackthrough', CFUNCTYPE(UNCHECKED(guint), POINTER(FsQueue), POINTER(SeqnoFrame))),
    ('flush', CFUNCTYPE(UNCHECKED(None), POINTER(FsQueue))),
    ('flush1', CFUNCTYPE(UNCHECKED(None), POINTER(FsQueue))),
    ('qlen', CFUNCTYPE(UNCHECKED(guint), POINTER(FsQueue))),
    ('setmaxqlen', CFUNCTYPE(UNCHECKED(None), POINTER(FsQueue), guint)),
    ('getmaxqlen', CFUNCTYPE(UNCHECKED(guint), POINTER(FsQueue))),
    ('hasqspace1', CFUNCTYPE(UNCHECKED(gboolean), POINTER(FsQueue))),
    ('hasqspace', CFUNCTYPE(UNCHECKED(gboolean), POINTER(FsQueue), guint)),
]

# ../include/fsqueue.h: 77
if hasattr(_libs['libassimilationclientlib.so'], 'fsqueue_new'):
    fsqueue_new = _libs['libassimilationclientlib.so'].fsqueue_new
    fsqueue_new.argtypes = [guint, POINTER(NetAddr), guint16]
    fsqueue_new.restype = POINTER(FsQueue)

# /home/alanr/monitor/src/include/fsprotocol.h: 70
class struct__FsProtocol(Structure):
    pass

FsProtocol = struct__FsProtocol # /home/alanr/monitor/src/include/fsprotocol.h: 43

# /home/alanr/monitor/src/include/fsprotocol.h: 51
class struct__FsProtoElem(Structure):
    pass

FsProtoElem = struct__FsProtoElem # /home/alanr/monitor/src/include/fsprotocol.h: 44

# /home/alanr/monitor/src/include/fsprotocol.h: 62
class struct__FsProtoElemSearchKey(Structure):
    pass

FsProtoElemSearchKey = struct__FsProtoElemSearchKey # /home/alanr/monitor/src/include/fsprotocol.h: 45

struct__FsProtoElem.__slots__ = [
    'endpoint',
    '_qid',
    'outq',
    'inq',
    'lastacksent',
    'lastseqsent',
    'nextrexmit',
    'parent',
]
struct__FsProtoElem._fields_ = [
    ('endpoint', POINTER(NetAddr)),
    ('_qid', guint16),
    ('outq', POINTER(FsQueue)),
    ('inq', POINTER(FsQueue)),
    ('lastacksent', POINTER(SeqnoFrame)),
    ('lastseqsent', POINTER(SeqnoFrame)),
    ('nextrexmit', gint64),
    ('parent', POINTER(FsProtocol)),
]

struct__FsProtoElemSearchKey.__slots__ = [
    'endpoint',
    '_qid',
]
struct__FsProtoElemSearchKey._fields_ = [
    ('endpoint', POINTER(NetAddr)),
    ('_qid', guint16),
]

struct__FsProtocol.__slots__ = [
    'baseclass',
    'io',
    'endpoints',
    'unacked',
    'ipend',
    'window_size',
    'rexmit_interval',
    '_timersrc',
    'find',
    'findbypkt',
    'addconn',
    'closeconn',
    'iready',
    'read',
    'receive',
    'send1',
    'send',
    'ackmessage',
]
struct__FsProtocol._fields_ = [
    ('baseclass', AssimObj),
    ('io', POINTER(NetIO)),
    ('endpoints', POINTER(GHashTable)),
    ('unacked', POINTER(GList)),
    ('ipend', POINTER(GList)),
    ('window_size', guint),
    ('rexmit_interval', gint64),
    ('_timersrc', guint),
    ('find', CFUNCTYPE(UNCHECKED(POINTER(FsProtoElem)), POINTER(FsProtocol), guint16, POINTER(NetAddr))),
    ('findbypkt', CFUNCTYPE(UNCHECKED(POINTER(FsProtoElem)), POINTER(FsProtocol), POINTER(NetAddr), POINTER(FrameSet))),
    ('addconn', CFUNCTYPE(UNCHECKED(POINTER(FsProtoElem)), POINTER(FsProtocol), guint16, POINTER(NetAddr))),
    ('closeconn', CFUNCTYPE(UNCHECKED(None), POINTER(FsProtocol), guint16, POINTER(NetAddr))),
    ('iready', CFUNCTYPE(UNCHECKED(gboolean), POINTER(FsProtocol))),
    ('read', CFUNCTYPE(UNCHECKED(POINTER(FrameSet)), POINTER(FsProtocol), POINTER(POINTER(NetAddr)))),
    ('receive', CFUNCTYPE(UNCHECKED(None), POINTER(FsProtocol), POINTER(NetAddr), POINTER(FrameSet))),
    ('send1', CFUNCTYPE(UNCHECKED(gboolean), POINTER(FsProtocol), POINTER(FrameSet), guint16, POINTER(NetAddr))),
    ('send', CFUNCTYPE(UNCHECKED(gboolean), POINTER(FsProtocol), POINTER(GSList), guint16, POINTER(NetAddr))),
    ('ackmessage', CFUNCTYPE(UNCHECKED(None), POINTER(FsProtocol), POINTER(NetAddr), POINTER(FrameSet))),
]

# /home/alanr/monitor/src/include/fsprotocol.h: 90
if hasattr(_libs['libassimilationclientlib.so'], 'fsprotocol_new'):
    fsprotocol_new = _libs['libassimilationclientlib.so'].fsprotocol_new
    fsprotocol_new.argtypes = [guint, POINTER(NetIO), guint]
    fsprotocol_new.restype = POINTER(FsProtocol)

# /home/alanr/monitor/src/include/generic_tlv_min.h: 27
if hasattr(_libs['libassimilationclientlib.so'], 'get_generic_tlv_type'):
    get_generic_tlv_type = _libs['libassimilationclientlib.so'].get_generic_tlv_type
    get_generic_tlv_type.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_type.restype = guint16

# /home/alanr/monitor/src/include/generic_tlv_min.h: 28
if hasattr(_libs['libassimilationclientlib.so'], 'get_generic_tlv_len'):
    get_generic_tlv_len = _libs['libassimilationclientlib.so'].get_generic_tlv_len
    get_generic_tlv_len.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_len.restype = guint16

# /home/alanr/monitor/src/include/generic_tlv_min.h: 29
if hasattr(_libs['libassimilationclientlib.so'], 'get_generic_tlv_value'):
    get_generic_tlv_value = _libs['libassimilationclientlib.so'].get_generic_tlv_value
    get_generic_tlv_value.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_value.restype = gconstpointer

# /home/alanr/monitor/src/include/generic_tlv_min.h: 30
if hasattr(_libs['libassimilationclientlib.so'], 'get_generic_tlv_nonconst_value'):
    get_generic_tlv_nonconst_value = _libs['libassimilationclientlib.so'].get_generic_tlv_nonconst_value
    get_generic_tlv_nonconst_value.argtypes = [gpointer, gconstpointer]
    get_generic_tlv_nonconst_value.restype = gpointer

# /home/alanr/monitor/src/include/generic_tlv_min.h: 31
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_generic_tlv_totalsize'):
        continue
    get_generic_tlv_totalsize = _lib.get_generic_tlv_totalsize
    get_generic_tlv_totalsize.argtypes = [gsize]
    get_generic_tlv_totalsize.restype = guint16
    break

# /home/alanr/monitor/src/include/generic_tlv_min.h: 32
if hasattr(_libs['libassimilationclientlib.so'], 'is_valid_generic_tlv_packet'):
    is_valid_generic_tlv_packet = _libs['libassimilationclientlib.so'].is_valid_generic_tlv_packet
    is_valid_generic_tlv_packet.argtypes = [gconstpointer, gconstpointer]
    is_valid_generic_tlv_packet.restype = gboolean

# /home/alanr/monitor/src/include/generic_tlv_min.h: 33
if hasattr(_libs['libassimilationclientlib.so'], 'get_generic_tlv_first'):
    get_generic_tlv_first = _libs['libassimilationclientlib.so'].get_generic_tlv_first
    get_generic_tlv_first.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_first.restype = gconstpointer

# /home/alanr/monitor/src/include/generic_tlv_min.h: 34
if hasattr(_libs['libassimilationclientlib.so'], 'get_generic_tlv_next'):
    get_generic_tlv_next = _libs['libassimilationclientlib.so'].get_generic_tlv_next
    get_generic_tlv_next.argtypes = [gconstpointer, gconstpointer]
    get_generic_tlv_next.restype = gconstpointer

# /home/alanr/monitor/src/include/generic_tlv_min.h: 35
if hasattr(_libs['libassimilationclientlib.so'], 'find_next_generic_tlv_type'):
    find_next_generic_tlv_type = _libs['libassimilationclientlib.so'].find_next_generic_tlv_type
    find_next_generic_tlv_type.argtypes = [gconstpointer, guint16, gconstpointer]
    find_next_generic_tlv_type.restype = gconstpointer

# /home/alanr/monitor/src/include/generic_tlv_min.h: 36
if hasattr(_libs['libassimilationclientlib.so'], 'set_generic_tlv_type'):
    set_generic_tlv_type = _libs['libassimilationclientlib.so'].set_generic_tlv_type
    set_generic_tlv_type.argtypes = [gpointer, guint16, gconstpointer]
    set_generic_tlv_type.restype = None

# /home/alanr/monitor/src/include/generic_tlv_min.h: 37
if hasattr(_libs['libassimilationclientlib.so'], 'set_generic_tlv_len'):
    set_generic_tlv_len = _libs['libassimilationclientlib.so'].set_generic_tlv_len
    set_generic_tlv_len.argtypes = [gpointer, guint16, gconstpointer]
    set_generic_tlv_len.restype = None

# /home/alanr/monitor/src/include/generic_tlv_min.h: 38
if hasattr(_libs['libassimilationclientlib.so'], 'set_generic_tlv_value'):
    set_generic_tlv_value = _libs['libassimilationclientlib.so'].set_generic_tlv_value
    set_generic_tlv_value.argtypes = [gpointer, POINTER(None), guint16, gconstpointer]
    set_generic_tlv_value.restype = None

# /home/alanr/monitor/src/include/hblistener.h: 44
class struct__HbListener(Structure):
    pass

HbListener = struct__HbListener # /home/alanr/monitor/src/include/hblistener.h: 32

enum_anon_103 = c_int # /home/alanr/monitor/src/include/hblistener.h: 37

HbPacketsBeingReceived = 1 # /home/alanr/monitor/src/include/hblistener.h: 37

HbPacketsTimedOut = 2 # /home/alanr/monitor/src/include/hblistener.h: 37

HbNodeStatus = enum_anon_103 # /home/alanr/monitor/src/include/hblistener.h: 37

struct__HbListener.__slots__ = [
    'baseclass',
    'get_deadtime',
    'set_deadtime',
    'get_warntime',
    'set_warntime',
    'set_heartbeat_callback',
    'set_deadtime_callback',
    'set_warntime_callback',
    'set_comealive_callback',
    '_expected_interval',
    '_warn_interval',
    'nexttime',
    'warntime',
    '_refcount',
    'listenaddr',
    'status',
    '_heartbeat_callback',
    '_deadtime_callback',
    '_warntime_callback',
    '_comealive_callback',
]
struct__HbListener._fields_ = [
    ('baseclass', Listener),
    ('get_deadtime', CFUNCTYPE(UNCHECKED(guint64), POINTER(HbListener))),
    ('set_deadtime', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64)),
    ('get_warntime', CFUNCTYPE(UNCHECKED(guint64), POINTER(HbListener))),
    ('set_warntime', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64)),
    ('set_heartbeat_callback', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), CFUNCTYPE(UNCHECKED(None), POINTER(HbListener)))),
    ('set_deadtime_callback', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), CFUNCTYPE(UNCHECKED(None), POINTER(HbListener)))),
    ('set_warntime_callback', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64))),
    ('set_comealive_callback', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64))),
    ('_expected_interval', guint64),
    ('_warn_interval', guint64),
    ('nexttime', guint64),
    ('warntime', guint64),
    ('_refcount', c_int),
    ('listenaddr', POINTER(NetAddr)),
    ('status', HbNodeStatus),
    ('_heartbeat_callback', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener))),
    ('_deadtime_callback', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener))),
    ('_warntime_callback', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64)),
    ('_comealive_callback', CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64)),
]

# /home/alanr/monitor/src/include/hblistener.h: 68
if hasattr(_libs['libassimilationclientlib.so'], 'hblistener_new'):
    hblistener_new = _libs['libassimilationclientlib.so'].hblistener_new
    hblistener_new.argtypes = [POINTER(NetAddr), POINTER(ConfigContext), gsize]
    hblistener_new.restype = POINTER(HbListener)

# /home/alanr/monitor/src/include/hblistener.h: 69
if hasattr(_libs['libassimilationclientlib.so'], 'hblistener_unlisten'):
    hblistener_unlisten = _libs['libassimilationclientlib.so'].hblistener_unlisten
    hblistener_unlisten.argtypes = [POINTER(NetAddr)]
    hblistener_unlisten.restype = None

# /home/alanr/monitor/src/include/hblistener.h: 70
if hasattr(_libs['libassimilationclientlib.so'], 'hblistener_set_martian_callback'):
    hblistener_set_martian_callback = _libs['libassimilationclientlib.so'].hblistener_set_martian_callback
    hblistener_set_martian_callback.argtypes = [CFUNCTYPE(UNCHECKED(None), POINTER(NetAddr))]
    hblistener_set_martian_callback.restype = None

# /home/alanr/monitor/src/include/hblistener.h: 71
if hasattr(_libs['libassimilationclientlib.so'], 'hblistener_find_by_address'):
    hblistener_find_by_address = _libs['libassimilationclientlib.so'].hblistener_find_by_address
    hblistener_find_by_address.argtypes = [POINTER(NetAddr)]
    hblistener_find_by_address.restype = POINTER(HbListener)

# /home/alanr/monitor/src/include/hbsender.h: 39
class struct__HbSender(Structure):
    pass

HbSender = struct__HbSender # /home/alanr/monitor/src/include/hbsender.h: 32

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
    ('_outmethod', POINTER(NetGSource)),
    ('_sendaddr', POINTER(NetAddr)),
    ('_refcount', c_int),
    ('timeout_source', guint),
]

# /home/alanr/monitor/src/include/hbsender.h: 51
if hasattr(_libs['libassimilationclientlib.so'], 'hbsender_new'):
    hbsender_new = _libs['libassimilationclientlib.so'].hbsender_new
    hbsender_new.argtypes = [POINTER(NetAddr), POINTER(NetGSource), guint, gsize]
    hbsender_new.restype = POINTER(HbSender)

# /home/alanr/monitor/src/include/hbsender.h: 52
if hasattr(_libs['libassimilationclientlib.so'], 'hbsender_stopsend'):
    hbsender_stopsend = _libs['libassimilationclientlib.so'].hbsender_stopsend
    hbsender_stopsend.argtypes = [POINTER(NetAddr)]
    hbsender_stopsend.restype = None

# /home/alanr/monitor/src/include/hbsender.h: 53
if hasattr(_libs['libassimilationclientlib.so'], 'hbsender_stopallsenders'):
    hbsender_stopallsenders = _libs['libassimilationclientlib.so'].hbsender_stopallsenders
    hbsender_stopallsenders.argtypes = []
    hbsender_stopallsenders.restype = None

# /home/alanr/monitor/src/include/intframe.h: 39
class struct__IntFrame(Structure):
    pass

IntFrame = struct__IntFrame # /home/alanr/monitor/src/include/intframe.h: 35

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

# /home/alanr/monitor/src/include/intframe.h: 47
if hasattr(_libs['libassimilationclientlib.so'], 'intframe_new'):
    intframe_new = _libs['libassimilationclientlib.so'].intframe_new
    intframe_new.argtypes = [guint16, c_int]
    intframe_new.restype = POINTER(IntFrame)

# /home/alanr/monitor/src/include/intframe.h: 48
if hasattr(_libs['libassimilationclientlib.so'], 'intframe_tlvconstructor'):
    intframe_tlvconstructor = _libs['libassimilationclientlib.so'].intframe_tlvconstructor
    intframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    intframe_tlvconstructor.restype = POINTER(Frame)

# /home/alanr/monitor/src/include/ipportframe.h: 40
class struct__IpPortFrame(Structure):
    pass

IpPortFrame = struct__IpPortFrame # /home/alanr/monitor/src/include/ipportframe.h: 32

struct__IpPortFrame.__slots__ = [
    'baseclass',
    '_addr',
    'port',
    '_basefinal',
    'getnetaddr',
]
struct__IpPortFrame._fields_ = [
    ('baseclass', Frame),
    ('_addr', POINTER(NetAddr)),
    ('port', guint16),
    ('_basefinal', CFUNCTYPE(UNCHECKED(None), POINTER(AssimObj))),
    ('getnetaddr', CFUNCTYPE(UNCHECKED(POINTER(NetAddr)), POINTER(IpPortFrame))),
]

# /home/alanr/monitor/src/include/ipportframe.h: 48
if hasattr(_libs['libassimilationclientlib.so'], 'ipportframe_netaddr_new'):
    ipportframe_netaddr_new = _libs['libassimilationclientlib.so'].ipportframe_netaddr_new
    ipportframe_netaddr_new.argtypes = [guint16, POINTER(NetAddr)]
    ipportframe_netaddr_new.restype = POINTER(IpPortFrame)

# /home/alanr/monitor/src/include/ipportframe.h: 49
if hasattr(_libs['libassimilationclientlib.so'], 'ipportframe_ipv4_new'):
    ipportframe_ipv4_new = _libs['libassimilationclientlib.so'].ipportframe_ipv4_new
    ipportframe_ipv4_new.argtypes = [guint16, guint16, gconstpointer]
    ipportframe_ipv4_new.restype = POINTER(IpPortFrame)

# /home/alanr/monitor/src/include/ipportframe.h: 50
if hasattr(_libs['libassimilationclientlib.so'], 'ipportframe_ipv6_new'):
    ipportframe_ipv6_new = _libs['libassimilationclientlib.so'].ipportframe_ipv6_new
    ipportframe_ipv6_new.argtypes = [guint16, guint16, gconstpointer]
    ipportframe_ipv6_new.restype = POINTER(IpPortFrame)

# /home/alanr/monitor/src/include/ipportframe.h: 51
if hasattr(_libs['libassimilationclientlib.so'], 'ipportframe_tlvconstructor'):
    ipportframe_tlvconstructor = _libs['libassimilationclientlib.so'].ipportframe_tlvconstructor
    ipportframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    ipportframe_tlvconstructor.restype = POINTER(Frame)

# /home/alanr/monitor/src/include/jsondiscovery.h: 36
class struct__JsonDiscovery(Structure):
    pass

JsonDiscovery = struct__JsonDiscovery # /home/alanr/monitor/src/include/jsondiscovery.h: 34

struct__JsonDiscovery.__slots__ = [
    'baseclass',
    'instancename',
    '_fullpath',
    '_tmpfilename',
    '_child_pid',
    '_sourceid',
    '_intervalsecs',
    'jsonparams',
    'fullpath',
]
struct__JsonDiscovery._fields_ = [
    ('baseclass', Discovery),
    ('instancename', String),
    ('_fullpath', String),
    ('_tmpfilename', String),
    ('_child_pid', GPid),
    ('_sourceid', guint),
    ('_intervalsecs', guint),
    ('jsonparams', POINTER(ConfigContext)),
    ('fullpath', CFUNCTYPE(UNCHECKED(String), POINTER(JsonDiscovery))),
]

# /home/alanr/monitor/src/include/jsondiscovery.h: 47
if hasattr(_libs['libassimilationclientlib.so'], 'jsondiscovery_new'):
    jsondiscovery_new = _libs['libassimilationclientlib.so'].jsondiscovery_new
    jsondiscovery_new.argtypes = [String, String, c_int, POINTER(ConfigContext), POINTER(NetGSource), POINTER(ConfigContext), gsize]
    jsondiscovery_new.restype = POINTER(JsonDiscovery)

# /home/alanr/monitor/src/include/lldp.h: 121
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldp_chassis_id_type'):
        continue
    get_lldp_chassis_id_type = _lib.get_lldp_chassis_id_type
    get_lldp_chassis_id_type.argtypes = [gconstpointer, gconstpointer]
    get_lldp_chassis_id_type.restype = c_uint
    break

# /home/alanr/monitor/src/include/lldp.h: 122
if hasattr(_libs['libassimilationclientlib.so'], 'get_lldp_chassis_id'):
    get_lldp_chassis_id = _libs['libassimilationclientlib.so'].get_lldp_chassis_id
    get_lldp_chassis_id.argtypes = [gconstpointer, POINTER(gssize), gconstpointer]
    get_lldp_chassis_id.restype = gconstpointer

# /home/alanr/monitor/src/include/lldp.h: 123
if hasattr(_libs['libassimilationclientlib.so'], 'get_lldp_port_id'):
    get_lldp_port_id = _libs['libassimilationclientlib.so'].get_lldp_port_id
    get_lldp_port_id.argtypes = [gconstpointer, POINTER(gssize), gconstpointer]
    get_lldp_port_id.restype = gconstpointer

# /home/alanr/monitor/src/include/lldp.h: 124
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'get_lldp_port_id_type'):
        continue
    get_lldp_port_id_type = _lib.get_lldp_port_id_type
    get_lldp_port_id_type.argtypes = [gconstpointer, gconstpointer]
    get_lldp_port_id_type.restype = c_uint
    break

# /home/alanr/monitor/src/include/lldp.h: 126
if hasattr(_libs['libassimilationclientlib.so'], 'get_lldptlv_type'):
    get_lldptlv_type = _libs['libassimilationclientlib.so'].get_lldptlv_type
    get_lldptlv_type.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_type.restype = guint8

# /home/alanr/monitor/src/include/lldp.h: 127
if hasattr(_libs['libassimilationclientlib.so'], 'get_lldptlv_len'):
    get_lldptlv_len = _libs['libassimilationclientlib.so'].get_lldptlv_len
    get_lldptlv_len.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_len.restype = gsize

# /home/alanr/monitor/src/include/lldp.h: 128
if hasattr(_libs['libassimilationclientlib.so'], 'get_lldptlv_first'):
    get_lldptlv_first = _libs['libassimilationclientlib.so'].get_lldptlv_first
    get_lldptlv_first.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_first.restype = gconstpointer

# /home/alanr/monitor/src/include/lldp.h: 129
if hasattr(_libs['libassimilationclientlib.so'], 'get_lldptlv_next'):
    get_lldptlv_next = _libs['libassimilationclientlib.so'].get_lldptlv_next
    get_lldptlv_next.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_next.restype = gconstpointer

# /home/alanr/monitor/src/include/lldp.h: 130
if hasattr(_libs['libassimilationclientlib.so'], 'get_lldptlv_body'):
    get_lldptlv_body = _libs['libassimilationclientlib.so'].get_lldptlv_body
    get_lldptlv_body.argtypes = [gconstpointer, gconstpointer]
    get_lldptlv_body.restype = gconstpointer

# /home/alanr/monitor/src/include/lldp.h: 131
if hasattr(_libs['libassimilationclientlib.so'], 'find_next_lldptlv_type'):
    find_next_lldptlv_type = _libs['libassimilationclientlib.so'].find_next_lldptlv_type
    find_next_lldptlv_type.argtypes = [gconstpointer, c_uint, gconstpointer]
    find_next_lldptlv_type.restype = gconstpointer

# /home/alanr/monitor/src/include/lldp.h: 132
if hasattr(_libs['libassimilationclientlib.so'], 'is_valid_lldp_packet'):
    is_valid_lldp_packet = _libs['libassimilationclientlib.so'].is_valid_lldp_packet
    is_valid_lldp_packet.argtypes = [gconstpointer, gconstpointer]
    is_valid_lldp_packet.restype = gboolean

# /home/alanr/monitor/src/include/lldp.h: 133
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'enable_lldp_packets'):
        continue
    enable_lldp_packets = _lib.enable_lldp_packets
    enable_lldp_packets.argtypes = [gboolean]
    enable_lldp_packets.restype = gboolean
    break

# /home/alanr/monitor/src/include/misc.h: 27
if hasattr(_libs['libassimilationclientlib.so'], 'daemonize_me'):
    daemonize_me = _libs['libassimilationclientlib.so'].daemonize_me
    daemonize_me.argtypes = [gboolean, String]
    daemonize_me.restype = None

# /home/alanr/monitor/src/include/nanoprobe.h: 32
class struct__NanoHbStats(Structure):
    pass

NanoHbStats = struct__NanoHbStats # /home/alanr/monitor/src/include/nanoprobe.h: 31

struct__NanoHbStats.__slots__ = [
    'heartbeat_count',
    'dead_count',
    'warntime_count',
    'comealive_count',
    'martian_count',
]
struct__NanoHbStats._fields_ = [
    ('heartbeat_count', guint64),
    ('dead_count', guint),
    ('warntime_count', guint),
    ('comealive_count', guint),
    ('martian_count', guint),
]

# /home/alanr/monitor/src/include/nanoprobe.h: 39
try:
    nano_hbstats = (NanoHbStats).in_dll(_libs['libassimilationclientlib.so'], 'nano_hbstats')
except:
    pass

# /home/alanr/monitor/src/include/nanoprobe.h: 41
if hasattr(_libs['libassimilationclientlib.so'], 'nano_start_full'):
    nano_start_full = _libs['libassimilationclientlib.so'].nano_start_full
    nano_start_full.argtypes = [String, guint, POINTER(NetGSource), POINTER(ConfigContext)]
    nano_start_full.restype = None

# /home/alanr/monitor/src/include/nanoprobe.h: 43
if hasattr(_libs['libassimilationclientlib.so'], 'nano_shutdown'):
    nano_shutdown = _libs['libassimilationclientlib.so'].nano_shutdown
    nano_shutdown.argtypes = [gboolean]
    nano_shutdown.restype = None

# /home/alanr/monitor/src/include/nanoprobe.h: 44
if hasattr(_libs['libassimilationclientlib.so'], 'nano_packet_decoder'):
    nano_packet_decoder = _libs['libassimilationclientlib.so'].nano_packet_decoder
    nano_packet_decoder.argtypes = []
    nano_packet_decoder.restype = POINTER(PacketDecoder)

# /home/alanr/monitor/src/include/nanoprobe.h: 45
if hasattr(_libs['libassimilationclientlib.so'], 'nanoprobe_report_upstream'):
    nanoprobe_report_upstream = _libs['libassimilationclientlib.so'].nanoprobe_report_upstream
    nanoprobe_report_upstream.argtypes = [guint16, POINTER(NetAddr), String, guint64]
    nanoprobe_report_upstream.restype = None

# /home/alanr/monitor/src/include/nanoprobe.h: 48
try:
    nanoprobe_deadtime_agent = (POINTER(CFUNCTYPE(UNCHECKED(None), POINTER(HbListener)))).in_dll(_libs['libassimilationclientlib.so'], 'nanoprobe_deadtime_agent')
except:
    pass

# /home/alanr/monitor/src/include/nanoprobe.h: 50
try:
    nanoprobe_heartbeat_agent = (POINTER(CFUNCTYPE(UNCHECKED(None), POINTER(HbListener)))).in_dll(_libs['libassimilationclientlib.so'], 'nanoprobe_heartbeat_agent')
except:
    pass

# /home/alanr/monitor/src/include/nanoprobe.h: 52
try:
    nanoprobe_warntime_agent = (POINTER(CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64))).in_dll(_libs['libassimilationclientlib.so'], 'nanoprobe_warntime_agent')
except:
    pass

# /home/alanr/monitor/src/include/nanoprobe.h: 54
try:
    nanoprobe_comealive_agent = (POINTER(CFUNCTYPE(UNCHECKED(None), POINTER(HbListener), guint64))).in_dll(_libs['libassimilationclientlib.so'], 'nanoprobe_comealive_agent')
except:
    pass

# /home/alanr/monitor/src/include/nanoprobe.h: 56
try:
    nanoprobe_hblistener_new = (POINTER(CFUNCTYPE(UNCHECKED(POINTER(HbListener)), POINTER(NetAddr), POINTER(ConfigContext)))).in_dll(_libs['libassimilationclientlib.so'], 'nanoprobe_hblistener_new')
except:
    pass

# /home/alanr/monitor/src/include/netioudp.h: 39
class struct__NetIOudp(Structure):
    pass

NetIOudp = struct__NetIOudp # /home/alanr/monitor/src/include/netioudp.h: 34

struct__NetIOudp.__slots__ = [
    'baseclass',
    '_finalize',
]
struct__NetIOudp._fields_ = [
    ('baseclass', NetIO),
    ('_finalize', GDestroyNotify),
]

# /home/alanr/monitor/src/include/netioudp.h: 43
if hasattr(_libs['libassimilationclientlib.so'], 'netioudp_new'):
    netioudp_new = _libs['libassimilationclientlib.so'].netioudp_new
    netioudp_new.argtypes = [gsize, POINTER(ConfigContext), POINTER(PacketDecoder)]
    netioudp_new.restype = POINTER(NetIOudp)

# /home/alanr/monitor/src/include/nvpairframe.h: 33
class struct__NVpairFrame(Structure):
    pass

NVpairFrame = struct__NVpairFrame # /home/alanr/monitor/src/include/nvpairframe.h: 30

struct__NVpairFrame.__slots__ = [
    'baseclass',
    'name',
    'value',
]
struct__NVpairFrame._fields_ = [
    ('baseclass', Frame),
    ('name', POINTER(gchar)),
    ('value', POINTER(gchar)),
]

# /home/alanr/monitor/src/include/nvpairframe.h: 39
if hasattr(_libs['libassimilationclientlib.so'], 'nvpairframe_new'):
    nvpairframe_new = _libs['libassimilationclientlib.so'].nvpairframe_new
    nvpairframe_new.argtypes = [guint16, POINTER(gchar), POINTER(gchar), gsize]
    nvpairframe_new.restype = POINTER(NVpairFrame)

# /home/alanr/monitor/src/include/nvpairframe.h: 40
if hasattr(_libs['libassimilationclientlib.so'], 'nvpairframe_tlvconstructor'):
    nvpairframe_tlvconstructor = _libs['libassimilationclientlib.so'].nvpairframe_tlvconstructor
    nvpairframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    nvpairframe_tlvconstructor.restype = POINTER(Frame)

bpf_u_int32 = u_int # /usr/include/pcap/bpf.h: 68

# /usr/include/pcap/bpf.h: 1042
class struct_bpf_insn(Structure):
    pass

# /usr/include/pcap/bpf.h: 88
class struct_bpf_program(Structure):
    pass

struct_bpf_program.__slots__ = [
    'bf_len',
    'bf_insns',
]
struct_bpf_program._fields_ = [
    ('bf_len', u_int),
    ('bf_insns', POINTER(struct_bpf_insn)),
]

struct_bpf_insn.__slots__ = [
    'code',
    'jt',
    'jf',
    'k',
]
struct_bpf_insn._fields_ = [
    ('code', u_short),
    ('jt', u_char),
    ('jf', u_char),
    ('k', bpf_u_int32),
]

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

# ../include/pcap_min.h: 44
if hasattr(_libs['libassimilationclientlib.so'], 'create_pcap_listener'):
    create_pcap_listener = _libs['libassimilationclientlib.so'].create_pcap_listener
    create_pcap_listener.argtypes = [String, gboolean, c_uint, POINTER(struct_bpf_program)]
    create_pcap_listener.restype = POINTER(pcap_t)

# ../include/pcap_min.h: 45
if hasattr(_libs['libassimilationclientlib.so'], 'close_pcap_listener'):
    close_pcap_listener = _libs['libassimilationclientlib.so'].close_pcap_listener
    close_pcap_listener.argtypes = [POINTER(pcap_t), String, c_uint]
    close_pcap_listener.restype = None

# /home/alanr/monitor/src/include/pcap_GSource.h: 38
class struct__GSource_pcap(Structure):
    pass

GSource_pcap_t = struct__GSource_pcap # /home/alanr/monitor/src/include/pcap_GSource.h: 33

struct__GSource_pcap.__slots__ = [
    'gs',
    'gfd',
    'capture',
    'pcprog',
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
    ('pcprog', struct_bpf_program),
    ('capturefd', c_int),
    ('capturedev', String),
    ('listenmask', c_uint),
    ('gsourceid', gint),
    ('userdata', gpointer),
    ('dispatch', CFUNCTYPE(UNCHECKED(gboolean), POINTER(GSource_pcap_t), POINTER(pcap_t), gconstpointer, gconstpointer, POINTER(struct_pcap_pkthdr), String, gpointer)),
    ('destroynote', GDestroyNotify),
]

# /home/alanr/monitor/src/include/pcap_GSource.h: 60
if hasattr(_libs['libassimilationclientlib.so'], 'g_source_pcap_new'):
    g_source_pcap_new = _libs['libassimilationclientlib.so'].g_source_pcap_new
    g_source_pcap_new.argtypes = [String, c_uint, CFUNCTYPE(UNCHECKED(gboolean), POINTER(GSource_pcap_t), POINTER(pcap_t), gconstpointer, gconstpointer, POINTER(struct_pcap_pkthdr), String, gpointer), GDestroyNotify, gint, gboolean, POINTER(GMainContext), gsize, gpointer]
    g_source_pcap_new.restype = POINTER(GSource)

# /home/alanr/monitor/src/include/pcap_GSource.h: 78
if hasattr(_libs['libassimilationclientlib.so'], 'g_source_pcap_finalize'):
    g_source_pcap_finalize = _libs['libassimilationclientlib.so'].g_source_pcap_finalize
    g_source_pcap_finalize.argtypes = [POINTER(GSource)]
    g_source_pcap_finalize.restype = None

# /home/alanr/monitor/src/include/pcap_GSource.h: 79
if hasattr(_libs['libassimilationclientlib.so'], 'construct_pcap_frameset'):
    construct_pcap_frameset = _libs['libassimilationclientlib.so'].construct_pcap_frameset
    construct_pcap_frameset.argtypes = [guint16, gconstpointer, gconstpointer, POINTER(struct_pcap_pkthdr), String]
    construct_pcap_frameset.restype = POINTER(FrameSet)

# /home/alanr/monitor/src/include/pcap_min.h: 44
if hasattr(_libs['libassimilationclientlib.so'], 'create_pcap_listener'):
    create_pcap_listener = _libs['libassimilationclientlib.so'].create_pcap_listener
    create_pcap_listener.argtypes = [String, gboolean, c_uint, POINTER(struct_bpf_program)]
    create_pcap_listener.restype = POINTER(pcap_t)

# /home/alanr/monitor/src/include/pcap_min.h: 45
if hasattr(_libs['libassimilationclientlib.so'], 'close_pcap_listener'):
    close_pcap_listener = _libs['libassimilationclientlib.so'].close_pcap_listener
    close_pcap_listener.argtypes = [POINTER(pcap_t), String, c_uint]
    close_pcap_listener.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 28
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_new'):
    proj_class_new = _libs['libassimilationclientlib.so'].proj_class_new
    proj_class_new.argtypes = [gsize, String]
    proj_class_new.restype = gpointer

# /home/alanr/monitor/src/include/proj_classes.h: 29
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_dissociate'):
    proj_class_dissociate = _libs['libassimilationclientlib.so'].proj_class_dissociate
    proj_class_dissociate.argtypes = [gpointer]
    proj_class_dissociate.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 30
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_free'):
    proj_class_free = _libs['libassimilationclientlib.so'].proj_class_free
    proj_class_free.argtypes = [gpointer]
    proj_class_free.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 31
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_register_object'):
    proj_class_register_object = _libs['libassimilationclientlib.so'].proj_class_register_object
    proj_class_register_object.argtypes = [gpointer, String]
    proj_class_register_object.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 32
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_is_a'):
    proj_class_is_a = _libs['libassimilationclientlib.so'].proj_class_is_a
    proj_class_is_a.argtypes = [gconstpointer, String]
    proj_class_is_a.restype = gboolean

# /home/alanr/monitor/src/include/proj_classes.h: 33
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_castas'):
    proj_class_castas = _libs['libassimilationclientlib.so'].proj_class_castas
    proj_class_castas.argtypes = [gpointer, String]
    proj_class_castas.restype = gpointer

# /home/alanr/monitor/src/include/proj_classes.h: 34
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_castasconst'):
    proj_class_castasconst = _libs['libassimilationclientlib.so'].proj_class_castasconst
    proj_class_castasconst.argtypes = [gconstpointer, String]
    proj_class_castasconst.restype = gconstpointer

# /home/alanr/monitor/src/include/proj_classes.h: 35
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_register_subclassed'):
    proj_class_register_subclassed = _libs['libassimilationclientlib.so'].proj_class_register_subclassed
    proj_class_register_subclassed.argtypes = [gpointer, String]
    proj_class_register_subclassed.restype = gpointer

# /home/alanr/monitor/src/include/proj_classes.h: 36
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_quark_add_superclass_relationship'):
    proj_class_quark_add_superclass_relationship = _libs['libassimilationclientlib.so'].proj_class_quark_add_superclass_relationship
    proj_class_quark_add_superclass_relationship.argtypes = [GQuark, GQuark]
    proj_class_quark_add_superclass_relationship.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 37
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_quark_is_a'):
    proj_class_quark_is_a = _libs['libassimilationclientlib.so'].proj_class_quark_is_a
    proj_class_quark_is_a.argtypes = [GQuark, GQuark]
    proj_class_quark_is_a.restype = gboolean

# /home/alanr/monitor/src/include/proj_classes.h: 38
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_classname'):
    proj_class_classname = _libs['libassimilationclientlib.so'].proj_class_classname
    proj_class_classname.argtypes = [gconstpointer]
    if sizeof(c_int) == sizeof(c_void_p):
        proj_class_classname.restype = ReturnString
    else:
        proj_class_classname.restype = String
        proj_class_classname.errcheck = ReturnString

# /home/alanr/monitor/src/include/proj_classes.h: 39
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_register_debug_counter'):
    proj_class_register_debug_counter = _libs['libassimilationclientlib.so'].proj_class_register_debug_counter
    proj_class_register_debug_counter.argtypes = [String, POINTER(guint)]
    proj_class_register_debug_counter.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 40
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_incr_debug'):
    proj_class_incr_debug = _libs['libassimilationclientlib.so'].proj_class_incr_debug
    proj_class_incr_debug.argtypes = [String]
    proj_class_incr_debug.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 41
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_decr_debug'):
    proj_class_decr_debug = _libs['libassimilationclientlib.so'].proj_class_decr_debug
    proj_class_decr_debug.argtypes = [String]
    proj_class_decr_debug.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 42
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_debug_dump'):
    proj_class_debug_dump = _libs['libassimilationclientlib.so'].proj_class_debug_dump
    proj_class_debug_dump.argtypes = [String, POINTER(AssimObj), String]
    proj_class_debug_dump.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 44
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_dump_live_objects'):
    proj_class_dump_live_objects = _libs['libassimilationclientlib.so'].proj_class_dump_live_objects
    proj_class_dump_live_objects.argtypes = []
    proj_class_dump_live_objects.restype = None

# /home/alanr/monitor/src/include/proj_classes.h: 45
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_live_object_count'):
    proj_class_live_object_count = _libs['libassimilationclientlib.so'].proj_class_live_object_count
    proj_class_live_object_count.argtypes = []
    proj_class_live_object_count.restype = guint32

# /home/alanr/monitor/src/include/proj_classes.h: 46
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_max_object_count'):
    proj_class_max_object_count = _libs['libassimilationclientlib.so'].proj_class_max_object_count
    proj_class_max_object_count.argtypes = []
    proj_class_max_object_count.restype = guint32

# /home/alanr/monitor/src/include/proj_classes.h: 47
if hasattr(_libs['libassimilationclientlib.so'], 'proj_class_finalize_sys'):
    proj_class_finalize_sys = _libs['libassimilationclientlib.so'].proj_class_finalize_sys
    proj_class_finalize_sys.argtypes = []
    proj_class_finalize_sys.restype = None

# /home/alanr/monitor/src/include/reliableudp.h: 43
class struct__ReliableUDP(Structure):
    pass

ReliableUDP = struct__ReliableUDP # /home/alanr/monitor/src/include/reliableudp.h: 39

struct__ReliableUDP.__slots__ = [
    'baseclass',
    '_protocol',
]
struct__ReliableUDP._fields_ = [
    ('baseclass', NetIOudp),
    ('_protocol', POINTER(FsProtocol)),
]

# /home/alanr/monitor/src/include/reliableudp.h: 47
if hasattr(_libs['libassimilationclientlib.so'], 'reliableudp_new'):
    reliableudp_new = _libs['libassimilationclientlib.so'].reliableudp_new
    reliableudp_new.argtypes = [gsize, POINTER(ConfigContext), POINTER(PacketDecoder), guint]
    reliableudp_new.restype = POINTER(ReliableUDP)

# /home/alanr/monitor/src/include/server_dump.h: 22
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'dump_cdp_packet'):
        continue
    dump_cdp_packet = _lib.dump_cdp_packet
    dump_cdp_packet.argtypes = [POINTER(None), POINTER(None)]
    dump_cdp_packet.restype = None
    break

# /home/alanr/monitor/src/include/server_dump.h: 23
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'dump_lldp_packet'):
        continue
    dump_lldp_packet = _lib.dump_lldp_packet
    dump_lldp_packet.argtypes = [POINTER(None), POINTER(None)]
    dump_lldp_packet.restype = None
    break

# /home/alanr/monitor/src/include/server_dump.h: 24
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'is_all_ascii'):
        continue
    is_all_ascii = _lib.is_all_ascii
    is_all_ascii.argtypes = [POINTER(None), POINTER(None)]
    is_all_ascii.restype = gboolean
    break

# /home/alanr/monitor/src/include/server_dump.h: 25
for _lib in _libs.itervalues():
    if not hasattr(_lib, 'dump_mem'):
        continue
    dump_mem = _lib.dump_mem
    dump_mem.argtypes = [POINTER(None), POINTER(None)]
    dump_mem.restype = None
    break

# /home/alanr/monitor/src/include/switchdiscovery.h: 34
class struct__SwitchDiscovery(Structure):
    pass

SwitchDiscovery = struct__SwitchDiscovery # /home/alanr/monitor/src/include/switchdiscovery.h: 32

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
    ('finalize', CFUNCTYPE(UNCHECKED(None), POINTER(AssimObj))),
    ('switchid', gpointer),
    ('switchidlen', gssize),
    ('portid', gpointer),
    ('portidlen', gssize),
]

# /home/alanr/monitor/src/include/switchdiscovery.h: 44
if hasattr(_libs['libassimilationclientlib.so'], 'switchdiscovery_new'):
    switchdiscovery_new = _libs['libassimilationclientlib.so'].switchdiscovery_new
    switchdiscovery_new.argtypes = [String, String, guint, gint, POINTER(GMainContext), POINTER(NetGSource), POINTER(ConfigContext), gsize]
    switchdiscovery_new.restype = POINTER(SwitchDiscovery)

# /home/alanr/monitor/src/include/tlvhelper.h: 27
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_get_guint8'):
    tlv_get_guint8 = _libs['libassimilationclientlib.so'].tlv_get_guint8
    tlv_get_guint8.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint8.restype = guint8

# /home/alanr/monitor/src/include/tlvhelper.h: 28
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_get_guint16'):
    tlv_get_guint16 = _libs['libassimilationclientlib.so'].tlv_get_guint16
    tlv_get_guint16.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint16.restype = guint16

# /home/alanr/monitor/src/include/tlvhelper.h: 29
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_get_guint24'):
    tlv_get_guint24 = _libs['libassimilationclientlib.so'].tlv_get_guint24
    tlv_get_guint24.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint24.restype = guint32

# /home/alanr/monitor/src/include/tlvhelper.h: 30
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_get_guint32'):
    tlv_get_guint32 = _libs['libassimilationclientlib.so'].tlv_get_guint32
    tlv_get_guint32.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint32.restype = guint32

# /home/alanr/monitor/src/include/tlvhelper.h: 31
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_get_guint64'):
    tlv_get_guint64 = _libs['libassimilationclientlib.so'].tlv_get_guint64
    tlv_get_guint64.argtypes = [POINTER(None), POINTER(None)]
    tlv_get_guint64.restype = guint64

# /home/alanr/monitor/src/include/tlvhelper.h: 32
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_set_guint8'):
    tlv_set_guint8 = _libs['libassimilationclientlib.so'].tlv_set_guint8
    tlv_set_guint8.argtypes = [POINTER(None), guint8, POINTER(None)]
    tlv_set_guint8.restype = None

# /home/alanr/monitor/src/include/tlvhelper.h: 33
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_set_guint16'):
    tlv_set_guint16 = _libs['libassimilationclientlib.so'].tlv_set_guint16
    tlv_set_guint16.argtypes = [POINTER(None), guint16, POINTER(None)]
    tlv_set_guint16.restype = None

# /home/alanr/monitor/src/include/tlvhelper.h: 34
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_set_guint24'):
    tlv_set_guint24 = _libs['libassimilationclientlib.so'].tlv_set_guint24
    tlv_set_guint24.argtypes = [POINTER(None), guint32, POINTER(None)]
    tlv_set_guint24.restype = None

# /home/alanr/monitor/src/include/tlvhelper.h: 35
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_set_guint32'):
    tlv_set_guint32 = _libs['libassimilationclientlib.so'].tlv_set_guint32
    tlv_set_guint32.argtypes = [POINTER(None), guint32, POINTER(None)]
    tlv_set_guint32.restype = None

# /home/alanr/monitor/src/include/tlvhelper.h: 36
if hasattr(_libs['libassimilationclientlib.so'], 'tlv_set_guint64'):
    tlv_set_guint64 = _libs['libassimilationclientlib.so'].tlv_set_guint64
    tlv_set_guint64.argtypes = [POINTER(None), guint64, POINTER(None)]
    tlv_set_guint64.restype = None

# /home/alanr/monitor/src/include/unknownframe.h: 34
class struct__UnknownFrame(Structure):
    pass

UnknownFrame = struct__UnknownFrame # /home/alanr/monitor/src/include/unknownframe.h: 28

struct__UnknownFrame.__slots__ = [
    'baseclass',
]
struct__UnknownFrame._fields_ = [
    ('baseclass', Frame),
]

# /home/alanr/monitor/src/include/unknownframe.h: 38
if hasattr(_libs['libassimilationclientlib.so'], 'unknownframe_new'):
    unknownframe_new = _libs['libassimilationclientlib.so'].unknownframe_new
    unknownframe_new.argtypes = [guint16]
    unknownframe_new.restype = POINTER(UnknownFrame)

# /home/alanr/monitor/src/include/unknownframe.h: 39
if hasattr(_libs['libassimilationclientlib.so'], 'unknownframe_tlvconstructor'):
    unknownframe_tlvconstructor = _libs['libassimilationclientlib.so'].unknownframe_tlvconstructor
    unknownframe_tlvconstructor.argtypes = [gconstpointer, gconstpointer]
    unknownframe_tlvconstructor.restype = POINTER(Frame)

# /home/alanr/monitor/src/include/address_family_numbers.h: 35
try:
    ADDR_FAMILY_IPV4 = 1
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 36
try:
    ADDR_FAMILY_IPV6 = 2
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 37
try:
    ADDR_FAMILY_NSAP = 3
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 38
try:
    ADDR_FAMILY_HDLC = 4
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 39
try:
    ADDR_FAMILY_BBN1822 = 5
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 40
try:
    ADDR_FAMILY_802 = 6
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 41
try:
    ADDR_FAMILY_E163 = 7
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 42
try:
    ADDR_FAMILY_E164 = 8
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 43
try:
    ADDR_FAMILY_F69 = 9
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 44
try:
    ADDR_FAMILY_X121 = 10
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 45
try:
    ADDR_FAMILY_IPX = 11
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 46
try:
    ADDR_FAMILY_APPLETALK = 12
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 47
try:
    ADDR_FAMILY_DECNET = 13
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 48
try:
    ADDR_FAMILY_BANYANVINES = 14
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 49
try:
    ADDR_FAMILY_E164_NSAP = 15
except:
    pass

# /home/alanr/monitor/src/include/address_family_numbers.h: 50
try:
    ADDR_FAMILY_DNS = 16
except:
    pass

# ../include/projectcommon.h: 13
def DIMOF(a):
    return (sizeof(a) / sizeof((a [0])))

# ../include/projectcommon.h: 14
def MALLOC0(nbytes):
    return (g_try_malloc0 (nbytes))

# ../include/projectcommon.h: 15
def MALLOC(nbytes):
    return (g_try_malloc (nbytes))

# ../include/projectcommon.h: 18
def FREE(m):
    return (g_free (m))

# ../include/projectcommon.h: 34
try:
    HAVE_PCAP_SET_RFMON = 1
except:
    pass

# /usr/include/glib-2.0/glib/gslist.h: 51
try:
    g_slist_free1 = g_slist_free_1
except:
    pass

# /usr/include/glib-2.0/glib/gslist.h: 107
def g_slist_next(slist):
    return slist and (slist.contents.next) or NULL

# ../include/projectcommon.h: 59
try:
    DISCOVERY_DIR = '/usr/share/assimilation/discovery_agents'
except:
    pass

# ../include/projectcommon.h: 60
try:
    CMAADDR = '224.0.2.5:1984'
except:
    pass

# ../include/projectcommon.h: 61
try:
    NANOLISTENADDR = '0.0.0.0:1984'
except:
    pass

# ../include/proj_classes.h: 72
def OBJ_IS_A(obj, Cclass):
    return (proj_class_is_a (obj, Cclass))

# ../include/frame.h: 58
try:
    FRAME_INITSIZE = 4
except:
    pass

# ../include/framesettypes.h: 32
try:
    FRAMESETTYPE_HEARTBEAT = 1
except:
    pass

# ../include/framesettypes.h: 33
try:
    FRAMESETTYPE_PING = 2
except:
    pass

# ../include/framesettypes.h: 34
try:
    FRAMESETTYPE_PONG = 3
except:
    pass

# ../include/framesettypes.h: 35
try:
    FRAMESETTYPE_ACK = 16
except:
    pass

# ../include/framesettypes.h: 36
try:
    FRAMESETTYPE_STARTUP = 18
except:
    pass

# ../include/framesettypes.h: 37
try:
    FRAMESETTYPE_HBDEAD = 19
except:
    pass

# ../include/framesettypes.h: 38
try:
    FRAMESETTYPE_HBSHUTDOWN = 20
except:
    pass

# ../include/framesettypes.h: 39
try:
    FRAMESETTYPE_HBLATE = 21
except:
    pass

# ../include/framesettypes.h: 40
try:
    FRAMESETTYPE_HBBACKALIVE = 22
except:
    pass

# ../include/framesettypes.h: 41
try:
    FRAMESETTYPE_HBMARTIAN = 23
except:
    pass

# ../include/framesettypes.h: 42
try:
    FRAMESETTYPE_PROBEALIVE = 24
except:
    pass

# ../include/framesettypes.h: 43
try:
    FRAMESETTYPE_SWDISCOVER = 25
except:
    pass

# ../include/framesettypes.h: 44
try:
    FRAMESETTYPE_JSDISCOVERY = 26
except:
    pass

# ../include/framesettypes.h: 45
try:
    FRAMESETTYPE_SENDHB = 64
except:
    pass

# ../include/framesettypes.h: 46
try:
    FRAMESETTYPE_EXPECTHB = 65
except:
    pass

# ../include/framesettypes.h: 47
try:
    FRAMESETTYPE_SENDEXPECTHB = 66
except:
    pass

# ../include/framesettypes.h: 48
try:
    FRAMESETTYPE_STOPSENDHB = 67
except:
    pass

# ../include/framesettypes.h: 49
try:
    FRAMESETTYPE_STOPEXPECTHB = 68
except:
    pass

# ../include/framesettypes.h: 50
try:
    FRAMESETTYPE_STOPSENDEXPECTHB = 69
except:
    pass

# ../include/framesettypes.h: 51
try:
    FRAMESETTYPE_SETCONFIG = 70
except:
    pass

# ../include/framesettypes.h: 52
try:
    FRAMESETTYPE_INCRDEBUG = 71
except:
    pass

# ../include/framesettypes.h: 53
try:
    FRAMESETTYPE_DECRDEBUG = 72
except:
    pass

# ../include/framesettypes.h: 54
try:
    FRAMESETTYPE_DODISCOVER = 73
except:
    pass

# ../include/framesettypes.h: 55
try:
    FRAMESETTYPE_STOPDISCOVER = 74
except:
    pass

# ../include/frameset.h: 54
try:
    FRAMESET_INITSIZE = 6
except:
    pass

# ../include/configcontext.h: 96
try:
    CONFIG_DEFAULT_DEADTIME = 30
except:
    pass

# ../include/configcontext.h: 97
try:
    CONFIG_DEFAULT_HBTIME = 3
except:
    pass

# ../include/configcontext.h: 98
try:
    CONFIG_DEFAULT_WARNTIME = 10
except:
    pass

# ../include/configcontext.h: 99
try:
    CONFIG_DEFAULT_HBPORT = 1984
except:
    pass

# ../include/configcontext.h: 100
try:
    CONFIG_DEFAULT_CMAPORT = 1984
except:
    pass

# ../include/configcontext.h: 102
try:
    CONFIG_DEFAULT_ADDRTYPE = ADDR_FAMILY_IPV4
except:
    pass

# ../include/configcontext.h: 103
try:
    CONFIG_DEFAULT_SIGNFRAME_TYPE = G_CHECKSUM_SHA256
except:
    pass

# ../include/configcontext.h: 105
try:
    CONFIGNAME_DEADTIME = 'deadtime'
except:
    pass

# ../include/configcontext.h: 106
try:
    CONFIGNAME_WARNTIME = 'warntime'
except:
    pass

# ../include/configcontext.h: 107
try:
    CONFIGNAME_HBTIME = 'hbtime'
except:
    pass

# ../include/configcontext.h: 108
try:
    CONFIGNAME_HBPORT = 'hbport'
except:
    pass

# ../include/configcontext.h: 109
try:
    CONFIGNAME_CMAPORT = 'cmaport'
except:
    pass

# ../include/configcontext.h: 110
try:
    CONFIGNAME_CMAINIT = 'cmainit'
except:
    pass

# ../include/configcontext.h: 112
try:
    CONFIGNAME_CMAADDR = 'cmaaddr'
except:
    pass

# ../include/configcontext.h: 113
try:
    CONFIGNAME_CMADISCOVER = 'cmadisc'
except:
    pass

# ../include/configcontext.h: 114
try:
    CONFIGNAME_CMAFAIL = 'cmafail'
except:
    pass

# ../include/configcontext.h: 115
try:
    CONFIGNAME_OUTSIG = 'outsig'
except:
    pass

# ../include/configcontext.h: 116
try:
    CONFIGNAME_CRYPT = 'crypt'
except:
    pass

# ../include/configcontext.h: 117
try:
    CONFIGNAME_COMPRESS = 'compress'
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 33
try:
    CDP_TLV_DEVID = 1
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 35
try:
    CDP_TLV_ADDRESS = 2
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 36
try:
    CDP_TLV_PORTID = 3
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 38
try:
    CDP_TLV_CAPS = 4
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 39
try:
    CDP_TLV_VERS = 5
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 40
try:
    CDP_TLV_PLATFORM = 6
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 41
try:
    CDP_TLV_IPPREFIX = 7
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 42
try:
    CDP_TLV_HELLO = 8
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 43
try:
    CDP_TLV_VTPDOMAIN = 9
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 44
try:
    CDP_TLV_NATIVEVLAN = 10
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 45
try:
    CDP_TLV_DUPLEX = 11
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 46
try:
    CDP_TLV_APPLID = 14
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 47
try:
    CDP_TLV_POWER = 16
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 59
try:
    CDP_CAPMASK_ROUTER = 1
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 60
try:
    CDP_CAPMASK_TBBRIDGE = 2
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 61
try:
    CDP_CAPMASK_SPBRIDGE = 4
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 62
try:
    CDP_CAPMASK_SWITCH = 8
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 63
try:
    CDP_CAPMASK_HOST = 16
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 64
try:
    CDP_CAPMASK_IGMPFILTER = 32
except:
    pass

# /home/alanr/monitor/src/include/cdp.h: 65
try:
    CDP_CAPMASK_REPEATER = 64
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 62
try:
    FRAMETYPE_END = 0
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 80
try:
    FRAMETYPE_SIG = 1
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 96
try:
    FRAMETYPE_CRYPT = 2
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 114
try:
    FRAMETYPE_COMPRESS = 3
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 130
try:
    FRAMETYPE_REQID = 4
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 144
try:
    FRAMETYPE_PKTDATA = 6
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 159
try:
    FRAMETYPE_WALLCLOCK = 7
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 172
try:
    FRAMETYPE_INTERFACE = 8
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 184
try:
    FRAMETYPE_HOSTNAME = 9
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 197
try:
    FRAMETYPE_IPADDR = 10
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 210
try:
    FRAMETYPE_MACADDR = 11
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 223
try:
    FRAMETYPE_PORTNUM = 12
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 235
try:
    FRAMETYPE_IPPORT = 13
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 248
try:
    FRAMETYPE_HBINTERVAL = 14
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 261
try:
    FRAMETYPE_HBDEADTIME = 15
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 274
try:
    FRAMETYPE_HBWARNTIME = 16
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 286
try:
    FRAMETYPE_PATHNAME = 17
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 299
try:
    FRAMETYPE_NVPAIR = 18
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 311
try:
    FRAMETYPE_JSDISCOVER = 19
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 322
try:
    FRAMETYPE_PARAMNAME = 20
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 333
try:
    FRAMETYPE_CSTRINGVAL = 21
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 345
try:
    FRAMETYPE_CINTVAL = 22
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 359
try:
    FRAMETYPE_ELAPSEDTIME = 23
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 371
try:
    FRAMETYPE_DISCNAME = 24
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 384
try:
    FRAMETYPE_DISCINTERVAL = 25
except:
    pass

# /home/alanr/monitor/src/include/frametypes.h: 397
try:
    FRAMETYPE_DISCJSON = 26
except:
    pass

# ../include/fsqueue.h: 78
try:
    DEFAULT_FSQMAX = 0
except:
    pass

# /home/alanr/monitor/src/include/fsprotocol.h: 91
try:
    DEFAULT_FSP_QID = 0
except:
    pass

# /home/alanr/monitor/src/include/fsprotocol.h: 92
try:
    FSPROTO_WINDOWSIZE = 7
except:
    pass

# /home/alanr/monitor/src/include/fsprotocol.h: 93
try:
    FSPROTO_REXMITINTERVAL = 2000000
except:
    pass

# /home/alanr/monitor/src/include/hblistener.h: 66
try:
    DEFAULT_DEADTIME = 60
except:
    pass

# /home/alanr/monitor/src/include/hbsender.h: 49
try:
    DEFAULT_DEADTIME = 60
except:
    pass

# /home/alanr/monitor/src/include/jsondiscovery.h: 32
try:
    JSONAGENTROOT = DISCOVERY_DIR
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 35
try:
    LLDP_INVAL = 65535
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 42
try:
    LLDP_TLV_END = 0
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 43
try:
    LLDP_TLV_CHID = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 44
try:
    LLDP_TLV_PID = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 45
try:
    LLDP_TLV_TTL = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 46
try:
    LLDP_TLV_PORT_DESCR = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 47
try:
    LLDP_TLV_SYS_NAME = 5
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 48
try:
    LLDP_TLV_SYS_DESCR = 6
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 49
try:
    LLDP_TLV_SYS_CAPS = 7
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 50
try:
    LLDP_TLV_MGMT_ADDR = 8
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 51
try:
    LLDP_TLV_ORG_SPECIFIC = 127
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 59
try:
    LLDP_CHIDTYPE_COMPONENT = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 61
try:
    LLDP_CHIDTYPE_ALIAS = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 62
try:
    LLDP_CHIDTYPE_PORT = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 64
try:
    LLDP_CHIDTYPE_MACADDR = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 65
try:
    LLDP_CHIDTYPE_NETADDR = 5
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 66
try:
    LLDP_CHIDTYPE_IFNAME = 6
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 67
try:
    LLDP_CHIDTYPE_LOCAL = 7
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 75
try:
    LLDP_PIDTYPE_ALIAS = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 76
try:
    LLDP_PIDTYPE_COMPONENT = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 78
try:
    LLDP_PIDTYPE_MACADDR = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 79
try:
    LLDP_PIDTYPE_NETADDR = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 80
try:
    LLDP_PIDTYPE_IFNAME = 5
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 81
try:
    LLDP_PIDTYPE_CIRCUITID = 6
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 82
try:
    LLDP_PIDTYPE_LOCAL = 7
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 89
try:
    LLDP_CAPMASK_REPEATER = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 90
try:
    LLDP_CAPMASK_BRIDGE = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 91
try:
    LLDP_CAPMASK_WLAN_AP = 8
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 92
try:
    LLDP_CAPMASK_ROUTER = 16
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 93
try:
    LLDP_CAPMASK_PHONE = 32
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 94
try:
    LLDP_CAPMASK_DOCSIS = 64
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 95
try:
    LLDP_CAPMASK_STATION = 128
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 103
try:
    LLDP_ORG802_1_VLAN_PVID = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 104
try:
    LLDP_ORG802_1_VLAN_PORTPROTO = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 105
try:
    LLDP_ORG802_1_VLAN_NAME = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 106
try:
    LLDP_ORG802_1_VLAN_PROTOID = 4
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 114
try:
    LLDP_ORG802_3_PHY_CONFIG = 1
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 115
try:
    LLDP_ORG802_3_POWERVIAMDI = 2
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 116
try:
    LLDP_ORG802_3_LINKAGG = 3
except:
    pass

# /home/alanr/monitor/src/include/lldp.h: 117
try:
    LLDP_ORG802_3_MTU = 4
except:
    pass

# ../include/pcap_min.h: 40
try:
    ENABLE_LLDP = 1
except:
    pass

# ../include/pcap_min.h: 42
try:
    ENABLE_CDP = 2
except:
    pass

# /home/alanr/monitor/src/include/pcap_min.h: 40
try:
    ENABLE_LLDP = 1
except:
    pass

# /home/alanr/monitor/src/include/pcap_min.h: 42
try:
    ENABLE_CDP = 2
except:
    pass

# /home/alanr/monitor/src/include/proj_classes.h: 72
def OBJ_IS_A(obj, Cclass):
    return (proj_class_is_a (obj, Cclass))

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 32
try:
    TLV_DTYPE_BINARY = 1
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 33
try:
    TLV_DTYPE_UINT8 = 2
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 34
try:
    TLV_DTYPE_UINT16 = 3
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 35
try:
    TLV_DTYPE_UINT32 = 4
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 36
try:
    TLV_DTYPE_UINT64 = 5
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 37
try:
    TLV_DTYPE_OUI = 6
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 38
try:
    TLV_DTYPE_MACADDR = 7
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 39
try:
    TLV_DTYPE_IPV4ADDR = 8
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 40
try:
    TLV_DTYPE_IPV6ADDR = 9
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 41
try:
    TLV_DTYPE_GENADDR = 10
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 42
try:
    TLV_DTYPE_LLCHASSIS = 11
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 43
try:
    TLV_DTYPE_LLPORTID = 12
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 44
try:
    TLV_DTYPE_LLCAPS = 13
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 45
try:
    TLV_DTYPE_LLMGMTADDR = 14
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 46
try:
    TLV_DTYPE_LL8021_VLANID = 15
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 47
try:
    TLV_DTYPE_LL8021_PPVLANID = 16
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 48
try:
    TLV_DTYPE_LL8021_VLANNAME = 17
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 49
try:
    TLV_DTYPE_LL8021_PROTOID = 18
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 50
try:
    TLV_DTYPE_LL8023_MACPHY = 19
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 51
try:
    TLV_DTYPE_LL8023_POWER = 20
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 52
try:
    TLV_DTYPE_LL8023_LINKAGGR = 21
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 53
try:
    TLV_DTYPE_LL8023_MTU = 22
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 54
try:
    TLV_DTYPE_FSTYPE = 23
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 55
try:
    TLV_DTYPE_FSFLAGS = 24
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 56
try:
    TLV_DTYPE_FRAMETYPE = 25
except:
    pass

# /home/alanr/monitor/src/include/tlv_valuetypes.h: 57
try:
    TLV_DTYPE_FR_REQTYPE = 26
except:
    pass

_GSList = struct__GSList # /usr/include/glib-2.0/glib/gslist.h: 40

_AssimObj = struct__AssimObj # ../include/assimobj.h: 49

_FrameSet = struct__FrameSet # ../include/frameset.h: 43

_Frame = struct__Frame # ../include/frame.h: 42

_NetAddr = struct__NetAddr # ../include/netaddr.h: 43

_AddrFrame = struct__AddrFrame # /home/alanr/monitor/src/include/addrframe.h: 38

_SignFrame = struct__SignFrame # ../include/signframe.h: 40

_SeqnoFrame = struct__SeqnoFrame # ../include/seqnoframe.h: 42

_ConfigContext = struct__ConfigContext # ../include/configcontext.h: 70

_ConfigValue = struct__ConfigValue # ../include/configcontext.h: 57

_Listener = struct__Listener # ../include/listener.h: 41

_FrameTypeToFrame = struct__FrameTypeToFrame # ../include/packetdecoder.h: 37

_PacketDecoder = struct__PacketDecoder # ../include/packetdecoder.h: 44

_NetIO = struct__NetIO # ../include/netio.h: 44

_NetGSource = struct__NetGSource # ../include/netgsource.h: 43

_AuthListener = struct__AuthListener # /home/alanr/monitor/src/include/authlistener.h: 41

_ObeyFrameSetTypeMap = struct__ObeyFrameSetTypeMap # /home/alanr/monitor/src/include/authlistener.h: 50

_CompressFrame = struct__CompressFrame # /home/alanr/monitor/src/include/compressframe.h: 33

_CryptFrame = struct__CryptFrame # /home/alanr/monitor/src/include/cryptframe.h: 33

_CstringFrame = struct__CstringFrame # /home/alanr/monitor/src/include/cstringframe.h: 35

_Discovery = struct__Discovery # /home/alanr/monitor/src/include/discovery.h: 47

_FsQueue = struct__FsQueue # ../include/fsqueue.h: 45

_FsProtocol = struct__FsProtocol # /home/alanr/monitor/src/include/fsprotocol.h: 70

_FsProtoElem = struct__FsProtoElem # /home/alanr/monitor/src/include/fsprotocol.h: 51

_FsProtoElemSearchKey = struct__FsProtoElemSearchKey # /home/alanr/monitor/src/include/fsprotocol.h: 62

_HbListener = struct__HbListener # /home/alanr/monitor/src/include/hblistener.h: 44

_HbSender = struct__HbSender # /home/alanr/monitor/src/include/hbsender.h: 39

_IntFrame = struct__IntFrame # /home/alanr/monitor/src/include/intframe.h: 39

_IpPortFrame = struct__IpPortFrame # /home/alanr/monitor/src/include/ipportframe.h: 40

_JsonDiscovery = struct__JsonDiscovery # /home/alanr/monitor/src/include/jsondiscovery.h: 36

_NanoHbStats = struct__NanoHbStats # /home/alanr/monitor/src/include/nanoprobe.h: 32

_NetIOudp = struct__NetIOudp # /home/alanr/monitor/src/include/netioudp.h: 39

_NVpairFrame = struct__NVpairFrame # /home/alanr/monitor/src/include/nvpairframe.h: 33

_GSource_pcap = struct__GSource_pcap # /home/alanr/monitor/src/include/pcap_GSource.h: 38

_ReliableUDP = struct__ReliableUDP # /home/alanr/monitor/src/include/reliableudp.h: 43

_SwitchDiscovery = struct__SwitchDiscovery # /home/alanr/monitor/src/include/switchdiscovery.h: 34

_UnknownFrame = struct__UnknownFrame # /home/alanr/monitor/src/include/unknownframe.h: 34

# No inserted files

