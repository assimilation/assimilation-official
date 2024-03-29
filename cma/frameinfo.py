#!/usr/bin/env python
"""
A collection of classes which provide constants for FrameTypes and FrameSetTypes
"""

import re

# from AssimCclasses import pyFrame, pyAddrFrame, pySignFrame, pySeqnoFrame, \
# 	pyIntFrame, pyCstringFrame, pyNVpairFrame, pyIpPortFrame

# pylint: disable=R0903


class pyFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class pyAddrFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class pySignFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class pySeqnoFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class pyIntFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class pyCstringFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class GpyNVpairFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class pyIpPortFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class pyCryptFrame(object):
    """Placeholder bootstrapping class"""

    def __init__(self):
        pass


class pyCompressFrame(object):
    """Placeholder class"""

    def __init__(self):
        pass


class pyCryptCurve25519(pyCryptFrame):
    """Placeholder class"""

    def __init__(self):
        pyCryptFrame.__init__(self)


class FrameTypes(object):
    """Class defining the universe of FrameSets - including code to generate a C header file"""
    fileheader = """
/**
 * @file
 * @brief Header file defining the data layouts for our Frames.
 * THIS FILE MECHANICALLY GENERATED by "%s".  DO NOT EDIT.
 *
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2011, 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 *  The Assimilation software is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  The Assimilation software is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
 */
/**
@addtogroup FrameFormats
@{
  Below is the set of frame formats and corresponding macro definitions
  This section will document the format of the individual frame types.
  The first frame in a frameset must be a signature frame.
  If an encryption frame is present, it must be the  frame in the frameset.
  If a compression frame is present, it must occur after the encryption frame
  if present, or after the signature frame, if there is no encryption frame.

  The final frame in a frameset must be an End frame (which will be
  added automatically by the @ref FrameSet marshalling classes).
@}
*/
/**
@defgroup IndividualFrameFormats Individual TLV 'Frame' data types and layouts (by TLV type)
@{
Below is the set of individual frame types and data layouts - organized by TLV type.
Note that a given @ref Frame subclass can appear be associated with many different TLV types.
This file organizes this data by the TLV type, not by the underlying @ref Frame subclass.
@ingroup FrameFormats
@ingroup DefineEnums
@{
*/
"""
    asciiart = {
        "pyFrame": """
+----------------+-----------+------------------+
| frametype = %2d | f_length  |    frame data    |
|   (16 bits)    | (24-bits) | (f_length bytes) |
+----------------+-----------+------------------+
""",
        "pySignFrame": """
+----------------+-----------+-----------------+------------+-------------------+
|                |           |      major      |            |                   |
| frametype = %2d | f_length  | signature-type  | minor type | digital signature |
|   (16 bits)    | (24-bits) |      (8 bits)   |  (8 bits)  |(f_length-2 bytes) |
+----------------+-----------+-----------------+------------+-------------------+
""",
        "pyCompressFrame": """
+----------------+-----------+------------------------+
| frametype = %2d | f_length  | compressed frames      |
|   (16 bits)    | (24-bits) |    (f_length bytes)    |
+----------------+-----------+------------------------+
""",
        "pySeqnoFrame": """
+----------------+---------------+-------------+-----------+
| frametype = %2d | f_length = 8  |  reply id   | queue id  |
|   (16 bits)    |   (24-bits)   |  (8 bytes)  | (2 bytes) |
+----------------+---------------+-------------+-----------+
""",
        "pyIntFrame": """
+----------------+--------------+-------------------------+
| frametype = %2d | f_length =   |     integer  value      |
|                | 1,2,3,4 or 8 |           value         |
|   (16 bits)    |   (24-bits)  |   (1,2,3,4,or 8 bytes)  |
+----------------+--------------+-------------------------+
""",
        "pyCstringFrame": """
+----------------+----------------+----------------+--------+
| frametype = %2d | f_length = 'n' | interface name |  0x00  |
|   (16 bits)    |    (24-bits)   |   (n-1 bytes)  | 1 byte |
+----------------+----------------+----------------+--------+
""",
        "pyAddrFrame": """
+----------------+----------------+---------------+--------------+
| frametype = %2d | f_length = n   | Address Type  |  address     |
|   (16 bits)    |    (24-bits)   |    2 bytes    | (n-2 bytes)  |
+----------------+----------------+---------------+--------------+
""",
        "pyIpPortFrame": """
+----------------+----------------+-------------+--------------+---------------+
| frametype = %2d | f_length = n   | Port Number | Address Type  |  address     |
|   (16 bits)    |    (24-bits)   |   2 bytes   |    2 bytes    | (n-4 bytes)  |
+----------------+----------------+-------------+--------------+---------------+
""",
        "pyNVpairFrame": """
+----------------+---------------+--------+-----------------+-------+------+
| frametype = %2d | f_length = n  | nm_len |  name    | NUL  |       | NUL  |
|   (16 bits)    |    (24-bits)  | 1 byte | nm_len-1 | byte | value | byte |
|                |               |(8 bits)|  bytes   |      |       |      |
+----------------+---------------+--------+-----------------+-------+------+
""",
        "pyCryptCurve25519":
        # pylint: disable=C0301
        """
+----------------+---------------+---------+----------+----------+----------+-----------------------+---------------------+------------+
|                |               | sender  |  sender  | receiver | receiver |                       |                     |            |
| frametype = %2d | f_length = n  | key_id  |  key id  | key name |  key id  | crypto_box_NONCEBYTES | crypto_box_MACBYTES | cyphertext |
|   (16 bits)    |    (24-bits)  | length  |          |  length  |          | (randomeness - nonce) |  MAC for cyphertext |     --     |
|                |               |         |("length" |          |("length" |                       |                     | originally |
|                |               | (1 byte)|  bytes)  | (1 byte) |  bytes)  |                       |                     | many frames|
+----------------+---------------+---------+----------+----------+----------+-----------------------+---------------------+------------+
                                 |<---------------------------- length() value in memory -------------------------------->|
                                 |<------------------------------- TLV length on the wire -------------------------------------------->|
For the sender:   the sender key is private, and the receiver key is public
For the receiver: the sender key is public,  and the receiver key is private
""",
    }
    intframetypes = {
        0: (
            pyFrame,
            "END",
            "Final frame in a message",
            """The last frame in a frameset is required to be an End frame.
End frames are of type zero and <b>always</b> have length zero.
Its corresponding class is @ref Frame.
This is the most basic Frame type, and is the only frame type that permits a length of zero.
""",
        ),
        1: (
            pySignFrame,
            "SIG",
            "Digital signature frame",
            """The signature frame is mandatory and must be the first
frame in the frameset - and must have frametype <b>1</b>.
The digital signature computed in the digital signature field is computed
on all the bytes in the frameset beginning with the first byte after
the end of this frame, extending through and including the last byte of the frameset.
Note that this will include the encryption frame if present.
The format and length of the digital signature depends on the type of signature.
""",
        ),
        2: (
            pyCryptCurve25519,
            "CRYPTCURVE25519",
            "@ref CryptCurve25519 Encryption frame",
            """If an encryption frame is present it must be the second
frame in the frameset, and can only be preceded by a @ref FRAMETYPE_SIG frame.
When this frame is present, then all the frames following
are encrypted according information in the encryption information value segment.
""",
        ),
        3: (
            pyCompressFrame,
            "COMPRESS",
            "Compression frame",
            """If a compression frame is present (<b>frametype = 3</b>) it must be the second
or third frame in the frameset, and can only be preceded by a @ref FRAMETYPE_SIG
and encryption frames.
When this frame is present, then all the frames following
are compreseed according information in the compression information value segment.
The format of the compression information value segment will likely be a
single integer saying which compression method was used.
""",
        ),
        4: (
            pySeqnoFrame,
            "REQID",
            "Request ID - a message sequence number.",
            """Requests from the central authority are identified by a request id
(basically a sequence number) and a queue id.  The combination of the two
is unique over a relatively long period of time - at least days.
Notifications from clients are sent with queue id 0, which will never be
used by the central authority.
""",
        ),
        6: (
            pyFrame,
            "PKTDATA",
            "Encapsulated packet data",
            """This frame format is normally used for a CDP or LLDP packet.
The data is kept exactly as it was received from the
network interface via libpcap.
""",
        ),
        7: (
            pyIntFrame,
            "WALLCLOCK",
            "64-bit local time",
            """This frame provides local time on the sending system as gotten from the
g_get_real_time() call - which is a 64-bit time measured in microseconds.
In spite of the apparent variability permitted above, it is an 8-byte (64-bit) integer.
""",
        ),
        8: (
            pyCstringFrame,
            "INTERFACE",
            "Name of network interface as a C-style string",
            """This frame provides the name of a network interface as a
NUL-terminated C-style string.
""",
        ),
        9: (
            pyCstringFrame,
            "HOSTNAME",
            "Name of host as a C-style string",
            """This frame provides the name of a host as a NUL-terminated C-style string.
""",
        ),
        10: (
            pyAddrFrame,
            "IPADDR",
            "IP address in either IPv4 or IPv6 format.",
            """IPv4 addresses are address type 1 and are 4 bytes long.
IPv6 addresses are address type 2 and are 16 bytes long,
and have Address types 1 and 2 respectively.
""",
        ),
        11: (
            pyAddrFrame,
            "MACADDR",
            "MAC Address.",
            """This frame can be either a 6 byte (EUI-48) or an 8 byte (EUI-64) format MAC address.
The Address Type for a MAC address is 6.
""",
        ),
        12: (
            pyIntFrame,
            "PORTNUM",
            "Port number.",
            """This frame is a 16-bit IP port number.
""",
        ),
        13: (
            pyIpPortFrame,
            "IPPORT",
            "IP w/Port.",
            """This frame is a 16-bit IP port number along with an IPv4 or IPv6 address.
""",
        ),
        14: (
            pyIntFrame,
            "HBINTERVAL",
            "Heartbeat interval.",
            """This frame is a heartbeat sending interval measured in seconds.
""",
        ),
        15: (
            pyIntFrame,
            "HBDEADTIME",
            "Heartbeat deadtime.",
            """This frame is a heartbeat deadtime measured in seconds.
""",
        ),
        16: (
            pyIntFrame,
            "HBWARNTIME",
            "Heartbeat warntime.",
            """This frame is a heartbeat warning time measured in seconds.
""",
        ),
        17: (
            pyCstringFrame,
            "PATHNAME",
            "file name",
            """This frame contains a pathname for a file as a C string.
""",
        ),
        19: (
            pyCstringFrame,
            "JSDISCOVER",
            "JSON-formatted discovery data",
            """This frame contains JSON-formatted output from a discovery process.
The type of discovery data and program collecting it are inside.
""",
        ),
        20: (
            pyCstringFrame,
            "CONFIGJSON",
            "JSON configuration data from CMA",
            "This frame provides JSON for initial configuration JSON as a NUL-terminated C-style "
            "string.",
        ),
        21: (
            pyCstringFrame,
            "CSTRINGVAL",
            "Generic string value",
            "Miscellaneous NUL-terminated C-style string.",
        ),
        22: (pyIntFrame, "CINTVAL", "Generic integer value", "Miscellaneous integer value."),
        23: (
            pyIntFrame,
            "ELAPSEDTIME",
            "64-bit elapsed time (usec)",
            """This frame provides elapsed time (measured locally) in microseconds.
In spite of the apparent variability permitted, it is an 8-byte (64-bit) integer.
""",
        ),
        24: (
            pyCstringFrame,
            "DISCNAME",
            "name of this discovery action",
            """This frame is a name to give this instance of a discovery action.
""",
        ),
        25: (
            pyIntFrame,
            "DISCINTERVAL",
            "Discovery interval",
            """This frame is a discovery repeat interval measured in seconds as an @ref IntFrame.
""",
        ),
        26: (
            pyCstringFrame,
            "DISCJSON",
            "Discovery JSON string",
            """This frame provides the data describing the discovery action in detail.
   It must be preceded by a FRAMETYPE_DISCNAME.
""",
        ),
        27: (
            pyCstringFrame,
            "RSCJSON",
            "JSON resource string",
            """This frame provides data describing the a resource or cancel operation in detail.
""",
        ),
        28: (
            pyCstringFrame,
            "RSCJSONREPLY",
            "JSON operation result",
            """This frame provides the data describing the result of a resource action in detail.
""",
        ),
        29: (
            pyCstringFrame,
            "KEYID",
            "Key ID",
            """This frame provides the name of a Key ID as a C-style string.
""",
        ),
        30: (
            pyFrame,
            "PUBKEYCURVE25519",
            "A Curve25519 Public Key",
            """This frame provides the raw bytes of a Curve25519 Public Key.
It is always <b>crypto_box_PUBLICKEYBYTES</b> bytes long - no more, no less.
""",
        ),
    }
    strframetypes = dict()
    for i in intframetypes.keys():
        data = intframetypes[i]
        key = data[1]
        strframetypes[key] = (i, data[0], key, data[1], data[2])

    def __init__(self):
        pass

    @staticmethod
    def get(key):
        """Return the tuple that corresponds to this key (integer or string)"""
        if isinstance(key, (str, bytes)):
            return FrameTypes.strframetypes[str(key)]
        else:
            if int(key) in FrameTypes.intframetypes:
                return FrameTypes.intframetypes[int(key)]
            return None, str(key), str(key), str(key)

    @classmethod
    def c_defines(cls, f):
        """Generate C #defines from our data"""
        intframetypes = FrameTypes.intframetypes.keys()
        f.write(FrameTypes.fileheader % __file__)
        # Create pretty ASCII art pictures and #defines of all our different packet formats
        for i in sorted(intframetypes):
            ourtuple = FrameTypes.intframetypes[i]
            pyclass = ourtuple[0].__name__
            frametype = i
            framename = ourtuple[1]
            # framedesc = ourtuple[1]
            frametext = ourtuple[3]
            Cclassname = re.sub("^py", "", pyclass)
            f.write(
                "/**\n FRAMETYPE_%s Frame (<b>frametype %d</b>)"
                " Frame subclass - @ref %s\n" % (framename, frametype, Cclassname)
            )
            f.write("<PRE>%s</PRE>\n%s\n */\n" % ((FrameTypes.asciiart[pyclass] % i), frametext))
            f.write(
                "#define FRAMETYPE_%s\t%d\t///< %s: @ref %s\n"
                % (ourtuple[1], i, ourtuple[2], Cclassname)
            )
        f.write("///@}\n")
        f.write("///@}\n")

        # Create the frame type map - mapping frame types to function names in the 'C' code.
        f.write("#define	FRAMETYPEMAP	{\t\t\t\t\t\\\n")
        for i in intframetypes:
            tup = FrameTypes.intframetypes[i]
            clsname = tup[0].__name__
            Cclassname = re.sub("^py", "", clsname) + "_tlvconstructor"
            Cfuncname = Cclassname.lower()
            f.write("        {FRAMETYPE_%s,\t/*%d*/ %s},	\\\n" % (tup[1], i, Cfuncname))
        f.write("}\n")


