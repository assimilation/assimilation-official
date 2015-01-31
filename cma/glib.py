#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2014 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community - http://assimproj.org
# Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
'''
This file provides wrapper functions for some glib mainloop-related classes that we need to know about.
It is somewhat compatible with the GObject introspection libraries for the same code.
The advantage we have is that we don't need that code which can be complicated to get in a particular
environment - since it involved both Python code and C code.
This is easy for us to do since we are using ctypes and ctypesgen anyway.
'''

from AssimCtypes import \
    G_IO_IN, G_IO_PRI, G_IO_ERR, G_IO_OUT, G_IO_HUP,    \
    g_main_loop_new, g_main_loop_run, g_main_loop_quit, g_main_context_default, \
    g_io_channel_unix_new, assim_set_io_watch, g_source_remove, g_timeout_add,  \
    guint, gboolean, GIOChannel, GIOCondition, GIOFunc, GSourceFunc, UNCHECKED
from ctypes import py_object, POINTER, CFUNCTYPE

IO_IN   =   G_IO_IN
IO_PRI  =   G_IO_PRI
IO_ERR  =   G_IO_ERR
IO_OUT  =   G_IO_OUT
IO_HUP  =   G_IO_HUP


class MainLoop(object):
    '''
    This class encapsulates the glib mainloop paradigm.
    '''
    def __init__(self):
        'Create a default mainloop object'
        self.mainloop = g_main_loop_new(g_main_context_default(), True)

    def run(self):
        'Run this mainloop until quit is called on it'
        g_main_loop_run(self.mainloop)
        pass

    def quit(self):
        'Stop this mainloop - causing run() call to return'
        g_main_loop_quit(self.mainloop)
        pass

# Ctypes gets these wrong...
# For our purposes the last argument needs to be py_object instead of gpointer
GIOFunc = CFUNCTYPE(UNCHECKED(gboolean), POINTER(GIOChannel), guint, py_object)
GSourceFunc = CFUNCTYPE(UNCHECKED(gboolean), py_object)
assim_set_io_watch.argtypes = [guint, GIOCondition, GIOFunc, py_object]
g_timeout_add.argtypes      = [guint, GSourceFunc,  py_object]

def io_add_watch(fileno, conditions, callback, otherobj=None):
    '''
    fileno is the UNIX file descriptor
    Conditions is a bitwise-OR of at least one of {IO_IN, IO_PRI, IO_ERR, IO_OUT, IO_HUP}
    The callback function receives three parameters:
            source
            calledcondition
            otherobj (as passed to io_add_watch)
        and returns a bool - True if we should keep watching this file descriptor, False if not.

    Return: int (source id of our watch condition - suitable to passing to source_remove)
    '''
    cb = GIOFunc(callback)
    obj = py_object(otherobj)
    return (assim_set_io_watch(fileno, conditions, cb, obj), cb, obj)

def source_remove(sourceid):
    '''
    We remove a source - from io_add_watch() above
    '''
    g_source_remove(sourceid[0])

def timeout_add(interval, callback, otherobj):
    '''
    Call a callback function at the (repeating) interval given
    '''
    cb = GSourceFunc(callback)
    obj = py_object(otherobj)
    return (g_timeout_add(interval, cb, obj), cb, obj)
