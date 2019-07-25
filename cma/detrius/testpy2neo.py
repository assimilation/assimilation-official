#
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012 - Alan Robertson <alanr@unix.sh>
#
#  The Assimilation software is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  The Assimilation software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
from __future__ import print_function

import re

# Import Neo4j modules
from py2neo import neo4j, cypher

# Attach to the graph db instance
graph_db = neo4j.GraphDatabaseService("http://localhost:7474/db/data/")

print("Version of Neo4J:", graph_db.neo4j_version)

# List of node types along with True if we create a corresponding index
nodetypes = {
    "Ring": True,
    "Drone": True,
    "Switch": True,
    "NIC": False,
    "IPaddr": True,
    "MACaddr": True,
}


indices = [key for key in nodetypes.keys() if nodetypes[key]]

indextbl = {}
nodetypetbl = {}

for index in indices:
    print("Creating index %s" % index)
    indextbl[index] = graph_db.get_or_create_index(neo4j.Node, index)
print("Creating index %s" % "nodetype")
indextbl["nodetype"] = graph_db.get_or_create_index(neo4j.Node, "nodetype")

nodetypeindex = indextbl["nodetype"]
Ringindex = indextbl["Ring"]
for index in nodetypes.keys():
    topnode = nodetypeindex.get_or_create(
        "nodetype", index, {"name": "#%sType" % index, "nodetype": "nodetype"}
    )
    nodetypetbl[index] = topnode


def node_new(nodetype, nodename, properties={}):
    """Possibly creates a new node, puts it in its appropriate index and creates an IS_A relationship
    with the nodetype object corresponding its nodetype.
    It is created and added to indexes if it doesn't already exist in its corresponding index - if there is one.
    If it already exists, the pre-existing node is returned.
    If this object type doesn't have an index, it will always be created.
    Note that the nodetype has to be in the nodetypetable - even if its NULL (for error detection).
    The IS_A relationship may be useful -- or not.  Hard to say at this point..."""
    properties["nodetype"] = nodetype
    properties["name"] = nodename
    if indextbl.has_key(nodetype):
        idx = indextbl[nodetype]
        obj = idx.get_or_create(nodetype, nodename, properties)
        # for pname in properties.keys():
        #    obj[pname] = properties[pname]
    else:
        obj = graph_db.create(properties)
        nt = nodetypetable[nodetype]
        if nt is not None:
            graph_db.relate((obj, "IS_A", nt))
    return obj


TheOneRing = node_new("Ring", "TheOneRing")
servidor = node_new("Drone", "servidor")


# Build a Cypher query
query = "START a=node({A}) MATCH a-[r:IS_A]->b RETURN a, r, b"

# Define two row handlers...
def print_row(row):
    a, rel, b = row
    bname = b["name"][1:]
    if bname.endswith("Type"):
        bname = bname[0 : len(bname) - 4]
    print(a["name"] + " " + str(rel.type) + " " + bname + " [nodetype: %s]" % a["nodetype"])


# ...and execute the query
cypher.execute(graph_db, query, {"A": TheOneRing.id}, row_handler=print_row)
cypher.execute(graph_db, query, {"A": servidor.id}, row_handler=print_row)
# 	Indexes:
# 	ringindex - index of all Ring objects [nodetype=ring]
# 	droneindex - index of all Drone objects [nodetype=drone]
# 	ipindex - index of all IP address objects [nodetype=ipaddr]
# 	macindex - index of all interfaces by MAC address [nodetype=nic]

# 	Node types [nodetype enumeration values]:
# 	ring	- heartbeat ring objects
# 	drone	- systems running our nanoprobes
# 	nic	- interfaces on drones
# 	ipaddr	- IP addresses (ipv4 or ipv6)

# 	Relationship types [reltype enumeration values]
#       ------------------------------------------
# 	reltype		fromnodetype	tonodetype
# 	--------	------------	----------
# 	nichost		nic		drone
# 	ipowner		ipaddr		nic
# 	ringnext	drone		drone
# 	ringmember	ring		ipaddr