# Create conventional class.DEFINENAME attributes
for s in FrameTypes.strframetypes.keys():
    setattr(FrameTypes, s, FrameTypes.strframetypes[s][0])


class FrameSetTypes(object):
    """Class defining the universe of FrameSets - including code to generate a C header file"""
    _fileheader = """#ifndef _FRAMESETTYPES_H
#define _FRAMESETTYPES_H
/**
 * @file
 * @brief Header file defining all known FrameSet types
 * THIS FILE MECHANICALLY GENERATED by "%s".  DO NOT EDIT.
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2011, 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 *  The Assimilation software is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  The Assimilation software is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
 */

/**
 * @defgroup FrameSetTypes FrameSet Types
 *
 * @{
 * @ingroup DefineEnums
 */
"""
    strframetypes = {
        # nanoprobe peer-peer FrameSets
        "HEARTBEAT": (1, "A heartbeat packet"),
        "PING": (2, "Are you alive? (can also come from the CMA)"),
        "PONG": (3, "I am alive (can also go to the CMA)"),
        "STARTUP": (4, "Nanoprobe originating packet is starting up."),
        # nanoprobe FrameSets sent to collective management authority
        "ACK": (16, "Frame referred to has been acted on. (can also come from the CMA)"),
        "CONNSHUT": (17, "Shutting down this connection (can also come from CMA)"),
        "CONNNAK": (18, "Ignoring your connection start request (can also come from CMA)"),
        "HBDEAD": (26, "System named in packet appears to be dead."),
        "HBSHUTDOWN": (27, "System originating packet has shut down."),
        "HBLATE": (28, "System named in packet sent a late heartbeat."),
        "HBBACKALIVE": (29, "System named in packet sent heartbeat after being marked dead."),
        "HBMARTIAN": (30, "System named in packet appears gave unexpected heartbeat."),
        "SWDISCOVER": (31, "Packet encapsulates switch discovery packet"),
        "JSDISCOVERY": (32, "Packet contains JSON-formatted discovery data"),
        "RSCOPREPLY": (33, "Packet contains return result from a resource operation"),
        "SEQPING": (34, "Are you alive? (can come from anyone)"),
        "SEQPONG": (35, "I am alive (can go to anyone)"),
        # 'Privileged' FrameSets sent from the CMA to nanoprobes
        "SENDHB": (64, "Send Heartbeats to these addresses"),
        "EXPECTHB": (65, "Expect (listen for) Heartbeats from these addresses"),
        "SENDEXPECTHB": (66, "Send Heartbeats to these addresses, and expect them as well."),
        "STOPSENDHB": (67, "Stop sending Heartbeats to these addresses"),
        "STOPEXPECTHB": (68, "Stop expecting (listening for) Heartbeats from these addresses"),
        "STOPSENDEXPECTHB": (
            69,
            "Stop sending Heartbeats to these addresses" ", and stop expecting them as well.",
        ),
        "SETCONFIG": (70, "Initial configuration packet"),
        "INCRDEBUG": (71, "Increment debug for some or all classes"),
        "DECRDEBUG": (72, "Increment debug for some or all classes"),
        "DODISCOVER": (73, "Perform (repeating) JSON discovery action"),
        "STOPDISCOVER": (74, "Stop a repeating JSON discovery action"),
        "DORSCOP": (75, "Do a (possibly-repeating) JSON resource action"),
        "STOPRSCOP": (76, "Stop a (possibly-repeating) JSON resource action"),
        "ACKSTARTUP": (77, "Acknowledge full response to STARTUP packet"),
        "RUNSCRIPT": (78, "Run an arbitrary script (not yet implemented)"),
    }
    intframetypes = dict()
    for s in strframetypes.keys():
        i = strframetypes[s][0]
        intframetypes[i] = (s, strframetypes[s][1])

    def __init__(self):
        pass

    @staticmethod
    def get(key):
        """Return the tuple that corresponds to this key (integer or string)"""
        if isinstance(key, (str, bytes)):
            return FrameSetTypes.strframetypes[str(key)]
        else:
            if key in FrameSetTypes.intframetypes:
                return FrameSetTypes.intframetypes[int(key)]
            return None, str(int(key)), str(int(key)), str(int(key))

    @classmethod
    def c_defines(cls, f):
        """Print out the C #defines that go with this set of definitions"""
        f.write(FrameSetTypes._fileheader % __file__)
        l = FrameSetTypes.intframetypes.keys()
        for i in sorted(l):
            ourtuple = FrameSetTypes.intframetypes[i]
            f.write("#define FRAMESETTYPE_%s\t%d\t///< %s\n" % (ourtuple[0], i, ourtuple[1]))
        f.write("///@}\n")
        # Don't currently want this map - probably not needed (or even a good idea...)
        # f.write('\n#define	FRAMESETTYPEMAP	{\t\t\t\t\t\t\\\n')
        # for i in l:
        # tup = FrameSetTypes.intframetypes[i]
        # Cobjname = "frameset_listener_" + tup[0].lower()
        # f.write('        {FRAMESETTYPE_%s,\t/*%d*/ %s},	\\\n' % (tup[0], i, Cobjname))
        # f.write('}\n')

        f.write(
            "#define MIN_SEQFRAMESET\tFRAMESETTYPE_ACK\t///<"
            " First frameset type with a sequence number\n"
        )
        f.write("#endif /* _FRAMESETTYPES_H */\n")


# Create conventional class.DEFINENAME attributes
for s in FrameSetTypes.strframetypes.keys():
    setattr(FrameSetTypes, s, FrameSetTypes.strframetypes[s][0])


if __name__ == "__main__":
    # pylint: disable=C0413
    import sys

    if len(sys.argv) != 3 or (sys.argv[1] != "frametypes" and sys.argv[1] != "framesettypes"):
        sys.stderr.write(
            "Usage: python %s (frametypes|framesettypes) output-filename\n" % sys.argv[0]
        )
        raise SystemExit(1)
    fvar = open(sys.argv[2], "w")
    if sys.argv[1] == "frametypes":
        FrameTypes.c_defines(fvar)
        sys.exit(0)
    elif sys.argv[1] == "framesettypes":
        FrameSetTypes.c_defines(fvar)
        sys.exit(0)
    raise SystemExit(1)
