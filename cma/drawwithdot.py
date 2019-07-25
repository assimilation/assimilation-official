#!/usr/bin/env python
#
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=80
#
# This file is part of the Assimilation Project.
#
# Author: Alan Robertson <alanr@unix.sh>
# Copyright (C) 2016 - Assimilation Systems Limited
#
# Free support is available from the Assimilation Project community
#   - http://assimproj.org
# Paid support is available from Assimilation Systems Limited
#   - http://assimilationsystems.com
#
# The Assimilation software is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Assimilation software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with the Assimilation Project software.
# If not, see http://www.gnu.org/licenses/
#
"""

Drawwithdot: Sample program to draw Assimilation graphs using Dot
             from the 'graphviz' software.

The core part of this program is pretty simple.
The complicated part is getting the 'dot' diagram to look pretty
This is accomplished by fancy format strings.

When we format nodes, the following variables are available:
    id: An idname suitable for matching up in relationship (see below)
    If the GraphNode supports __getitem__ (mainly Drones) then any
        item that __getitem__ might return
    Any attributes of the GraphNode

We only format nodes when we have a format string for its nodetype

When we format relationships, the following variables are available:
    from: the idname of the from node in the relationship
    to: the idname of the to node in the relationship
    type: the relationship type
    Any other attributes of the relationship

    In other words, this relationship looks like this in Cypher notation:
        from-[:type]->to

    We only output relationships when we've formatted (selected) both the
    from and the to node in the relationship, AND we have a format
    string for that relationship type.


This is a very flexible and powerful graph drawing method, for which
the code is simple and common - and the formats are more complicated.
"""

from __future__ import print_function  # , unicode_literals
import sys, os, optparse
import inject
import assimcli
from cmainit import CMAInjectables
from store import Store
from AssimCclasses import pyConfigContext, pyNetAddr
from AssimCtypes import VERSION_STRING, LONG_LICENSE_STRING, SHORT_LICENSE_STRING

# pylint complaint: too few public methods. It's OK - it's a utility class ;-)
# pylint: disable=R0903
class DictObj(object):
    """This is a class that allows us to see the objects below us as a
    dict-like object - both for any dict-like characteristics and for its
    attributes.  This is for formatting them with the "usual" Python
    formatting rules like for example, "%(ipaddr)s".
    """

    def __init__(self, obj, kw=None, failreturn=""):
        """Initialization"""
        self.obj = obj
        self.failreturn = failreturn
        if kw is None:
            kw = {}
        self.kw = kw

    @staticmethod
    def _strip_itemname(name):
        "Strip the out and return itemname out of the format name"
        return name if name.find(":") < 0 else name.split(":")[1]

    @staticmethod
    def _labelstring(name):
        "Strip the out and return label out of the format"
        if name.find(":") < 0:
            return ""
        label = name.split(":")[0]
        if len(label) == 0:
            return r"\n"
        return r"\n" + label + ": "

    @staticmethod
    def _fixup(value):
        "Fix up our values for printing neatly in minimal space"
        if isinstance(value, unicode):
            if value.startswith("::"):
                try:
                    ip = pyNetAddr(value)
                    value = repr(ip)
                except ValueError:
                    pass
            return str(value).strip()
        elif isinstance(value, str):
            return value
        elif hasattr(value, "__iter__"):
            ret = "["
            prefix = ""
            for item in value:
                ret += "%s%s" % (prefix, str(item).strip())
                prefix = ", "
            ret += "]"
            return ret
        return str(value)

    def __contains__(self, name):
        "Return True if we can find the given attribute/index"
        name = DictObj._strip_itemname(name)
        try:
            if name in self.kw or name in self.obj:
                return True
        except TypeError:
            pass
        return hasattr(self.obj, name)

    def __getitem__(self, name):
        try:
            ret = self._getitem(self._strip_itemname(name))
            if ret is None or str(ret) == "":
                raise ValueError
            ret = str(ret)
            ret = ret.strip() if isinstance(ret, (str, unicode)) else ret
            return self._labelstring(name) + DictObj._fixup(ret)
        except ValueError:
            return self._failreturn(name)

    def _getitem(self, name):
        "Return the given attribute or item from our object"
        if name in self.kw:
            return self.kw[name](self.obj, name) if callable(self.kw[name]) else self.kw[name]
        try:
            # print("Looking for %s in %s." % (name, type(self.obj)),
            #   file=sys.stderr)
            ret = self.obj.deepget(name) if hasattr(self.obj, "deepget") else self.obj[name]
            if ret is not None:
                return ret
        except (IndexError, KeyError, TypeError):
            pass
        try:
            if not hasattr(self.obj, name):
                # print("Name %s not found in %s." % (name, type(self.obj)),
                #    file=sys.stderr)
                if name.find(".") > 0:
                    prefix, suffix = name.split(".", 1)
                    base = getattr(self.obj, prefix)
                    subobj = pyConfigContext(base)
                    return subobj.deepget(suffix)
            # print("Returning getattr( %s, %s." % (type(self.obj), name),
            #    file=sys.stderr)
            return getattr(self.obj, name)
        except AttributeError:
            pass
        raise ValueError(name)

    def _failreturn(self, name):
        """Return a failure"""
        if callable(self.failreturn):
            return self.failreturn(self.obj, name)
        return self.failreturn


class FancyDictObj(DictObj):
    """A fancy DictObj that knows how to get some aggregate data
    for use as pseudo-attributes of the objects we know and love ;-)

    """

    os_namemap = {
        "description": "Description",
        "distro": "Distributor ID",
        "distributor": "Distributor ID",
        "release": "Release",
        "codename": "Codename",
    }

    @staticmethod
    def osinfo(obj, name):
        """Provide aliases for various OS attributes for formatting
        These will only work on a Drone node"""
        if name.startswith("os-"):
            name = name[3:]
        try:
            print("OBJ %s" % str(obj))
            print("OBJ.os: %s" % str(obj["os"]))
            print("OBJ.os.data: %s" % str(obj["os"]["data"]))
            if name in FancyDictObj.os_namemap:
                return obj["os"]["data"][FancyDictObj.os_namemap[name]]
        except (KeyError, IndexError, TypeError):
            return "(unknown)"

    @staticmethod
    def proc_name(obj, _name):
        "Construct a reasonable looking string to display for a process name."
        retname = os.path.basename(obj["pathname"])
        if retname.endswith("java"):
            retname += r"\n%s" % obj["argv"][-1]
        elif len(obj["argv"]) > 1:
            if not obj["argv"][1].startswith("-"):
                retname += " %s" % obj["argv"][1]
        return retname

    @staticmethod
    def drone_attrs(obj, _name):
        "Construct a string to set the attributes for Drone nodes."
        secscore = (
            obj.bp_category_security_score if hasattr(obj, "bp_category_security_score") else 0
        )
        init = ""
        if obj["status"] != "up":
            if obj["reason"] == "HBSHUTDOWN":
                init = 'style="filled,dashed" fillcolor=gray90 '
            else:
                init = 'style="filled,dashed" fillcolor=hotpink1 fontname=bold '
        if secscore < 1:
            return init + "color=green penwidth=3 "
        elif secscore <= 10:
            return init + "color=yellow penwidth=4 "
        if secscore <= 20:
            return init + "color=orange penwidth=4 "
        return init + "color=red penwidth=10"

    @staticmethod
    def service_attrs(obj, _name):
        "Construct a reasonable looking string to set the service options."
        ret = " color=blue"
        if "server" in obj["roles"] and not obj["is_monitored"]:
            ret += " style=dashed penwidth=2"
        if obj["uid"] == "root" or obj["gid"] == "root":
            ret += " fontcolor=red"
        if "server" in obj["roles"]:
            ret += " shape=folder"
        else:
            ret += " shape=rectangle"
        return ret

    @staticmethod
    def monitor_attrs(obj, _name):
        "Construct a reasonable looking string to set monitor options."
        if obj["monitorclass"] == "NEVERMON" or not obj["isactive"]:
            return "style=filled fillcolor=gray90"
        if not obj["isworking"]:
            return "color=red penwidth=5 style=filled fillcolor=hotpink"
        return ""

    @staticmethod
    def nic_attrs(obj, _name):
        "Construct a reasonable looking string to set NIC options."
        ret = "shape=octagon color=navy "
        if "carrier" in obj and not obj["carrier"]:
            ret += "style=dotted penwidth=2 "
        return ret

    def __init__(self, obj, kw=None, failreturn=""):
        DictObj.__init__(self, obj, kw, failreturn)
        for key in self.os_namemap:
            self.kw["os-" + key] = FancyDictObj.osinfo
        for key in (
            "nodename",
            "operating-system",
            "machine",
            "distributor" "codename",
            "distro",
            "processor",
            "hardware-platform",
            "kernel-name",
            "kernel-release",
            "kernel-version",
        ):
            self.kw["os-" + key] = FancyDictObj.osinfo
        self.kw["proc-name"] = FancyDictObj.proc_name
        self.kw["drone-attrs"] = FancyDictObj.drone_attrs
        self.kw["service-attrs"] = FancyDictObj.service_attrs
        self.kw["monitor-attrs"] = FancyDictObj.monitor_attrs
        self.kw["nic-attrs"] = FancyDictObj.nic_attrs


class DotGraph(object):
    """Class to format Assimilation graphs as 'dot' graphs"""

    # pylint - too many arguments. It's a bit flexible...
    # pylint: disable=R0913
    @inject.params(store=Store)
    def __init__(
        self,
        formatdict,
        store=None,
        dronelist=None,
        dictclass=FancyDictObj,
        options=None,
        executor_context=None,
    ):
        """Initialization
        Here are the main two things to understand:
            formatdict is a dict-like object which provides a format string
            for each kind of relationship and node.

            These format strings are then interpolated with the values
            from the relationship or node as filtered by @dictclass objects.
            The @dictclass object must behave like a dict. When format items
            are requested by a format in the formatdict, the dictclass object
            is expected to provide those values.
        params:
            @formatdict - dictionary providing format strings for
                          nodes and relationships
            @dburl - URL for opening the database
            @dronelist - a possibly-None list of drones to start from
            @dictclass - a dict-like class which can take a node or
                    relationship as a parameter for its constructor
                    along with extra keywords as the kw parameter.
        """
        self.formatdict = formatdict
        self.store = store
        self.nodeids = None
        self.dictclass = dictclass
        self.options = options
        self.executor_context = executor_context
        if isinstance(dronelist, (str, unicode)):
            self.dronelist = [dronelist]
        else:
            self.dronelist = dronelist

    @staticmethod
    def idname(nodeid):
        "Format a node id so dot will like it (not numeric)"
        return "node_%d" % nodeid

    def _outnodes(self, nodes):
        """Yield the requested nodes, formatted for 'dot'
        """
        self.nodeids = set()
        # print('NODES: %s' % nodes)
        nodeformats = self.formatdict["nodes"]
        for node in nodes:
            nodetype = node["nodetype"]
            if nodetype not in nodeformats:
                continue
            nodeid = node["_node_id"]
            self.nodeids.add(nodeid)
            dictobj = self.dictclass(node, kw={"id": DotGraph.idname(nodeid)})
            # print('Nodetype: %s' % node.nodetype, file=sys.stderr)
            # print('nodeformats: %s' % nodeformats[node.nodetype],
            #       file=sys.stderr)
            yield nodeformats[nodetype] % dictobj

    def _outrels(self, relationships):
        """Yield relationships, formatted for 'dot'
        """
        relformats = self.formatdict["relationships"]
        for rel in relationships:
            reltype = rel["type"]
            if (
                rel["end_node"] not in self.nodeids
                or rel["start_node"] not in self.nodeids
                or reltype not in relformats
            ):
                continue
            dictobj = self.dictclass(
                rel,
                kw={
                    "from": DotGraph.idname(rel["start_node"]),
                    "to": DotGraph.idname(rel["end_node"]),
                },
            )
            yield relformats[reltype] % dictobj

    def render_options(self):
        "Render overall graph options as a dot-formatted string"
        ret = ""
        if not self.options:
            return ""
        for option in self.options:
            optvalue = self.options[option]
            if isinstance(optvalue, (str, unicode, bool, int, float, long)):
                ret += ' %s="%s"' % (str(option), str(optvalue))
                continue
            if hasattr(optvalue, "__iter__"):
                listval = ""
                delim = ""
                for elem in optvalue:
                    listval += "%s%s" % (delim, elem)
                    delim = ","
                ret += ' %s="%s"' % (str(option), str(listval))
        return ret

    def __iter__(self):
        """Yield 'dot' strings for our nodes and relationships"""
        queryobj = None
        yield "Digraph G {%s\n" % self.render_options()
        nodetypes = self.formatdict["nodes"].keys()
        reltypes = self.formatdict["relationships"].keys()
        if self.dronelist is None:
            params = {"nodetypes": nodetypes, "reltypes": reltypes}
            queryname = "allhostsubgraph"
        else:
            queryname = "hostsubgraph"
            params = {"nodetypes": nodetypes, "reltypes": reltypes, "hostname": self.dronelist}
        print("NODETYPES: %s " % str(nodetypes), file=sys.stderr)
        print("RELTYPES: %s " % str(reltypes), file=sys.stderr)
        print("RELTYPES: %s " % str(reltypes), file=sys.stderr)
        print("QUERYNAME: %s " % str(queryname), file=sys.stderr)
        querymeta = assimcli.query.load_query_object(self.store, queryname)
        print("QUERYMETA: %s " % str(querymeta), file=sys.stderr)
        queryiter = querymeta.execute(
            self.executor_context, expandjson=True, elemsonly=True, **params
        )
        # Subgraph queries produce a single row, with two elements:
        #   nodes and relationships
        for jsonline in queryiter:
            queryobj = pyConfigContext(jsonline)
            break

        for line in self._outnodes(queryobj["nodes"]):
            yield line.strip() + "\n"
        for line in self._outrels(queryobj["relationships"]):
            yield line.strip() + "\n"
        yield "}\n"

    def out(self, outfile=sys.stdout):
        """Output nodes and relationships to the 'outfile'."""
        outfile.writelines(self.__iter__())

    def __str__(self):
        """Output nodes and relationships in a string."""
        ret = ""
        for line in self.__iter__():
            ret += "%s\n" % line
        return ret


ip_format = r"""%(id)s [shape=box color=blue label="%(ipaddr)s%(:hostname)s"]"""

drone_format = (
    r"""%(id)s [shape=house %(drone-attrs)s label="""
    + """"%(designation)s"""
    + """%(:os-description)s %(os-codename)s%(:os-kernel-release)"""
    + """s%(Security Risk:bp_category_security_score)s"""
    + """%(Status:status)s%(Reason:reason)s%(:roles)s"]"""
)

switch_format = (
    r"""%(id)s [shape=box color=black penwidth=3 """
    + r"""label="%(designation)s%(Name:SystemName)s%(:SystemDescription)s"""
    + r"""%(Manufacturer:manufacturer)s%(Model:model)s%(Roles:roles)s"""
    + r"""%(Address:ManagementAddress)s%(HW Vers:hardware-revision)s"""
    + r"""%(FW Vers:firmware-revision)s%(SW Vers:software-revision)s"""
    + r"""%(serial:serial-number)s%(Asset:asset-id)s"]"""
)

MAC_format = (
    r"""%(id)s [%(nic-attrs)s """
    + r"""label="%(macaddr)s%(NIC:ifname)s%(:PortDescription)s"""
    + r"""%(:OUI)s%(MTU:json.mtu)s%(Duplex:json.duplex)s%(carrier:carrier)s"]"""
)
processnode_format = (
    r"""%(id)s [%(service-attrs)s label="%(proc-name)s"""
    + r"""%(uid:uid)s%(gid:gid)s%(pwd:cwd)s"]"""
)
iptcpportnode_format = (
    r"""%(id)s [shape=rectangle fontsize=10 """ + """label="%(ipaddr)s%(:port)s"]"""
)
monitoraction_format = (
    r"""%(id)s [%(monitor-attrs)s shape=component """
    + r"""label="%(monitorclass)s%(:monitortype)s"]"""
)

default_relfmt = r"""%(from)s->%(to)s [label=%(type)s]"""
ipowner_format = r"""%(from)s->%(to)s [color=hotpink label=ipowner]"""
nicowner_format = r"""%(from)s->%(to)s [color=black label=nicowner]"""
wiredto_format = (
    r"""%(from)s->%(to)s [color=blue label=wiredto """ + """penwidth=3 arrowhead=none]"""
)

#
#   This defines all our various 'skins'
#   A skin defines how we tell dot to draw nodes and relationships
#   in a given diagram.
#
skin_formats = {
    "default": {  # The default drawing 'skin'
        "nodes": {
            "IPaddrNode": ip_format,
            "NICNode": MAC_format,
            "Drone": drone_format,
            "SystemNode": switch_format,
            "ProcessNode": processnode_format,
            "IPtcpportNode": iptcpportnode_format,
            "MonitorAction": monitoraction_format,
        },
        "relationships": {
            "baseip": default_relfmt,
            "hosting": default_relfmt,
            "ipowner": ipowner_format,
            "monitoring": default_relfmt,
            "nicowner": nicowner_format,
            "tcpservice": default_relfmt,
            "tcpclient": default_relfmt,
            "wiredto": wiredto_format,
            "RingNext_The_One_Ring": default_relfmt,
        },
    }
}

#
# A drawing type is a collection of nodes, relationships that we want to
# make sure show up in the drawing
#
# Eventually this should probably include queries that produce the
# particular desired nodes that go with this particular diagram.
#
drawing_types = {
    "everything": {
        "description": "everything and the kitchen sink",
        "nodes": skin_formats["default"]["nodes"].keys(),
        "relationships": skin_formats["default"]["relationships"].keys(),
    },
    "network": {
        "description": "network diagram",
        "nodes": ["IPaddrNode", "NICNode", "Drone", "SystemNode"],
        "relationships": ["ipowner", "nicowner", "wiredto"],
    },
    "service": {
        "description": "attack surface (services) diagram",
        "nodes": ["Drone", "ProcessNode", "IPtcpportNode"],
        "relationships": ["ipowner", "baseip", "hosting", "tcpservice", "tcpclient"],
    },
    "monitoring": {
        "description": "monitoring diagram",
        "nodes": ["Drone", "MonitorAction", "ProcessNode"],
        "relationships": ["monitoring", "hosting", "tcpservice"],
    },
    "monring": {
        "description": "neighbor monitoring ring diagram",
        "nodes": ["Drone"],
        "relationships": ["RingNext_The_One_Ring"],
    },
}


def validate_drawing_types(dtypes=None, skins=None):
    """We make sure that all the drawing types we have available
    are well-defined in each of the skins...
    This is really just for debugging, but it's quick enough to do
    each time...
    """
    if dtypes is None:
        dtypes = drawing_types
    if skins is None:
        skins = skin_formats
    for skin in skins:
        nodetypes = skins[skin]["nodes"]
        reltypes = skins[skin]["relationships"]
        for dtype in dtypes:
            dnodes = dtypes[dtype]["nodes"]
            for nodetype in dnodes:
                if nodetype not in nodetypes:
                    raise ValueError("Nodetype %s not in skin %s" % (nodetype, skin))
            drels = dtypes[dtype]["relationships"]
            for reltype in drels:
                if reltype not in reltypes:
                    raise ValueError("Relationship type %s not in skin %s" % (reltype, skin))


def construct_dot_formats(drawingtype="network", skintype="default"):
    """Construct 'dot' formats from our skins and this drawing type"""
    diagram = drawing_types[drawingtype]
    skin = skin_formats[skintype]
    result = {"nodes": {}, "relationships": {}}
    for nodetype in diagram["nodes"]:
        result["nodes"][nodetype] = skin["nodes"][nodetype]
    for reltype in diagram["relationships"]:
        result["relationships"][reltype] = skin["relationships"][reltype]
    return result


def drawing_type_help():
    "Create help string for the --drawingtype option"
    ret = "Type of drawing to create. Must be one of "
    delim = "("
    for dtype in drawing_types.keys():
        ret += "%s%s" % (delim, dtype)
        delim = ", "
    ret += "). "
    for dtype in drawing_types.keys():
        ret += '"%s": %s. ' % (dtype, drawing_types[dtype]["description"])
    return ret


if __name__ == "__main__":
    CMAInjectables.default_cma_injection_configuration()
    validate_drawing_types()
    desc = "Create illustration from Assimilation graph database"
    desc += ".\nLicensed under the %s" % LONG_LICENSE_STRING
    usage = "usage: drawwithdot [options] "
    delimiter = "("
    for drawing_type in sorted(drawing_types.keys()):
        usage += "%s%s" % (delimiter, drawing_type)
        delimiter = "|"
    usage += ")"

    opts = optparse.OptionParser(
        description=desc,
        usage=usage,
        version=VERSION_STRING + " (License: %s)" % SHORT_LICENSE_STRING,
    )
    opts.add_option(
        "-d",
        "--drawingtype",
        action="store",
        dest="drawingtype",
        type="choice",
        choices=drawing_types.keys(),
        help=drawing_type_help(),
    )
    opts.set_defaults(drawingtype="everything")
    opts.add_option(
        "-D", "--dpi", action="store", dest="dpi", type="int", help="Dots-per-inch for drawing"
    )
    opts.add_option(
        "-s",
        "--size",
        action="store",
        dest="size",
        type="int",
        nargs=2,
        help="(x,y) dimensions of drawing in inches",
    )
    # opts.set_defaults('size', (30,8))
    cmdoptions, args = opts.parse_args()
    cmdoptions.skin = "default"
    if len(args) == 1:
        if args[0] not in drawing_types:
            print('ERROR: "%s" is not a known illustration type.' % args[0], file=sys.stderr)
            print("Known illustration types: %s" % str(drawing_types.keys()))
            exit(1)
        cmdoptions.drawingtype = args[0]
    elif len(args) > 1:
        print("ERROR: Only one illustration type allowed.", file=sys.stderr)
        exit(1)

    # Process all the overall command line options...
    graphoptions = {}
    for attr in ("size", "dpi"):
        graphoptions[attr] = getattr(cmdoptions, attr)

    dot = DotGraph(
        construct_dot_formats(cmdoptions.drawingtype, skintype=cmdoptions.skin),
        options=graphoptions,
    )
    dot.out()
