# pylint: disable=C0302
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
# C0302: too many lines in module
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
# pylint: disable=C0302,W0212
"""
A collection of classes which wrap our @ref C-Classes and provide Pythonic interfaces
to these C-classes.
"""
from __future__ import print_function, absolute_import
from typing import Optional, List, Union, Tuple
import six
import collections
import traceback
import types
from sys import stderr
import gc
import pickle
import ctypes
import AssimCtypes
from AssimCtypes import (
    POINTER,
    String,
    cast,
    addressof,
    pointer,
    string_at,
    create_string_buffer,
    c_char_p,
    byref,
    memmove,
    c_uint,
    g_free,
    GSList,
    GDestroyNotify,
    g_slist_length,
    g_slist_next,
    struct__Frame,
    struct__FrameSet,
    struct__GSList,
    struct__NetIO,
    struct__ReliableUDP,
    g_slist_free,
    MALLOC,
    FRAMETYPE_SIG,
    Frame,
    AssimObj,
    NetAddr,
    SeqnoFrame,
    frame_new,
    addrframe_new,
    nvpairframe_new,
    frameset_new,
    frameset_append_frame,
    frameset_prepend_frame,
    seqnoframe_new,
    cstringframe_new,
    unknownframe_new,
    ipportframe_netaddr_new,
    ipportframe_ipv4_new,
    ipportframe_ipv6_new,
    frameset_construct_packet,
    frameset_get_flags,
    frameset_set_flags,
    frameset_clear_flags,
    frameset_dump,
    frameset_sender_key_id,
    frameset_sender_identity,
    LLDP_TLV_END,
    LLDP_TLV_CHID,
    LLDP_TLV_PID,
    LLDP_TLV_TTL,
    LLDP_TLV_PORT_DESCR,
    LLDP_TLV_SYS_NAME,
    LLDP_TLV_SYS_DESCR,
    LLDP_TLV_SYS_CAPS,
    LLDP_TLV_MGMT_ADDR,
    LLDP_TLV_ORG_SPECIFIC,
    LLDP_ORG802_1_VLAN_PVID,
    LLDP_ORG802_1_VLAN_PORTPROTO,
    LLDP_ORG802_1_VLAN_NAME,
    LLDP_ORG802_1_VLAN_PROTOID,
    LLDP_ORG802_3_PHY_CONFIG,
    LLDP_ORG802_3_POWERVIAMDI,
    LLDP_ORG802_3_LINKAGG,
    LLDP_ORG802_3_MTU,
    LLDP_PIDTYPE_ALIAS,
    LLDP_PIDTYPE_IFNAME,
    LLDP_PIDTYPE_LOCAL,
    LLDP_CHIDTYPE_ALIAS,
    LLDP_CHIDTYPE_IFNAME,
    LLDP_CHIDTYPE_LOCAL,
    LLDP_CHIDTYPE_MACADDR,
    LLDP_CHIDTYPE_COMPONENT,
    LLDP_CHIDTYPE_NETADDR,
    CDP_TLV_DEVID,
    CDP_TLV_ADDRESS,
    CDP_TLV_PORTID,
    CDP_TLV_CAPS,
    CDP_TLV_VERS,
    CDP_TLV_POWER,
    CDP_TLV_PLATFORM,
    CDP_TLV_MTU,
    CDP_TLV_SYSTEM_NAME,
    CDP_TLV_MANAGEMENT_ADDR,
    CDP_TLV_DUPLEX,
    CDP_TLV_LOCATION,
    CDP_TLV_EXT_PORTID,
    CDP_TLV_NATIVEVLAN,
    CDP_TLV_VLREPLY,
    CDP_TLV_VLQUERY,
    CDP_TLV_VTPDOMAIN,
    CDP_TLV_TRUST_BITMAP,
    CDP_TLV_UNTRUSTED_COS,
    CDP_TLV_HELLO,
    CMAADDR,
    ADDR_FAMILY_IPV4,
    ADDR_FAMILY_IPV6,
    ADDR_FAMILY_802,
    is_valid_lldp_packet,
    is_valid_cdp_packet,
    netaddr_ipv4_new,
    netaddr_ipv6_new,
    netaddr_dns_new,
    netaddr_mac48_new,
    netaddr_mac64_new,
    proj_class_classname,
    assimobj_new,
    intframe_new,
    signframe_glib_new,
    packetdecoder_new,
    configcontext_new,
    configcontext_new_JSON_string,
    netio_new,
    netioudp_new,
    reliableudp_new,
    netio_is_dual_ipv4v6_stack,
    create_setconfig,
    create_sendexpecthb,
    get_lldptlv_type,
    get_lldptlv_len,
    get_lldptlv_body,
    get_lldptlv_first,
    get_lldptlv_next,
    get_cdptlv_type,
    get_cdptlv_len,
    get_cdptlv_body,
    get_cdptlv_first,
    get_cdptlv_next,
    pcap_capture_iter_new,
    pcap_capture_iter_del,
    pcap_capture_iter_next,
    tlv_get_guint8,
    tlv_get_guint16,
    tlv_get_guint24,
    tlv_get_guint32,
    tlv_get_guint64,
    CFG_EEXIST,
    CFG_CFGCTX,
    CFG_STRING,
    CFG_NETADDR,
    CFG_FRAME,
    CFG_INT64,
    CFG_ARRAY,
    CFG_FLOAT,
    CFG_BOOL,
    DEFAULT_FSP_QID,
    CFG_NULL,
    CMA_IDENTITY_NAME,
    COMPRESS_ZLIB,
    FRAMETYPE_COMPRESS,
    compressframe_new_string,
    cryptframe_associate_identity,
    cryptframe_set_dest_key_id,
    cryptframe_whois_key_id,
    cryptframe_get_dest_key_id,
    cryptframe_new_by_destaddr,
    cryptframe_get_key_ids,
    cryptframe_set_signing_key_id,
    cryptframe_private_key_by_id,
    cryptcurve25519_set_encryption_method,
    cryptcurve25519_cache_all_keypairs,
    CMA_KEY_PREFIX,
    curve25519_key_id_to_filename,
    cryptcurve25519_gen_persistent_keypair,
    cryptcurve25519_new,
    FRAMETYPE_CRYPTCURVE25519,
    proj_class_live_object_count,
    proj_class_dump_live_objects,
)
from consts import CMAconsts
from frameinfo import FrameTypes, FrameSetTypes

Frame_p = POINTER(struct__Frame)
FrameSet_p = POINTER(struct__FrameSet)
NetIO_p = POINTER(struct__NetIO)
ReliableUDP_p = POINTER(struct__ReliableUDP)


def u_string_at(s: bytes, size: int = -1) -> Optional[str]:
    """
    Return a UTF-8 encoded version of a C-string
    :param s: C-style string pointer
    :param size: int: size of string if known
    :return: UTF8-encoded Python string, or None
    """
    s_at = string_at(s, size)
    # print('s_at_type', type(s_at), file=sys.stderr)
    assert isinstance(s_at, bytes)
    return s_at.decode("utf8") if s_at is not None else None


def u_string_free(s: c_char_p) -> Optional[str]:
    result = u_string_at(s)
    g_free(s)
    return result


# pylint: disable=R0903
class cClass(object):
    """Just a handy collection of POINTER() objects"""

    def __init__(self):
        pass

    AssimObj = POINTER(AssimCtypes.AssimObj)
    NetAddr = POINTER(AssimCtypes.NetAddr)
    NetIO = POINTER(AssimCtypes.NetIO)
    ReliableUDP = POINTER(AssimCtypes.ReliableUDP)
    Frame = POINTER(AssimCtypes.Frame)
    AddrFrame = POINTER(AssimCtypes.AddrFrame)
    IntFrame = POINTER(AssimCtypes.IntFrame)
    SeqnoFrame = POINTER(AssimCtypes.SeqnoFrame)
    CstringFrame = POINTER(AssimCtypes.CstringFrame)
    UnknownFrame = POINTER(AssimCtypes.UnknownFrame)
    SignFrame = POINTER(AssimCtypes.SignFrame)
    FrameSet = POINTER(AssimCtypes.FrameSet)
    ConfigContext = POINTER(AssimCtypes.ConfigContext)
    ConfigValue = POINTER(AssimCtypes.ConfigValue)
    IpPortFrame = POINTER(AssimCtypes.IpPortFrame)
    CompressFrame = POINTER(AssimCtypes.CompressFrame)
    guint8 = POINTER(AssimCtypes.guint8)
    GSList = POINTER(AssimCtypes.GSList)
    CryptCurve25519 = POINTER(AssimCtypes.CryptCurve25519)


# pylint: disable=C0123
def not_this_exact_type(obj, cls):
    """Do return True if this is NOT the given type.
    This is necessary for dealing with Ctypes, but pylint hates this construct
    so we ignore its warning.
    """
    return type(obj) is not cls


def CCref(obj):
    """
    Increment the reference count to an AssimObj (_not_ a pyAssimObj)
    Need to call CCref under the following circumstances:
        When we are creating an object that points to another underlying C-class object
        which already has a permanent reference to it somewhere else
        For example, if we're returning a pyNetAddr object that points to a NetAddr object
        that's in a ConfigContext object.  If we don't, then when our pyNetAddr object goes
        out of scope, then the underlying NetAddr object will be freed, even though there's
        a reference to it in the ConfigContext object.  Conversely, if the ConfigContext
        object goes out of scope first, then the our pyNetAddr object could become invalid.

    Do not call it when you've constructed a new object that there were no previous pointers
        to.
    """
    base = obj[0]
    while not_this_exact_type(base, AssimObj):
        base = base.baseclass
    print(f"CCref-ing {base}.ref({obj})")
    base.ref(obj)
    print(f"CCref-ed {base}.ref({obj}): {base._refcount}")


def CCunref(obj):
    """Unref an AssimObj object (or subclass)"""
    print(f"CCunref {obj.__class__.__name__}.unref({obj})")
    base = obj[0]
    # This 'hasattr' construct only works because we are the base C-class
    while not hasattr(base, "unref"):
        print(f"CCunref: next class {base.__class__.__name__}: {base}")
        print(f"CCunref: baseclass: {base.baseclass}")
        base = base.baseclass
    print(f"CCunref-ing {base.__class__.__name__}.unref({obj}): {base._refcount}")
    base.unref(obj)


class pySwitchDiscovery(object):
    """
    Class for interpreting switch discovery data via LLDP or CDP
    Currently LLDP is better implemented than CDP.
    """

    lldpnames = {
        LLDP_TLV_END: ("END", True),
        LLDP_TLV_CHID: ("ChassisId", True),
        LLDP_TLV_PID: ("PortId", True),
        LLDP_TLV_TTL: ("TTL", True),
        LLDP_TLV_PORT_DESCR: ("PortDescription", False),
        LLDP_TLV_SYS_NAME: ("SystemName", True),
        LLDP_TLV_SYS_DESCR: ("SystemDescription", True),
        LLDP_TLV_SYS_CAPS: ("SystemCapabilities", True),
        LLDP_TLV_MGMT_ADDR: ("ManagementAddress", True),
        LLDP_TLV_ORG_SPECIFIC: ("(OrgSpecific)", True),
    }
    lldp802_1names = {
        LLDP_ORG802_1_VLAN_PVID: ("VlanPvId", False),
        LLDP_ORG802_1_VLAN_PORTPROTO: ("VlanPortProtocol", False),
        LLDP_ORG802_1_VLAN_NAME: ("VlanName", False),
        LLDP_ORG802_1_VLAN_PROTOID: ("VlanProtocolId", False),
    }
    lldp802_3names = {
        LLDP_ORG802_3_PHY_CONFIG: ("PhysicalConfiguration", False),
        LLDP_ORG802_3_POWERVIAMDI: ("PowerViaMDI", False),
        LLDP_ORG802_3_LINKAGG: ("LinkAggregation", False),
    }

    cdpnames = {
        # System-wide capabilities
        CDP_TLV_DEVID: ("ChassisId", True),
        CDP_TLV_CAPS: ("SystemCapabilities", True),
        CDP_TLV_VERS: ("SystemVersion", True),
        CDP_TLV_PLATFORM: ("SystemPlatform", True),
        CDP_TLV_VTPDOMAIN: ("VLANManagementDomain", True),
        CDP_TLV_ADDRESS: ("SystemAddress", True),
        CDP_TLV_MANAGEMENT_ADDR: ("ManagementAddress", True),
        CDP_TLV_SYSTEM_NAME: ("SystemName", True),
        CDP_TLV_LOCATION: ("SystemDescription", True),
        CDP_TLV_HELLO: ("CiscoHello", True),
        # Per-port capabilities follow
        CDP_TLV_TRUST_BITMAP: ("CiscoTrustBitMap", False),
        CDP_TLV_UNTRUSTED_COS: ("CiscoUnTrustedPortCOS", False),
        CDP_TLV_NATIVEVLAN: ("VlanId", False),
        CDP_TLV_VLQUERY: ("VlanQuery", False),
        CDP_TLV_VLREPLY: ("VlanReply", False),
        CDP_TLV_PORTID: ("PortId", False),
        CDP_TLV_EXT_PORTID: ("PortDescription", False),
        CDP_TLV_DUPLEX: ("duplex", False),
        CDP_TLV_MTU: ("mtu", False),
        CDP_TLV_POWER: ("PortPower", False),
    }

    def __init__(self):
        pass

    @staticmethod
    def _byte0(pktstart):
        "Return the first (zeroth) byte from a memory blob"
        return int(cast(pktstart, cClass.guint8)[0])

    @staticmethod
    def _byte1addr(pktstart):
        "Return the address of byte 1 in a memory blob"
        addr = addressof(pktstart.contents) + 1
        return pointer(type(pktstart.contents).from_address(addr))

    @staticmethod
    def _byteN(pktstart, n):
        "Return the Nth byte from a memory blob"
        return int(cast(pktstart, cClass.guint8)[n])

    @staticmethod
    def _byteNaddr(pktstart, n):
        "Return the address of the Nth byte in a memory blob"
        addr = addressof(pktstart.contents) + n
        return pointer(type(pktstart.contents).from_address(addr))

    @staticmethod
    def _decode_netaddr(addrstart, addrlen):
        """Return an appropriate pyNetAddr object corresponding to the given memory blob"""
        byte0 = pySwitchDiscovery._byte0(addrstart)
        byte1addr = pySwitchDiscovery._byte1addr(addrstart)
        c_netaddr = None
        if byte0 == ADDR_FAMILY_IPV6:
            if addrlen != 17:
                return None
            c_netaddr = netaddr_ipv6_new(byte1addr, 0)
        elif byte0 == ADDR_FAMILY_IPV4:
            if addrlen != 5:
                return None
            c_netaddr = netaddr_ipv4_new(byte1addr, 0)
        elif byte0 == ADDR_FAMILY_802:
            if addrlen == 7:
                c_netaddr = netaddr_mac48_new(byte1addr)
            elif addrlen == 9:
                c_netaddr = netaddr_mac64_new(byte1addr)
        if c_netaddr is not None:
            return str(pyNetAddr(None, Cstruct=c_netaddr))
        return None

    @staticmethod
    def decode_discovery(host, interface, instance, wallclock, pktstart, pktend):
        "Return a JSON packet corresponding to the given switch discovery packet"

        if is_valid_lldp_packet(pktstart, pktend):
            # print('>>>>>>>>>>>>>>>LLDP PACKET', file=stderr)
            return pySwitchDiscovery._decode_lldp(
                host, interface, instance, wallclock, pktstart, pktend
            )

        if is_valid_cdp_packet(pktstart, pktend):
            # print('>>>>>>>>>>>>>>>CDP PACKET', file=stderr)
            return pySwitchDiscovery._decode_cdp(
                host, interface, instance, wallclock, pktstart, pktend
            )
        raise ValueError("Malformed Switch Discovery Packet")

    @staticmethod
    def _decode_lldp_chid(tlvptr, tlvlen):
        "Decode the LLDP CHID field, and return an appropriate value"
        chidtype = pySwitchDiscovery._byte0(tlvptr)

        if (
            chidtype == LLDP_CHIDTYPE_COMPONENT
            or chidtype == LLDP_CHIDTYPE_ALIAS
            or chidtype == LLDP_CHIDTYPE_IFNAME
            or chidtype == LLDP_CHIDTYPE_LOCAL
        ):
            sloc = pySwitchDiscovery._byte1addr(tlvptr)
            return u_string_at(sloc, tlvlen - 1)
        elif chidtype == LLDP_CHIDTYPE_MACADDR:
            byte1addr = pySwitchDiscovery._byte1addr(tlvptr)
            Cmacaddr = None
            if tlvlen == 7:
                Cmacaddr = netaddr_mac48_new(byte1addr)
            elif tlvlen == 9:
                Cmacaddr = netaddr_mac64_new(byte1addr)
            if Cmacaddr is not None:
                return pyNetAddr(None, Cstruct=Cmacaddr)
        elif chidtype == LLDP_CHIDTYPE_NETADDR:
            byte1addr = pySwitchDiscovery._byte1addr(tlvptr)
            return pySwitchDiscovery._decode_netaddr(byte1addr, tlvlen - 1)
        return None

    # pylint: disable=R0914,R0912
    @staticmethod
    def _decode_lldp(host, interface, instance, wallclock, pktstart, pktend):
        """Decode LLDP packet into a JSON discovery packet"""
        # print('DECODING LLDP PACKET!<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<', file=stderr)
        thisportinfo = pyConfigContext(
            init={"ConnectsToHost": host, "ConnectsToInterface": interface}
        )
        switchinfo = pyConfigContext(init={"ports": pyConfigContext()})
        metadata = pyConfigContext(
            init={
                "discovertype": "__LinkDiscovery",
                "description": "Link Level Switch Discovery (lldp)",
                "source": "_decode_lldp()",
                "host": host,
                "instance": instance,
                "localtime": str(wallclock),
                "data": switchinfo,
            }
        )
        capnames = [
            None,
            CMAconsts.ROLE_repeater,
            CMAconsts.ROLE_bridge,
            CMAconsts.ROLE_AccessPoint,
            CMAconsts.ROLE_router,
            CMAconsts.ROLE_phone,
            CMAconsts.ROLE_DOCSIS,
            CMAconsts.ROLE_Station,
        ]

        sourcemacptr = pySwitchDiscovery._byteNaddr(cast(pktstart, cClass.guint8), 6)
        if not sourcemacptr:
            return metadata
        Cmacaddr = netaddr_mac48_new(sourcemacptr)
        sourcemac = pyNetAddr(None, Cstruct=Cmacaddr)

        this = cast(get_lldptlv_first(pktstart, pktend), cClass.guint8)
        while this:
            tlvtype = get_lldptlv_type(this, pktend)
            tlvlen = get_lldptlv_len(this, pktend)
            tlvptr = cast(get_lldptlv_body(this, pktend), cClass.guint8)
            # print("EXAMINE:", tlvptr, tlvtype, tlvlen, file=stderr)
            value = None
            if tlvtype not in pySwitchDiscovery.lldpnames:
                print("Cannot find tlvtype %d" % tlvtype, file=stderr)
                tlvtype = None
            else:
                (tlvname, isswitchinfo) = pySwitchDiscovery.lldpnames[tlvtype]

            if (
                tlvtype == LLDP_TLV_PORT_DESCR
                or tlvtype == LLDP_TLV_SYS_NAME
                or tlvtype == LLDP_TLV_SYS_DESCR
            ):  #########################################
                value = u_string_at(tlvptr, tlvlen)

            elif tlvtype == LLDP_TLV_PID:  ###############################################
                pidtype = pySwitchDiscovery._byte0(tlvptr)
                if (
                    pidtype == LLDP_PIDTYPE_ALIAS
                    or pidtype == LLDP_PIDTYPE_IFNAME
                    or pidtype == LLDP_PIDTYPE_LOCAL
                ):
                    sloc = pySwitchDiscovery._byte1addr(tlvptr)
                    value = u_string_at(sloc, tlvlen - 1)

            elif tlvtype == LLDP_TLV_CHID:  #############################################
                value = pySwitchDiscovery._decode_lldp_chid(tlvptr, tlvlen)

            elif tlvtype == LLDP_TLV_MGMT_ADDR:  #########################################
                addrlen = pySwitchDiscovery._byte0(tlvptr)
                byte1addr = pySwitchDiscovery._byte1addr(tlvptr)
                value = pySwitchDiscovery._decode_netaddr(byte1addr, addrlen)

            elif tlvtype == LLDP_TLV_SYS_CAPS:  #########################################
                byte0 = pySwitchDiscovery._byte0(tlvptr)
                byte1 = pySwitchDiscovery._byteN(tlvptr, 1)
                byte2 = pySwitchDiscovery._byteN(tlvptr, 2)
                byte3 = pySwitchDiscovery._byteN(tlvptr, 3)
                caps0 = byte0 << 8 | byte1
                caps1 = byte2 << 8 | byte3
                # The values we assign here have many possibilities
                # pylint: disable=R0204
                value = pyConfigContext()
                mask = 2
                for j in range(1, 7):
                    if caps0 & mask:
                        value[capnames[j]] = (caps1 & mask) != 0
                    mask <<= 1

            elif tlvtype == LLDP_TLV_ORG_SPECIFIC:  ######################################
                pySwitchDiscovery._decode_lldp_org_specific(
                    switchinfo, thisportinfo, tlvptr, tlvlen, pktend
                )

            if value is not None:
                if tlvtype == LLDP_TLV_PID:
                    switchinfo["ports"][value] = thisportinfo
                    thisportinfo["PortId"] = value
                    numericpart = value
                    while len(numericpart) > 0 and not numericpart.isdigit():
                        numericpart = numericpart[1:]
                    # if len > 0 and numericpart.isdigit():
                    #    thisportinfo['PORTNUM'] = int(numericpart)
                else:
                    if isswitchinfo:
                        switchinfo[tlvname] = value
                    else:
                        thisportinfo[tlvname] = value
            this = cast(get_lldptlv_next(this, pktend), cClass.guint8)
        thisportinfo["sourceMAC"] = sourcemac
        return metadata

    @staticmethod
    def _dump_c_bytes(prefix, tlvstart, tlvlen):
        """Dump out data from a given C-style address"""
        dump = "%s: DUMP (%d bytes):" % (prefix, tlvlen)
        for offset in range(0, tlvlen):
            dump += " %02x" % pySwitchDiscovery._byteN(tlvstart, offset)
        print(dump, file=stderr)

    @staticmethod
    def _decode_lldp_org_specific(switchinfo, thisportinfo, tlvptr, tlvlen, pktend):
        """Decode LLDP org-specific TLV sets (or not...)"""
        oui = tlv_get_guint24(tlvptr, pktend)
        # print ('ORG_OUI: 0x%06x' % oui, file=stderr)
        tlv3ptr = pySwitchDiscovery._byteNaddr(tlvptr, 3)
        if oui == 0x0080C2:
            pySwitchDiscovery._decode_lldp_802_1(
                switchinfo, thisportinfo, tlv3ptr, tlvlen - 3, pktend
            )
        elif oui == 0x00120F:
            pySwitchDiscovery._decode_lldp_802_3(
                switchinfo, thisportinfo, tlv3ptr, tlvlen - 3, pktend
            )
        elif oui == 0x0012BB:
            pySwitchDiscovery._decode_lldp_med(
                switchinfo, thisportinfo, tlv3ptr, tlvlen - 3, pktend
            )
        elif oui == 0x00CEFF:
            pySwitchDiscovery._decode_lldp_profibus(
                switchinfo, thisportinfo, tlv3ptr, tlvlen - 3, pktend
            )
        elif oui == 0x00CECF:
            pySwitchDiscovery._decode_lldp_hytec(
                switchinfo, thisportinfo, tlv3ptr, tlvlen - 3, pktend
            )
        else:
            print(
                "Ignored %d bytes of unknown LLDP org-specific extensions. OUI: %06x."
                % (tlvlen, oui),
                file=stderr,
            )

    @staticmethod
    def _decode_lldp_802_1(_switchinfo, thisportinfo, tlvptr, tlvlen, pktend):
        """Decode 802.1 LLDP org-specific TLV sets (or not...)"""
        subtype = pySwitchDiscovery._byte0(tlvptr)
        tlvstart = pySwitchDiscovery._byte1addr(tlvptr)
        if subtype == 1:
            thisportinfo["pvid"] = tlv_get_guint16(tlvstart, pktend)
        elif subtype == 2:
            ppstatus = pySwitchDiscovery._byte0(tlvstart)
            thisportinfo["pp_vlan_capable"] = (ppstatus & 2) == 2
            thisportinfo["pp_vlan_enabled"] = (ppstatus & 4) == 4
            thisportinfo["ppvid"] = tlv_get_guint16(pySwitchDiscovery._byte1addr(tlvstart), pktend)
        elif subtype == 3:
            vlannameaddr = pySwitchDiscovery._byteNaddr(tlvptr, 3)
            namelen = pySwitchDiscovery._byte0(vlannameaddr)
            if namelen != tlvlen - 4:
                print(
                    "F.4: invalid name length %s out of total of %s" % (namelen, tlvlen),
                    file=stderr,
                )
                pySwitchDiscovery._dump_c_bytes("PACKET:", tlvptr, tlvlen)
            else:
                thisportinfo["vid"] = tlv_get_guint16(tlvstart, pktend)
                thisportinfo["vlan_name"] = u_string_at(
                    pySwitchDiscovery._byte1addr(vlannameaddr), namelen
                ).strip()
        else:
            print(
                "Ignored %d bytes of LLDP 802.1 extensions (Annex F, subtype %d)."
                % (tlvlen, subtype),
                file=stderr,
            )

    @staticmethod
    def _decode_lldp_802_3(switchinfo, thisportinfo, tlvptr, tlvlen, pktend):
        """Decode 802.3 LLDP org-specific TLV sets (or not...)"""
        subtype = pySwitchDiscovery._byte0(tlvptr)
        if subtype == 1:
            pySwitchDiscovery._decode_lldp_802_3_mac_phy(
                switchinfo, thisportinfo, pySwitchDiscovery._byte1addr(tlvptr), tlvlen - 1, pktend
            )
            return
        if subtype == LLDP_ORG802_3_MTU:  # G.5: Maximum Frame Size TLV (4)
            mtuaddr = pySwitchDiscovery._byte1addr(tlvptr)
            thisportinfo["mtu"] = tlv_get_guint16(mtuaddr, pktend)
            return
        print(
            "Ignored %d bytes of LLDP 802.3 extensions (Annex G, subtype %d)." % (tlvlen, subtype),
            file=stderr,
        )

    @staticmethod
    def dot3MauTypes(mautype):
        """MAU types and characteristics from RFC 3636 - starting at page 9
        The LLDP spec says that MAU types returned by G2.3 MAU type are to be
        the same as dot3MauType information in RFC 3636.
        This is my take on that information.
        """
        mautypes = {
            1: {"speed": 10, "duplex": "half", "media": "thick coax"},
            2: {"speed": 10, "duplex": "half", "media": "FOIRL"},
            3: {"speed": 10, "duplex": "half", "media": "thick coax"},
            4: {"speed": 10, "duplex": "half", "media": "thin coax"},
            5: {"speed": 10, "media": "UTP"},
            6: {"speed": 10, "media": "passive fiber"},
            7: {"speed": 10, "media": "sync fiber"},
            8: {"speed": 10, "media": "async fiber"},
            9: {"speed": 10, "media": "broadband DTE"},
            10: {"speed": 10, "duplex": "half", "media": "UTP"},
            11: {"speed": 10, "duplex": "full", "media": "UTP"},
            12: {"speed": 10, "duplex": "half", "media": "async fiber"},
            13: {"speed": 10, "duplex": "full", "media": "async fiber"},
            14: {"speed": 100, "media": "4 pair category 3 UTP"},
            15: {"speed": 100, "duplex": "half", "media": "2 pair category 5 UTP"},
            16: {"speed": 100, "duplex": "half", "media": "2 pair category 5 UTP"},
            17: {"speed": 100, "duplex": "half", "media": "X fiber over PMT"},
            18: {"speed": 100, "duplex": "full", "media": "X fiber over PMT"},
            19: {"speed": 100, "duplex": "half", "media": "2 pair category 3 UTP"},
            20: {"speed": 100, "duplex": "full", "media": "2 pair category 3 UTP"},
            21: {"speed": 1000, "duplex": "half", "media": "PCS/PMA, unknown PMD"},
            22: {"speed": 1000, "duplex": "full", "media": "PCS/PMA, unknown PMD"},
            23: {"speed": 1000, "duplex": "half", "media": "fiber over long-wavelength laser"},
            24: {"speed": 1000, "duplex": "full", "media": "fiber over long-wavelength laser"},
            25: {"speed": 1000, "duplex": "half", "media": "fiber over short-wavelength laser"},
            26: {"speed": 1000, "duplex": "full", "media": "fiber over short-wavelength laser"},
            27: {"speed": 1000, "duplex": "half", "media": "copper over 150-ohm balanced cable"},
            28: {"speed": 1000, "duplex": "full", "media": "copper over 150-ohm balanced cable"},
            29: {"speed": 1000, "duplex": "half", "media": "Four-pair Category 5 UTP"},
            30: {"speed": 1000, "duplex": "full", "media": "Four-pair Category 5 UTP"},
            31: {"speed": 10000, "media": "X PCS/PMA, unknown MD"},
            32: {"speed": 10000, "media": "X fiber over WWDM optics"},
            33: {"speed": 10000, "media": "R PCS/PMA, unknown PMD"},
            34: {"speed": 10000, "media": "R fiber over 1550 nm optics"},
            35: {"speed": 10000, "media": "R fiber over 1310 nm optics"},
            36: {"speed": 10000, "media": "R fiber over 850 nm optics"},
            37: {"speed": 10000, "media": "W PCS/PMA, unknown PMD"},
            38: {"speed": 10000, "media": "W fiber over 1550 nm optics"},
            39: {"speed": 10000, "media": "R fiber over 1310 nm optics"},
            40: {"speed": 10000, "media": "R fiber over 850 nm optics"},
        }
        return mautypes[mautype] if mautype in mautypes else {}

    @staticmethod
    def _decode_lldp_802_3_mac_phy(_switchinfo, thisportinfo, tlvptr, tlvlen, pktend):
        """Decode 802.3 MAC/PHY TLV org-specific TLV (or not...)"""
        if tlvlen != 5:
            print(
                "Invalid %d byte LLDP 802.3 MAC/PHY information (Annex G.2)." % tlvlen, file=stderr
            )
            return
        autoneg_status = pySwitchDiscovery._byte0(tlvptr)
        thisportinfo["autoneg_supported"] = (autoneg_status & 0x01) == 0x01
        thisportinfo["autoneg_enabled"] = (autoneg_status & 0x10) == 0x10
        # @TODO: Need to add info about autonegotiation speeds/duplexes supported (pmd_autoneg)
        # I'm ignoring the PMD_AUTONEG field because it's not horribly important
        # and it's incorrect on the switches in my test lab - and it's kinda
        # complicated to decode and figure out ;-)
        #
        # It has one bit for each speed/duplex it is _capable_ of autonegotiating.
        # PMD auto-negotiation advertised capability is described as the field
        # ifMauAutoNegCapAdvertisedBits in RFC 3636 (page 42)
        # pmd_autoneg_addr = pySwitchDiscovery._byte1addr(tlvptr)
        # pmd_autoneg = tlv_get_guint16(pmd_autoneg_addr, pktend)
        mau_addr = pySwitchDiscovery._byteNaddr(tlvptr, 3)
        mau_type = tlv_get_guint16(mau_addr, pktend)
        mauinfo = pySwitchDiscovery.dot3MauTypes(mau_type)
        for key in mauinfo:
            thisportinfo[key] = mauinfo[key]
        # print("Autoneg_status: 0x%02x" % autoneg_status), file=stderr)
        # print("pmd_autoneg: %d" % pmd_autoneg), file=stderr)
        # print("MAU type: %d" % mau_type), file=stderr)

    @staticmethod
    def _decode_lldp_med(switchinfo, _thisportinfo, tlvptr, tlvlen, _pktend):
        """Decode LLDP-MED org-specific TLV (or not...)"""
        subtype = pySwitchDiscovery._byte0(tlvptr)
        #  for Location Identification (0x03) see https://tools.ietf.org/html/rfc4776#page-7
        # Co-ordinate LCI
        # Coordinate-based location data format uses geospatial data, that is, latitude,
        # longitude, and altitude (height or floors), including indications of resolution, with
        # reference to a particular datum: WGS 84, NAD83-North American Vertical Datum of 1988
        # (NAVD88), or NAD83-Mean Lower Low Water (MLLW). For more information, see RFC 3825,
        # Dynamic Host Configuration Protocol Option for Coordinate-based Location
        # Configuration Information.

        # ELIN LCI
        # Emergency Location Identification Number (ELIN) location data format provides a unique
        # number for each location for Emergency Call Services (ECS). In North America, ELINs
        # are typically 10 digits long; ELINs up to 25 digits are supported.

        # Civic Address LCI
        # The Civic Address location data format uses common street address format, as described
        # in RFC4776.
        if subtype == 5:
            pySwitchDiscovery._get_med_string(switchinfo, "hardware_revision", tlvptr, tlvlen)
        elif subtype == 6:
            pySwitchDiscovery._get_med_string(switchinfo, "firmware_revision", tlvptr, tlvlen)
        elif subtype == 7:
            pySwitchDiscovery._get_med_string(switchinfo, "software_revision", tlvptr, tlvlen)
        elif subtype == 8:
            pySwitchDiscovery._get_med_string(switchinfo, "serial_number", tlvptr, tlvlen)
        elif subtype == 9:
            pySwitchDiscovery._get_med_string(switchinfo, "manufacturer", tlvptr, tlvlen)
        elif subtype == 10:
            pySwitchDiscovery._get_med_string(switchinfo, "model", tlvptr, tlvlen)
        elif subtype == 11:
            pySwitchDiscovery._get_med_string(switchinfo, "asset_id", tlvptr, tlvlen)
        else:
            print(
                "Ignored %d bytes of LLDP-MED extensions (subtype %d)." % (tlvlen, subtype),
                file=stderr,
            )

    @staticmethod
    def _get_med_string(info, name, tlvptr, tlvlen):
        """Decode LLDP-MED string value - trim off extra white space at end"""
        strptr = cast(pySwitchDiscovery._byte1addr(tlvptr), c_char_p)
        info[name] = u_string_at(strptr, tlvlen - 1).strip()

    @staticmethod
    def _decode_lldp_profibus(_switchinfo, _thisportinfo, _tlvptr, tlvlen, _pktend):
        """Decode LLDP Profibus org-specific TLV (or not...)"""
        print("Ignored %d bytes of Profibus International LLDP extensions." % tlvlen, file=stderr)

    @staticmethod
    def _decode_lldp_hytec(_switchinfo, _thisportinfo, _tlvptr, tlvlen, _pktend):
        """Decode LLDP Hytec org-specific TLV (or not...)"""
        print("Ignored %d bytes of Hytec Geraetebau GmbH LLDP extensions." % tlvlen, file=stderr)

    @staticmethod
    def _decode_cdp(host, interface, instance, wallclock, pktstart, pktend):
        "Decode CDP packet into a JSON discovery packet"
        thisportinfo = pyConfigContext(
            init={"ConnectsToHost": host, "ConnectsToInterface": interface}
        )
        switchinfo = pyConfigContext(init={"ports": pyConfigContext()})
        metadata = pyConfigContext(
            init={
                "discovertype": "__LinkDiscovery",
                "description": "Link Level Switch Discovery (cdp)",
                "source": "_decode_cdp()",
                "host": host,
                "instance": instance,
                "localtime": str(wallclock),
                "data": switchinfo,
            }
        )
        sourcemacptr = pySwitchDiscovery._byteNaddr(cast(pktstart, cClass.guint8), 6)
        if not sourcemacptr:
            return metadata
        Cmacaddr = netaddr_mac48_new(sourcemacptr)
        sourcemac = pyNetAddr(None, Cstruct=Cmacaddr)
        this = cast(get_cdptlv_first(pktstart, pktend), cClass.guint8)
        while this:
            tlvtype = get_cdptlv_type(this, pktend)
            tlvlen = get_cdptlv_len(this, pktend)
            tlvptr = cast(get_cdptlv_body(this, pktend), cClass.guint8)
            this = cast(get_cdptlv_next(this, pktend), cClass.guint8)
            value = None
            # Each of the different cases handles 'value' differently
            # pylint: disable=R0204
            if tlvtype not in pySwitchDiscovery.cdpnames:
                tlvname = "TLV_0x%02x" % tlvtype
                isswitchinfo = True  # Gotta do _something_...
            else:
                (tlvname, isswitchinfo) = pySwitchDiscovery.cdpnames[tlvtype]
            if tlvtype == CDP_TLV_DEVID:
                value = u_string_at(tlvptr, tlvlen - 4)
            elif tlvtype == CDP_TLV_ADDRESS:
                # 4 byte count + 'count' addresses
                value = pySwitchDiscovery.getcdpaddresses(tlvlen, tlvptr, pktend)
            elif tlvtype == CDP_TLV_PORTID:
                value = u_string_at(tlvptr, tlvlen - 4)
            elif tlvtype == CDP_TLV_CAPS:
                # bytez = [ '%02x' % pySwitchDiscovery._byteN(tlvptr, j) for j in range(0, tlvlen)]
                # print('CAPBYTES = ', bytez, file=stderr)
                caps = pySwitchDiscovery.getNint(tlvptr, 4, pktend)
                # print('CAPS IS: 0x%08x (%d bytes)' % (caps, tlvlen)), file=stderr)
                value = pySwitchDiscovery.construct_cdp_caps(caps)
            elif tlvtype == CDP_TLV_VERS:
                value = u_string_at(tlvptr, tlvlen - 4)
            elif tlvtype == CDP_TLV_PLATFORM:
                value = u_string_at(tlvptr, tlvlen - 4)
            elif tlvtype == CDP_TLV_POWER:
                tlen = tlvlen if tlvlen <= 2 else 2
                value = pySwitchDiscovery.getNint(tlvptr, tlen, pktend)
            elif tlvtype == CDP_TLV_MTU:
                value = pySwitchDiscovery.getNint(tlvptr, tlvlen, pktend)
            elif tlvtype == CDP_TLV_SYSTEM_NAME:
                value = u_string_at(tlvptr, tlvlen - 4)
            elif tlvtype == CDP_TLV_MANAGEMENT_ADDR:
                # 4 byte count + 'count' addresses
                value = pySwitchDiscovery.getcdpaddresses(tlvlen, tlvptr, pktend)
            elif tlvtype == CDP_TLV_VTPDOMAIN:
                value = u_string_at(tlvptr, tlvlen - 4)
            elif tlvtype == CDP_TLV_NATIVEVLAN:
                value = tlv_get_guint16(tlvptr, pktend)
            elif tlvtype == CDP_TLV_UNTRUSTED_COS:
                value = pySwitchDiscovery._byte0(tlvptr)
            elif tlvtype == CDP_TLV_DUPLEX:
                value = "half" if pySwitchDiscovery._byte0(tlvptr) == 0 else "full"
            elif tlvtype == CDP_TLV_LOCATION:
                value = u_string_at(tlvptr, tlvlen - 4)
            elif tlvtype == CDP_TLV_EXT_PORTID:
                value = u_string_at(tlvptr, tlvlen - 4)
            else:
                value = "0x"
                for offset in range(0, tlvlen):
                    value += "%02x" % pySwitchDiscovery._byteN(tlvptr, offset)
                # print('Ignoring CDP field %s: %s' % (tlvname, value), file=stderr)
                value = None

            if value is None:
                print(
                    "Ignored %d bytes for %s field [0x%02x]" % (tlvlen, tlvname, tlvtype),
                    file=stderr,
                )
            else:
                if tlvtype == CDP_TLV_PORTID:
                    switchinfo["ports"][value] = thisportinfo
                    thisportinfo["PortId"] = value
                    numericpart = value
                    while len(numericpart) > 0 and not numericpart.isdigit():
                        numericpart = numericpart[1:]
                    # if len > 0 and numericpart.isdigit():
                    #    thisportinfo['PORTNUM'] = int(numericpart)
                else:
                    if isswitchinfo:
                        switchinfo[tlvname] = value
                    else:
                        thisportinfo[tlvname] = value
                # print(('TLVNAME[%s] %s has value "%s" -- len: %d', file=stderr)
                # %   (tlvtype, tlvname, value, len(str(value))))
        thisportinfo["sourceMAC"] = sourcemac
        return metadata

    @staticmethod
    def getNint(tlvptr, tlvlen, pktend):
        """Return an integer of any size that we support..."""
        intptr = tlvptr
        if tlvlen == 1:
            return tlv_get_guint8(intptr, pktend)
        if tlvlen == 2:
            return tlv_get_guint16(intptr, pktend)
        if tlvlen == 3:
            return tlv_get_guint24(intptr, pktend)
        if tlvlen == 4:
            return tlv_get_guint32(intptr, pktend)
        if tlvlen == 8:
            return tlv_get_guint64(intptr, pktend)
        return None

    @staticmethod
    def construct_cdp_caps(capval):
        """Construct Capability value from the CDP capability integer"""
        capnames = [
            CMAconsts.ROLE_router,
            CMAconsts.ROLE_tb_bridge,
            CMAconsts.ROLE_srcbridge,
            CMAconsts.ROLE_bridge,
            CMAconsts.ROLE_host,
            CMAconsts.ROLE_igmp,
            CMAconsts.ROLE_repeater,
        ]
        mask = 1
        value = []
        for j in range(0, len(capnames)):
            if capval & mask:
                # value[capnames[j]] = ((capval & mask) != 0)
                value.append(capnames[j])
            mask <<= 1
        return value

    @staticmethod
    def getcdpaddresses(tlvlen, tlvstart, pktend):
        """
        Decode utterly bizarre CDP-specific address list format
        4 bytes address count
        'count' addresses in this form:
            one bytes protocol length
            'protocol length' bytes of protocol type
            two bytes address length
            'address length' bytes of address
            IPv4:
                protocol length = 1, protocol type = 0xCC
            IPv6:
                protocol length = 8 and address length = 16
                protocol type == 0xAAAA0300000086DD ??
            +-------+--------------------+----------+-----------------+
            |Proto  |Protocol Type       | address  | Actual address  |
            |Length |(protolength bytes) | length   | (addresslength  |
            |1 byte |(1-255 bytes)       | (2 bytes)|  bytes)         |
            +-------+--------------------+----------+-----------------+

            Min length for an IPV4 address is 8 bytes
        """
        minlength = 8
        retlist = []
        offset = 0
        count = pySwitchDiscovery.getNint(tlvstart, 4, pktend)
        offset += 4
        for j in range(0, count):
            addr = None
            if (offset + minlength) > tlvlen:
                break
            protolen = pySwitchDiscovery.getNint(
                pySwitchDiscovery._byteNaddr(cast(tlvstart, cClass.guint8), offset), 1, pktend
            )
            offset += 2
            if protolen < 1:
                break
            if offset >= tlvlen:
                break
            if protolen == 1:
                prototype = pySwitchDiscovery._byteN(tlvstart, offset + protolen - 1)
            elif protolen == 16:
                prototype = pySwitchDiscovery.getNint(
                    pySwitchDiscovery._byteNaddr(
                        cast(tlvstart, cClass.guint8), offset + protolen - 2
                    ),
                    2,
                    pktend,
                )
            else:
                prototype = 0xDEADBEEF
            offset += protolen
            if offset > tlvlen:
                break
            addrlen = pySwitchDiscovery.getNint(
                pySwitchDiscovery._byteNaddr(cast(tlvstart, cClass.guint8), offset), 2, pktend
            )
            if protolen == 1 and addrlen == 4 and prototype == 0xCC:
                addrstr = ""
                for j in (offset + 2, offset + 3, offset, offset + 1):
                    addrstr += chr(pySwitchDiscovery._byteN(tlvstart, j))
                addr = netaddr_ipv4_new(c_char_p(addrstr.encode("utf8")), 0)
            elif protolen == 8 and addrlen == 16 and prototype == 0x86DD:
                # protocol type == 0xAAAA0300000086DD
                addr = netaddr_ipv6_new(
                    pySwitchDiscovery._byteNaddr(cast(tlvstart, cClass.guint8), offset), 0
                )
            if addr is not None:
                pyaddr = pyNetAddr(Cstruct=addr, addrstring=None)
                retlist.append(pyaddr)
            offset += addrlen

        if len(retlist) == 0:
            return None
        if len(retlist) == 1:
            return retlist[0]
        return retlist


class pyAssimObj(object):
    """The base object for all the C-class objects"""

    object_map = {}

    def __init__(self, Cstruct=None):
        "Create a base pyAssimObj object"
        self._Cstruct = None
        if Cstruct is not None:
            assert not isinstance(Cstruct, int)
            self._Cstruct = Cstruct
        else:
            self._Cstruct = cast(assimobj_new(0), cClass.AssimObj)
        addr = self.int_address()
        # if addr in pyAssimObj.object_map:
        #     addrmap = pyAssimObj.object_map[addr]
        #     raise RuntimeError(f"Reallocating {addr:0x%x} {addrmap} "
        #                        f"as {self.__class__.__name__}: address")
        pyAssimObj.object_map[addr] = {
            "Python class": self.__class__,
            "C class": str(self.cclassname())
        }
        # print 'ASSIMOBJ:init: %s' % (Cstruct)
        if isinstance(self, pyNetAddr):
            self.creation_stack = traceback.extract_stack()
        else:
            self.creation_stack = []

    def int_address(self):

        # print(f"ATTRIBUTES OF OBJECT: {dir(ctypes.addressof(self._Cstruct))}", file=stderr)
        # print(f"STR OF OBJECT: {str(ctypes.addressof(self._Cstruct))}", file=stderr)
        return int(ctypes.addressof(self._Cstruct))

    def cclassname(self):
        "Return the 'C' class name for this object"
        return proj_class_classname(self._Cstruct).decode("utf8")

    def __str__(self):
        "Convert this AssimObj into a printable string"
        if not self._Cstruct:
            return "[None]"
        base = self._Cstruct[0]
        while not_this_exact_type(base, AssimObj):
            base = base.baseclass
        cstringret = cast(base.toString(self._Cstruct), c_char_p)
        ret = u_string_at(cstringret)
        g_free(cstringret)
        return ret

    # pylint: disable=W0603
    def __del__(self):
        "Free up the underlying Cstruct for this pyAssimObj object."
        if not self._Cstruct or self._Cstruct is None:
            return
        addr = self.int_address()
        if addr not in pyAssimObj.object_map:
            traceback.print_stack()
            raise ValueError(f"Bad {self.__class__.__name__} _Cstruct: {addr:0x%x}")
        del pyAssimObj.object_map[addr]
        global badfree
        badfree = 0
        print(f"{self.__class__.__name__}:PyAssimObj.CCunref{self._Cstruct}")
        c_class_name: str = self.cclassname()
        print(f"{self.__class__.__name__}:PyAssimObj.CCunref-class:{c_class_name}")
        if c_class_name == '(unknown class)':
            self.log(f"CRITICAL: Unrefing dead object {self.__class__.__name__}")
            if self.creation_stack:
                self.log(f"CRITICAL: Dead {self.__class__.__name__} object creation Traceback:")
                print("".join(traceback.format_list(self.creation_stack)))
            self._Cstruct = None
            return
        CCunref(self._Cstruct)
        if badfree != 0:
            print("Attempt to free something already freed(%s)" % str(self._Cstruct), file=stderr)
            traceback.print_stack()
            badfree = 0
        self._Cstruct = None

    def refcount(self):
        """Return the reference count for this object"""
        base = self._Cstruct[0]
        while hasattr(base, "baseclass"):
            base = base.baseclass
        return base._refcount


class pyNetAddr(pyAssimObj):
    """This class represents the Python version of our C-class @ref NetAddr
    - represented by the struct _NetAddr.
    """

    def __init__(self, addrstring, port=None, Cstruct=None):
        """This constructor needs a list of integers of the right length as its first argument.
        The length of the list determines the type of address generated.
         4 bytes == ipv4
         6 bytes == MAC address
         8 bytes == MAC address
         16 bytes == ipv6 address
        This is slightly sleazy but it should work for the forseeable future.
        """

        self._Cstruct = None  # Silence error messages in failure cases

        if Cstruct is not None:
            assert (not isinstance(Cstruct, int)) and Cstruct
            pyAssimObj.__init__(self, Cstruct=Cstruct)
            if port is not None:
                self.setport(port)
            assert self._Cstruct
            return

        if port is None:
            port = 0

        if isinstance(addrstring, six.string_types) or isinstance(addrstring, pyNetAddr):
            addrstring = str(addrstring)
        if isinstance(addrstring, str):
            cs = cast(netaddr_dns_new(addrstring), cClass.NetAddr)
            if not cs:
                raise ValueError('Illegal NetAddr initial value: "%s"' % addrstring)
            if port != 0:
                cs[0].setport(cs, port)
            pyAssimObj.__init__(self, Cstruct=cs)
            assert self._Cstruct
            return

        self._init_from_binary(addrstring, port)
        assert self._Cstruct

    def _init_from_binary(self, addrstring, port):
        """Initialize an addrstring from a binary argument"""
        alen = len(addrstring)
        addr = create_string_buffer(alen)
        # print("ADDRTYPE:", type(addr), file=stderr)
        # print("ADDRSTRINGTYPE:", type(addrstring), file=stderr)
        for i in range(0, alen):
            asi = addrstring[i]
            if isinstance(asi, six.string_types):
                addr[i] = str(asi)
            else:
                addr[i] = asi
        # print('ADDR = %s'  % addr, file=stderr)
        if alen == 4:  # ipv4
            NA = netaddr_ipv4_new(addr, port)
        elif alen == 16:  # ipv6
            NA = netaddr_ipv6_new(addr, port)
        elif alen == 6:  # "Normal" 48-bit MAC address
            assert port == 0
            NA = netaddr_mac48_new(addr, port)
        elif alen == 8:  # Extended 64-bit MAC address
            assert port == 0
            NA = netaddr_mac64_new(addr, port)
        else:
            raise ValueError("Invalid address length - not 4, 6, 8, or 16")
        pyAssimObj.__init__(self, Cstruct=cast(NA, cClass.NetAddr))

    def port(self):
        """Return the port (if any) for this pyNetAddr object"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        return base.port(self._Cstruct)

    def setport(self, port):
        """Return the port (if any) for this pyNetAddr object"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        base.setport(self._Cstruct, int(port))

    def addrtype(self):
        """Return the type of address for this pyNetAddr object"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        return base.addrtype(self._Cstruct)

    def addrlen(self):
        """Return the number of bytes necessary to represent this pyNetAddr object on the wire."""
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        return base._addrlen

    def islocal(self):
        """Return True if this address is a local address"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        return base.islocal(self._Cstruct)

    def isanyaddr(self):
        """Return True if this address is the 'ANY' address"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        return base.isanyaddr(self._Cstruct)

    def and_with_cidr(self, cidr):
        """
        Bitwise AND this IP address with a CIDR mask - in place
        :return: NetAddr: (self)
        """
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        base.and_with_cidr(self._Cstruct, int(cidr))
        return self

    def toIPv6(self, port=None):
        """Return an equivalent IPv6 address to the one that was given. Guaranteed to be a copy"""
        if str(self) == "127.0.0.1":  # FIXME: Fix C code to not do this, and us to not rely on it!
            return pyNetAddr("::ffff:127.0.0.1")
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        newcs = cast(base.toIPv6(self._Cstruct), cClass.NetAddr)
        return pyNetAddr(None, Cstruct=newcs, port=port)

    def toIPv4(self, port=None):
        """Return an equivalent IPv4 address to the one that was given - if possible.
        Guaranteed to be a copy"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        newcs = cast(base.toIPv4(self._Cstruct), cClass.NetAddr)
        if not newcs:
            raise ValueError("Could not be converted to IPv4: %s" % (str(self)))
        return pyNetAddr(None, Cstruct=newcs, port=port)

    def __repr__(self):
        """Return a canonical representation of this NetAddr"""
        assert self._Cstruct
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        # cstringret = cast(base.canonStr(self._Cstruct), c_char_p)
        cstringret = base.canonStr(self._Cstruct)
        ret = u_string_at(cstringret)
        g_free(cstringret)
        return ret

    def __eq__(self, other):
        """Return True if the two pyNetAddrs are equal"""
        if not hasattr(other, "_Cstruct") or not other._Cstruct or not self._Cstruct:
            return False
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        return True if base.equal(self._Cstruct, other._Cstruct) else False

    def __hash__(self):
        """Return a hash value for the given pyNetAddr"""
        if not self._Cstruct:
            return 0
        base = self._Cstruct[0]
        while not_this_exact_type(base, NetAddr):
            base = base.baseclass
        return base.hash(self._Cstruct)


class pyFrame(pyAssimObj):
    """This class represents the Python version of our C-class @ref Frame
    - represented by the struct _Frame.
    This class is a base class for several different pyFrame subclasses.
    Each of these various pyFrame subclasses have a corresponding C-class @ref Frame subclass.
    The purpose of these pyFrames and their subclasses is to talk on the wire with our C code in our
    nanoprobes.

    Deliberately leaving out the updatedata() C-class member function - at least for now.
    I suspect that the Python code will only need the corresponding calls in a @ref FrameSet
    - which would then update the corresponding @ref Frame member functions...
    """

    #
    # 	Our subclasses need to implement these methods:
    # 		__init__ - subclass initializer
    # 		from_Cstruct classmethod - call the corresponding xxxframe_tlvconstructor() function
    # 			to act as a pseudo-constructor.  This method/constructor is used to create
    # 			Python objects from incoming packet data.
    #
    def __init__(self, initval, Cstruct=None):
        """Initializer for the pyFrame object."""
        if Cstruct is None:
            try:
                frametype = initval.tlvtype
            except (AttributeError):
                frametype = int(initval)
            # If we don't do this, then a subclass __init__ function must do it instead...
            pyAssimObj.__init__(self, Cstruct=cast(frame_new(frametype, 0), Frame_p))
        else:
            pyAssimObj.__init__(self, Cstruct=Cstruct)

    def frametype(self):
        """Return the TLV type for the pyFrame object."""
        base = self._Cstruct[0]
        while not_this_exact_type(base, Frame):
            base = base.baseclass
        return base.type

    def framelen(self):
        """Return the length of this frame in bytes (TLV length)."""
        base = self._Cstruct[0]
        while not_this_exact_type(base, Frame):
            base = base.baseclass
        return base.length

    def framevalue(self):
        """Return a C-style pointer to the underlying raw TLV data (if any)"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, Frame):
            base = base.baseclass
        return cast(base.value, c_char_p)

    def frameend(self):
        """Return a C-style pointer to the underlying raw TLV data (if any)"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, Frame):
            base = base.baseclass
        return cast(base.value + base.length, c_char_p)

    def dataspace(self):
        """Return the amount of space this frame needs - including type and length"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, Frame):
            base = base.baseclass
        return base.dataspace(cast(self._Cstruct, Frame_p))

    def isvalid(self):
        """Return True if this Frame is valid"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, Frame):
            base = base.baseclass
        #        pstart = pointer(cast(base.value, c_char_p))
        #        if pstart[0] is None:
        #            return False
        return int((base.isvalid(cast(self._Cstruct, Frame_p), None, None))) != 0

    def setvalue(self, value):
        """Assign a chunk of memory to the Value portion of this Frame"""
        vlen = len(value)
        if isinstance(value, six.string_types):
            valbuf = create_string_buffer(vlen + 1)
            for i in range(0, vlen):
                vi = value[i]
                valbuf[i] = ord(vi) if isinstance(vi, str) else vi
            valbuf[vlen] = 0
            vlen += 1
        else:
            valbuf = create_string_buffer(vlen)
            for i in range(0, vlen):
                vi = value[i]
                valbuf[i] = int(vi)
        base = self._Cstruct[0]
        valptr = MALLOC(vlen)
        memmove(valptr, valbuf, vlen)
        while not_this_exact_type(base, Frame):
            base = base.baseclass
        base.setvalue(
            cast(self._Cstruct, Frame_p), cast(valptr, c_char_p), vlen, cast(None, GDestroyNotify)
        )

    def dump(self, prefix):
        """Dump out this Frame (using C-class "dump" member function)"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, Frame):
            base = base.baseclass
        base.dump(cast(self._Cstruct, Frame_p), cast(prefix, c_char_p))

    def __str__(self):
        """Convert this Frame to a string"""
        base = self._Cstruct[0]
        while not_this_exact_type(base, AssimObj):
            base = base.baseclass
        cstringret = cast(base.toString(self._Cstruct), c_char_p)
        ret = u_string_at(cstringret)
        g_free(cstringret)
        return "%s: %s" % (FrameTypes.get(self.frametype())[1], ret)

    @staticmethod
    def Cstruct2Frame(frameptr) -> 'pyFrame':
        """Unmarshalls a binary blob (Cstruct) into a Frame"""
        print(f"Cstruct2Frame: {frameptr}")
        frameptr = cast(frameptr, cClass.Frame)
        print(f"Cstruct2Frame: CCref-ing {frameptr}")
        CCref(frameptr)
        frametype = frameptr[0].type
        print(f"Cstruct2Frame:  frametype {frametype}")
        Cclassname: str = proj_class_classname(frameptr).decode("utf8")
        our_c_class = getattr(cClass, Cclassname)
        print(f"OUR C CLASS: {our_c_class}, {type(our_c_class)}")
        print(f"FRAMEPTR: {frameptr}, {type(frameptr)}")
        class_frameptr = cast(frameptr, our_c_class)
        if Cclassname == "NetAddr":
            frame_result = pyNetAddr(frametype, None, Cstruct=class_frameptr)
        elif Cclassname == "IpPortFrame":
            frame_result = pyIpPortFrame(frametype, None, None, Cstruct=class_frameptr)
        else:
            pyclassname = "py" + Cclassname
            assert pyclassname in globals()
            pyobjclass = globals()[pyclassname]
            print(f"PYOBJCLASS: {pyobjclass}")
            assert issubclass(pyobjclass, pyFrame)
            frame_result = pyobjclass(frametype, Cstruct=class_frameptr)
        print(f"FRAME_RESULT w/o EVAL: {frame_result}: {type(frame_result)}")
        return frame_result



class pyCompressFrame(pyFrame):
    """This class represents the Python version of our C-class CompressFrame
    - represented by the struct _CompressFrame.  It is used to tell us that
    what kind of compression we want in our communication stream.
    """

    def __init__(
        self, frametype=FRAMETYPE_COMPRESS, compression_method=COMPRESS_ZLIB, Cstruct=None
    ):
        self._Cstruct = None  # Keep error legs from complaining.
        if Cstruct is None:
            Cstruct = compressframe_new_string(frametype, compression_method)
        else:
            Cstruct = Cstruct
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)


class pyAddrFrame(pyFrame):
    """This class represents the Python version of our C-class AddrFrame
    - represented by the struct _AddrFrame.
    """

    def __init__(self, frametype, addrstring=None, port=None, Cstruct=None):
        "Initializer for the pyAddrFrame object."
        self._Cstruct = None  # Keep error legs from complaining.
        if Cstruct is None:
            if isinstance(addrstring, pyNetAddr):
                self._pyNetAddr = addrstring
            else:
                self._pyNetAddr = pyNetAddr(addrstring, port=port)
            Cstruct = addrframe_new(frametype, 0)
            if addrstring is not None:
                Cstruct[0].setnetaddr(Cstruct, self._pyNetAddr._Cstruct)
        else:
            assert port is None
            assert addrstring is None
            # Allow for prefixed address type - two bytes
            addrlen = Cstruct[0].baseclass.length - 2
            assert addrlen == 4 or addrlen == 6 or addrlen == 8 or addrlen == 16, (
                "addrlen is %d" % addrlen
            )
            addrstr = Cstruct[0].baseclass.value + 2
            addrstring = create_string_buffer(addrlen)
            memmove(addrstring, addrstr, addrlen)
            self._pyNetAddr = pyNetAddr(addrstring, port=None)
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)

    def addrtype(self):
        """Return the Address type for this AddrFrame"""
        return self._pyNetAddr.addrtype()

    def getnetaddr(self):
        """Return the pyNetAddr for this AddrFrame"""
        return self._pyNetAddr

    def __str__(self):
        return "pyAddrFrame(%s, (%s))" % (FrameTypes.get(self.frametype())[1], str(self._pyNetAddr))


class pyIpPortFrame(pyFrame):
    """This class represents the Python version of our C-class IpPortFrame
    - represented by the struct _IpPortFrame.
    """

    def __init__(self, frametype, addrstring, port=None, Cstruct=None):
        """Initializer for the pyIpPortFrame object."""
        self._Cstruct = None  # Keep error legs from complaining.
        if Cstruct is None:
            if isinstance(addrstring, pyNetAddr):
                self._pyNetAddr = addrstring
                Cstruct = ipportframe_netaddr_new(frametype, addrstring._Cstruct)
                if not Cstruct:
                    raise ValueError("invalid initializer")
                self.port = addrstring.port()
            else:
                Cstruct = self._init_from_binary(frametype, addrstring, port)
        else:
            assert port is None
            assert addrstring is None
            addrlen = Cstruct[0].baseclass.length - 4  # Allow for prefixed port and address type
            if addrlen != 4 and addrlen != 16:
                raise ValueError("Bad addrlen: %d" % addrlen)
            port = Cstruct[0].port
            self.port = port
            addrstr = Cstruct[0].baseclass.value + 4
            addrstring = create_string_buffer(addrlen)
            memmove(addrstring, addrstr, addrlen)
            self._pyNetAddr = pyNetAddr(addrstring, port=port)
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)

    def _init_from_binary(self, frametype, addrstring, port):
        """Initialize a pyIpAddrFrame from a binary argument"""
        addrlen = len(addrstring)
        self._pyNetAddr = pyNetAddr(addrstring, port=port)
        if self._pyNetAddr is None:
            raise ValueError("Invalid initializer.")
        addrstr = create_string_buffer(addrlen)
        for j in range(0, addrlen):
            addrstr[j] = addrstring[j]
        if addrlen == 4:
            Cstruct = ipportframe_ipv4_new(frametype, port, addrstr)
        elif addrlen == 16:
            Cstruct = ipportframe_ipv6_new(frametype, port, addrstr)
        else:
            raise ValueError("Bad address length: %d" % addrlen)
        self.port = port
        if port == 0:
            raise ValueError("zero port")
        if not Cstruct:
            raise ValueError("invalid initializer")
        return Cstruct

    def addrtype(self):
        """Return the Address type of this pyIpPortFrame"""
        return self._pyNetAddr.addrtype()

    def getnetaddr(self):
        """Return the NetAddr of this pyIpPortFrame"""
        return self._pyNetAddr

    def getport(self):
        """Return the port of this pyIpPortFrame"""
        return self._pyNetAddr.port()


class pyCstringFrame(pyFrame):
    """This class represents the Python version of our C-class CstringFrame
    - represented by the struct _CstringFrame.
    This class represents a Frame standard NUL-terminated C string.
    """

    def __init__(self, frametype, initval=None, Cstruct=None):
        """Constructor for pyCstringFrame object - initial value should be something
        that looks a lot like a Python string"""
        if Cstruct is None:
            Cstruct = cast(cstringframe_new(frametype, 0), cClass.CstringFrame)
        pyFrame.__init__(self, frametype, Cstruct)
        if initval is not None:
            self.setvalue(initval)

    def getstr(self):
        """Return the String part of this pyCstringFrame"""
        base = self._Cstruct[0]
        while not hasattr(base, "value"):
            base = base.baseclass
        return u_string_at(base.value)


class pyIntFrame(pyFrame):
    """This class represents the Python version of our IntFrame C-class
    - represented by the struct _IntFrame.
    This class represents an integer of 1, 2, 3, 4 or 8 bytes.
    """

    def __init__(self, frametype, initval=None, intbytes=4, Cstruct=None):
        """Constructor for pyIntFrame object
        - initial value should be something that looks a lot like an integer"""
        self._Cstruct = None
        if Cstruct is None:
            Cstruct = intframe_new(frametype, intbytes)
        if not Cstruct:
            raise ValueError("Invalid integer size (%d) in pyIntFrame constructor" % intbytes)
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)
        if initval is not None:
            self.setint(initval)

    def __int__(self):
        """Return the integer value of this pyIntFrame. (implemented by the
        underlying IntFrame object)"""
        return self._Cstruct[0].getint(self._Cstruct)

    def __str__(self):
        """Return a string representation of this pyIntFrame (the integer value)."""
        return "pyIntFrame(%s, (%d))" % (FrameTypes.get(self.frametype())[1], int(self))

    def getint(self):
        """Return the integer value of this pyIntFrame - same as __int__."""
        return int(self)

    def setint(self, intval):
        """Set the value of this pyIntFrame to the given integer value.
        Note that this value is range checked by the underlying IntFrame implementation.
        """
        self._Cstruct[0].setint(self._Cstruct, int(intval))

    def intlength(self):
        """Return the number of bytes in the integer underlying this pyIntFrame object.
           (implemented by underlying IntFrame object)"""
        return self._Cstruct[0].intlength(self._Cstruct)


class pyUnknownFrame(pyFrame):
    "Class for a Frame type we don't recognize"

    def __init__(self, frametype, Cstruct=None):
        """Initializer for pyUnknownFrame"""
        if Cstruct is None:
            Cstruct = unknownframe_new(frametype)
        pyFrame.__init__(self, frametype, Cstruct)


class pySeqnoFrame(pyFrame):
    """Class for a Sequence Number Frame - for reliable UDP packet transmission."""

    def __init__(self, frametype, initval=None, Cstruct=None):
        "Initializer for pySeqnoFrame"
        self._Cstruct = None
        # TODO(?): Need to allow for initialization of seqno frames.
        if Cstruct is None:
            Cstruct = seqnoframe_new(frametype, 0)
        if not Cstruct:
            raise ValueError("Constructor error for PySeqnoFrame()")
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)
        if initval is not None:
            self.setqid(initval[0])
            self.setreqid(initval[1])

    def setreqid(self, reqid):
        """Set the request ID portion of this SeqnoFrame"""
        self._Cstruct[0].setreqid(self._Cstruct, reqid)

    def setqid(self, qid):
        """Set the Queue ID portion of this SeqnoFrame"""
        self._Cstruct[0].setqid(self._Cstruct, qid)

    def getreqid(self):
        """Get the request ID portion of this SeqnoFrame"""
        return self._Cstruct[0].getreqid(self._Cstruct)

    def getqid(self):
        """Get the Queue ID portion of this SeqnoFrame"""
        return self._Cstruct[0].getqid(self._Cstruct)

    def __eq__(self, rhs):
        """Compare this pySeqnoFrame to another pySeqnoFrame"""
        lhsbase = self._Cstruct[0]
        while not_this_exact_type(lhsbase, SeqnoFrame):
            lhsbase = lhsbase.baseclass
        return True if lhsbase.equal(self._Cstruct, rhs._Cstruct) else False

    def __str__(self):
        """Convert this pySeqnoFrame to a String"""
        return "pySeqNo(%s: (%d, %d))" % (
            FrameTypes.get(self.frametype())[1],
            self.getqid(),
            self.getreqid(),
        )


class pySignFrame(pyFrame):
    """Class for Digital Signature Frames
    - for authenticating data (subclasses will authenticate senders)"""

    def __init__(self, gchecksumtype, Cstruct=None):
        """Initializer for pySignFrame"""
        self._Cstruct = None
        if Cstruct is None:
            Cstruct = signframe_glib_new(gchecksumtype, 0)
        if not Cstruct:
            raise ValueError("Invalid checksum type (%s) for PySignFrame()" % gchecksumtype)
        pyFrame.__init__(self, initval=FRAMETYPE_SIG, Cstruct=Cstruct)


class pyNVpairFrame(pyFrame):
    """Class for a Frame containing a single name/value pair"""

    def __init__(self, frametype, name, value, Cstruct=None):
        "Initializer for pyNVpairFrame"
        self._Cstruct = None
        if Cstruct is None:
            Cstruct = nvpairframe_new(frametype, name, value, 0)
        if not Cstruct:
            raise ValueError("Invalid NVpair initializer for pyNVPairFrame()")
        pyFrame.__init__(self, initval=frametype, Cstruct=Cstruct)

    def name(self):
        """Return the name portion of a pyNVpairFrame"""
        return u_string_at(self._Cstruct[0].name)

    def value(self):
        """Return the value portion of a pyNVpairFrame"""
        return u_string_at(self._Cstruct[0].value)


class pyCryptFrame(pyFrame):
    """Abstract class for a generalized encryption frame
    Our main importance is for our static methods which allow us
    to map key ids to identities, and IP addresses to key ids.
    The underlying C code then automatically creates the correct
    CryptFrame objects for outgoing packets.
    """

    NOTAKEY = AssimCtypes.NOTAKEY
    PUBLICKEY = AssimCtypes.PUBLICKEY
    PRIVATEKEY = AssimCtypes.PRIVATEKEY

    def __init__(self, destaddr=None, Cstruct=None):
        self._Cstruct = None
        if Cstruct is None and destaddr is None:
            raise ValueError("pyCryptFrame requires destaddr or Cstruct")
        if Cstruct is None:
            Cstruct = cryptframe_new_by_destaddr(destaddr._Cstruct)
        pyFrame.__init__(self, None, Cstruct=Cstruct)

    def receiver_id(self):
        """Return the key_id of the receiver key"""
        return u_string_at(self._Cstruct[0].receiver_key_id)

    @staticmethod
    def get_key_ids():
        """Returns the set of key ids that we know about"""
        keyidlist_int = cryptframe_get_key_ids()
        keyid_gslist = cast(keyidlist_int, cClass.GSList)
        keyid_list = []
        curkeyid = keyid_gslist
        while curkeyid:
            keyid_list.append(u_string_at(curkeyid[0].data))
            curkeyid = g_slist_next(curkeyid)
        g_slist_free(keyid_gslist)
        return keyid_list

    @staticmethod
    def get_cma_key_ids():
        """Return the set of CMA key ids we know about"""
        ret = []
        for keyid in pyCryptFrame.get_key_ids():
            if keyid.startswith(CMA_KEY_PREFIX):
                ret.append(keyid)
        return ret

    @staticmethod
    def associate_identity(identityname, key_id):
        """Associate the given identity name with the given key id
        This allows many keys to be associated with a single identity, but
        does not support a key being associated with multiple identities
        (which doesn't make sense anyway).
        """
        assert identityname is not None
        assert key_id is not None
        if not cryptframe_associate_identity(str(identityname), str(key_id)):
            raise ValueError("Problem with key id %s or identity %s" % (key_id, identityname))

    @staticmethod
    def get_identity(key_id: str):
        """Return the identity associated with the given key id"""
        assert key_id is not None
        cret: Optional[bytes] = cryptframe_whois_key_id(key_id.encode('utf-8'))
        if not cret:
            return None
        return cret.decode('utf-8')

    @staticmethod
    def get_dest_identity(destaddr: str) -> Optional[str]:
        """Return the identity associated with this pyNetAddr"""
        key_id = pyCryptFrame.get_dest_key_id(destaddr)
        if key_id is None:
            return None
        return pyCryptFrame.get_identity(key_id)

    @staticmethod
    def get_dest_key_id(destaddr: str) -> Optional[str]:
        """Return the key_id associated with this pyNetAddr"""
        cret: Optional[bytes] = cryptframe_get_dest_key_id(destaddr._Cstruct)
        if not cret:
            return None
        return cret.decode('utf-8')

    @staticmethod
    def dest_set_key_id(destaddr: str, key_id: str):
        """Set the public key we should use when talking to the given destination
        address (including port).
        """
        if not destaddr._Cstruct or key_id is None:
            raise ValueError("illegal parameters")
        if not cryptframe_set_dest_key_id(destaddr._Cstruct, key_id.encode('utf-8')):
            raise ValueError("Inappropriate key_id %s" % key_id)


# This is a bizarre and buggy complaint...
# AssimCclasses.py:1283: [R0904:pyCryptCurve25519] Too many public methods (21/20)
# pylint: disable=R0904
class pyCryptCurve25519(pyCryptFrame):
    """Encryption Frame based on Libsodium - Curve25519 public key encryption.
    Strangely enough, we may not actually use objects of this class - because it's
    effectively hidden by the C code from us having to know about it.

    Instead we just manage public keys, and map IP addresses to public keys
    and the C code under us takes care of the rest in terms of creating these objects.
    """

    def __init__(self, publickey_id=None, privatekey_id=None, Cstruct=None):
        self._Cstruct = None
        if Cstruct is None:
            Cstruct = cryptcurve25519_new(FRAMETYPE_CRYPTCURVE25519, publickey_id, privatekey_id, 0)
        pyCryptFrame.__init__(self, Cstruct=Cstruct)

    @staticmethod
    def key_id_to_filename(key_id, keytype):
        """Translate a key_id to a filename"""
        ret = curve25519_key_id_to_filename(key_id, keytype)
        pyret = u_string_at(ret.raw)
        g_free(ret.raw)
        return pyret

    @staticmethod
    def initkeys():
        """Initialize our set of persistent public keys / keypairs and get ready to encrypt.
        This involves several steps:
            1) Read in all available public and private keys
            2) If we have no CMA keys, then generate two keypairs and give instructions
                on hiding the second one...
            2) Figure out which private keys are ours and select which one (oldest) to use
               as our preferred signing key
            3) set the default signing method

            Note that there are still two issues that this doesn't deal with:
                Persisting the association between nanoprobe keys ids and (domain, hostname) pairs
                Assigning default IP addresses with nanoprobe key ids.
        """
        warnings = []
        cryptcurve25519_cache_all_keypairs()
        cma_ids = sorted(pyCryptFrame.get_cma_key_ids())
        if len(cma_ids) == 0:
            warnings.append("No CMA keys found. Generating two CMA key-pairs to start.")
            for keyid in (0, 1):
                print("Generating key id", keyid, file=stderr)
                cryptcurve25519_gen_persistent_keypair("%s%05d" % (CMA_KEY_PREFIX, keyid))
            cryptcurve25519_cache_all_keypairs()
            cma_ids = pyCryptFrame.get_cma_key_ids()
        elif len(cma_ids) == 1:
            lastkey = cma_ids[0]
            lastseqno = int(lastkey[len(CMA_KEY_PREFIX) :])
            newkeyid = "%s%05d" % (CMA_KEY_PREFIX, lastseqno + 1)
            warnings.append("Generating an additional CMA key-pair.")
            cryptcurve25519_gen_persistent_keypair(newkeyid)
            cryptcurve25519_cache_all_keypairs()
            cma_ids = pyCryptFrame.get_cma_key_ids()
        if len(cma_ids) != 2:
            warnings.append(
                "Unexpected number of CMA keys.  Expecting 2, but got %d." % len(cma_ids)
            )
        # We want to use the lowest-numbered private key we have access to.
        privatecount = 0
        extras = []
        for keyid in sorted(cma_ids):
            pyCryptFrame.associate_identity(CMA_IDENTITY_NAME, keyid)
            if cryptframe_private_key_by_id(keyid):
                privatecount += 1
                if privatecount == 1:
                    cryptframe_set_signing_key_id(keyid)
                else:
                    extras.append(keyid)
        if privatecount < 1:
            raise RuntimeError("FATAL: No CMA private keys to sign with!")
        if privatecount != 1:
            warnings.append(
                "Incorrect number of Private CMA keys.  Expecting 1, but got %d." % len(cma_ids)
            )
            warnings.append("YOU MUST SECURELY HIDE all but one private CMA key.")
            for keyid in extras:
                warnings.append(
                    "SECURELY HIDE *private* key %s"
                    % pyCryptCurve25519.key_id_to_filename(keyid, pyCryptFrame.PRIVATEKEY)
                )
        cryptcurve25519_set_encryption_method()
        return warnings


class pyFrameSet(pyAssimObj):
    """Class for Frame Sets - for collections of Frames making up a logical packet"""

    def __init__(self, framesettype, Cstruct=None):
        "Initializer for pyFrameSet"
        if Cstruct is None:
            Cstruct = frameset_new(framesettype)
        pyAssimObj.__init__(self, Cstruct=Cstruct)

    def append(self, frame):
        """Append a frame to the end of a @ref FrameSet"""
        frameset_append_frame(self._Cstruct, cast(frame._Cstruct, Frame_p))

    def prepend(self, frame):
        """Prepend a frame before the first frame in a @ref FrameSet"""
        frameset_prepend_frame(self._Cstruct, cast(frame._Cstruct, Frame_p))

    def construct_packet(self, signframe: pySignFrame,
                         cryptframe: Optional[pyCryptFrame] = None,
                         compressframe: Optional[pyCompressFrame] = None
                         ) -> None:
        """
        Construct packet from curent frameset + special prefix frames
        """
        cf = None
        cmpf = None
        if cryptframe is not None:
            cf = cryptframe._Cstruct
        if compressframe is not None:
            cmpf = compressframe._Cstruct
        frameset_construct_packet(self._Cstruct, signframe._Cstruct, cf, cmpf)

    def get_framesettype(self):
        """Return frameset type of this FrameSet"""
        return self._Cstruct[0].fstype

    def get_flags(self):
        """Return current flags for this FrameSet"""
        return frameset_get_flags(self._Cstruct)

    def set_flags(self, flags):
        """'OR' the given flags into the set of flags for this FrameSet"""
        return frameset_set_flags(self._Cstruct, int(flags))

    def clear_flags(self, flags):
        """Clear the given flags for this FrameSet"""
        return frameset_clear_flags(self._Cstruct, int(flags))

    def sender_key_id(self):
        """Return the key_id of the cryptographic sender of this FrameSet"""
        # print('TYPE(self)', type(self), 'str(self)', str(self), type(self._Cstruct), file=stderr)
        ret = frameset_sender_key_id(self._Cstruct)
        # print('sender_key_id: TYPE(ret)', type(ret), 'ret', ret,
        #         'raw', ret.raw, 'data', ret.data, file=stderr)
        # print('sender_key_id: str(ret)', str(ret), type(str(ret)), not ret, file=stderr)
        if not ret:
            # print('Returning None(!)', self.get_framesettype(), file=stderr)
            return None
        # print('SENDER_KEY_ID:', type(ret), ret, file=stderr)
        pyret = u_string_at(ret)
        # print('PYRET:', type(pyret), 'pyret:', pyret, file=stderr)
        return pyret

    def sender_identity(self):
        """Return the identity of the cryptographic sender of this FrameSet"""
        cret = frameset_sender_identity(self._Cstruct)
        if not cret:
            return None
        return str(cret)

    def dump(self):
        """Dump out the given frameset"""
        frameset_dump(self._Cstruct)

    def getpacket(self):
        """Return the constructed packet for this pyFrameSet"""
        if not self._Cstruct[0].packet:
            raise ValueError("No packet constructed for frameset")
        return (self._Cstruct[0].packet, self._Cstruct[0].pktend)

    def __len__(self):
        """Return the number of Frames in this pyFrameSet"""
        # This next statement OUGHT to work - and indeed it returns the right value
        # But somehow, 'self' doesn't get freed like it ought to :-(
        # BUG??
        # return g_slist_length(self._Cstruct[0].framelist)
        # So, let's do this instead...
        curframe = self._Cstruct[0].framelist
        count = 0
        while curframe:
            count += 1
            curframe = g_slist_next(curframe)
        return int(count)

    def __delitem__(self, key):
        """Fail - we don't implement this"""
        raise NotImplementedError("FrameSet does not implement __delitem__()")

    def __getitem__(self, key):
        """Fail - we don't implement this"""
        raise NotImplementedError("FrameSet does not implement __getitem__()")

    def __setitem__(self, key, value):
        """Fail - we don't implement this"""
        raise NotImplementedError("FrameSet does not implement __setitem__()")

    def iter(self):
        "Generator yielding the set of pyFrames in this pyFrameSet"
        curframe = self._Cstruct[0].framelist
        while curframe:
            cast(curframe[0].data, struct__GSList._fields_[0][1])
            yieldval = pyFrame.Cstruct2Frame(cast(curframe[0].data, cClass.Frame))
            # print(("Constructed frame IS [%s]" % str(yieldval)), file=stderr)
            if not yieldval.isvalid():
                print(
                    "OOPS! Constructed %d byte frame from iter() is not valid [%s]"
                    % (yieldval.framelen(), str(yieldval)),
                    file=stderr,
                )
                raise ValueError(
                    "Constructed %d byte frame from iter() is not valid [%s]"
                    % (yieldval.framelen(), str(yieldval))
                )
            # print "Yielding:", str(yieldval), "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"
            yield yieldval
            curframe = g_slist_next(curframe)

    def fstypestr(self):
        """Return the frameset type name as a string"""
        return FrameSetTypes.get(self.get_framesettype())[0]

    def __str__(self):
        """Convert this pyFrameSet to a String"""
        result = "%s:{" % self.fstypestr()
        comma = ""
        for frame in self.iter():
            result += "%s[%d]%s" % (comma, frame.framelen(), str(frame))
            comma = ", "
        result += "}"
        return result

    def to_bytearray_packet(self,
                            sign_frame: Optional[pySignFrame] = None,
                            crypt_frame: Optional[pyCryptFrame] = None,
                            compress_frame: Optional[pyCompressFrame] = None,
                            ) -> bytes:
        """
        Return the bytearray representation of this packet, suitable for pickling

        :param sign_frame: Optional[pySignFrame]: signature frame -- or None
        :param crypt_frame: Optional[pyCryptFrame]: encryption frame -- or None
        :param compress_frame: Optional[pyCompressFrame]: compression frame -- or None
        """
        if not sign_frame:
            sign_frame = pySignFrame(1)

        self.construct_packet(sign_frame, crypt_frame, compress_frame)
        first, last = self.getpacket()
        # Create a Ctypes type for this particular length of packet
        fs_ctype_type = ctypes.c_ubyte * (last - first)
        return bytearray(fs_ctype_type.from_address(first))




class pyPacketDecoder(pyAssimObj):
    """Class for Decoding packets - for returning an array of FrameSets from a physical packet."""

    def __init__(self, Cstruct=None):
        """Initializer for pyPacketDecoder"""
        if Cstruct is None:
            Cstruct = packetdecoder_new(0, None, 0)
        pyAssimObj.__init__(self, Cstruct=Cstruct)

    def fslist_from_pktdata(self, pktlocation: Tuple[int, int]) -> List[pyFrameSet]:
        """Make a list of FrameSets out of a packet."""
        base = self._Cstruct[0]
        while not_this_exact_type(base, AssimCtypes.PacketDecoder):
            base = base.baseclass
        fs_gslistint = base.pktdata_to_framesetlist(
            self._Cstruct, cast(pktlocation[0], cClass.guint8), cast(pktlocation[1], cClass.guint8)
        )
        # fslist_to_pyfs_array() disposes of the s_list, while keeping the framesets
        return pyPacketDecoder.fslist_to_pyfs_array(fs_gslistint)

    @staticmethod
    def fslist_to_pyfs_array(listheadint) -> List[pyFrameSet]:
        """
        Converts a GSList of FrameSets to a python array of pyFrameSets
        It frees the FrameSetList (GSList) it is passed as a parameter using g_slist_free().
        This does _not_ free the objects pointed to by the list (and this is a good thing)
        https://developer.gnome.org/glib/stable/glib-Singly-Linked-Lists.html#g-slist-free

        The docs allude to a case where the list head might be dangling. I don't _think_
        that this is our case (?).
        """
        fs_gslist = cast(listheadint, cClass.GSList)
        frameset_list: List[pyFrameSet] = []
        curfs = fs_gslist
        while curfs:
            cfs = cast(curfs[0].data, cClass.FrameSet)
            fs = pyFrameSet(None, Cstruct=cfs)
            frameset_list.append(fs)
            curfs = g_slist_next(curfs)
        g_slist_free(fs_gslist)
        return frameset_list

    @staticmethod
    def pickle_packet(frameset_list: Union[List[pyFrameSet], int],
                      sign: Optional[pySignFrame] = None,
                      crypt: Optional[pyCryptFrame] = None,
                      compress: Optional[pyCompressFrame] = None,
                      ) -> bytes:
        """
        Convert a frameset list into a pickled packet - since FrameSets aren't directly pickleable.
        A pyFrameSet is a logical packet, and a "packet" is a physical packet, which consists
        of one or more Framesets headed to the same destination at the same time.

        To do this we construct a packet from the frameset list, then pickle the resulting
        packet.

        NOTE: PICKLING/UNPICKLING IS POTENTIALLY DANGEROUS - ONLY UNPICKLE FROM TRUSTED SOURCES

        :param frameset_list: int: A list of Framesets or an int that points to a 'C' FrameSetList
        :param sign: Optional[pySignFrame]: signature frame -- or None
        :param crypt: Optional[pyCryptFrame]: encryption frame -- or None
        :param compress: Optional[pyCompressFrame]: compression frame -- or None
        :return:bytes: A pickled packet which is structured like this:
            List[bytearray]
            where each bytearray represents a single packetized FrameSet (logical packet)
        """
        if isinstance(frameset_list, int):
            decoder = pyPacketDecoder()
            frameset_list = decoder.fslist_to_pyfs_array(frameset_list)

        frameset_buf_list = [fs.to_bytearray_packet(sign, crypt, compress) for fs in frameset_list]
        return pickle.dumps(frameset_buf_list)

    def unpickle_packet(self, pickled_packet: bytes) -> List[pyFrameSet]:
        """
        Convert a pickled packet from pickle_packet() back into a list of pyFrameSets.
        NOTE: PICKLING/UNPICKLING IS POTENTIALLY DANGEROUS - ONLY UNPICKLE FROM TRUSTED SOURCES

        :param pickled_packet: bytes: pickled Packet
        :return: List[pyFrameSet]: List of framesets from the packet
        """
        frameset_list: List[pyFrameSet] = []
        frameset_buf_list = pickle.loads(pickled_packet)

        if not isinstance(frameset_buf_list, list):
            raise ValueError(f"Pickled packet not a list: {type(frameset_buf_list)}")
        for frameset_buf in frameset_buf_list:
            if not isinstance(frameset_buf, bytearray):
                raise ValueError(f"Pickled packet not a collection of bytearrays: "
                                 f"{type(frameset_buf)}")
            # Construct a Ctypes type for this particular FrameSet
            packet_type = ctypes.c_ubyte * len(frameset_buf)
            packet = packet_type.from_buffer(frameset_buf)
            first = int(ctypes.addressof(packet))
            last = first + len(frameset_buf)
            decoder = pyPacketDecoder()
            # Extract a frameset list from our "packet data"
            fs_list = self.fslist_from_pktdata((first, last))
            # There should only be a single frameset in this chunk...
            if len(fs_list) != 1:
                raise ValueError(f"Pickled FrameSetList length is incorrect {len(fs_list)}")
            for fs in fs_list:
                if not isinstance(fs, pyFrameSet):
                    raise ValueError(f"Pickled FrameSet incorrect type {type(fs)}")
                frameset_list.append(fs)
        return frameset_list


# R0904: Too many public methods
# pylint: disable=R0904
class pyConfigContext(pyAssimObj):
    """Class for Holding configuration information - now a general JSON-compatible data bag"""

    def __init__(self, init=None, filename=None, Cstruct=None):
        "Initializer for pyConfigContext"
        self._Cstruct = None  # Keep error legs from complaining.
        if not Cstruct:
            # Cstruct overrides init and filename
            if filename is not None:
                f = open(filename, "r")
                # filename overrides init
                init = f.read()
                f.close()
            if isinstance(init, six.string_types):
                Cstruct = configcontext_new_JSON_string(str(init))
                if not Cstruct:
                    raise ValueError("Bad JSON [%s]" % str(init))
                init = None
            else:
                Cstruct = configcontext_new(0)
        pyAssimObj.__init__(self, Cstruct=Cstruct)
        if init is not None:
            for key in list(init.keys()):
                self[key] = init[key]

    def getint(self, name):
        """Return the integer associated with "name\""""
        return self._Cstruct[0].getint(self._Cstruct, name)

    def setint(self, name, value):
        """Set the integer associated with "name\""""
        self._Cstruct[0].setint(self._Cstruct, name, value)

    def getbool(self, name):
        """Return the boolean associated with "name\""""
        return self._Cstruct[0].getbool(self._Cstruct, name) != 0

    def setbool(self, name, value):
        """Set the boolean associated with "name\""""
        self._Cstruct[0].setbool(self._Cstruct, name, bool(value))

    def getfloat(self, name):
        """Return the floating point value associated with "name\""""
        return self._Cstruct[0].getdouble(self._Cstruct, name)

    def setfloat(self, name, value):
        """Set the floating point value associated with "name\""""
        self._Cstruct[0].setdouble(self._Cstruct, name, float(value))

    def getaddr(self, name):
        """Return the NetAddr associated with "name\""""
        naddr = self._Cstruct[0].getaddr(self._Cstruct, name)
        if naddr:
            naddr = cast(naddr, cClass.NetAddr)
            # We're creating a new reference to the pre-existing NetAddr
            CCref(naddr)
            gotten_addr = pyNetAddr(None, Cstruct=naddr)
            print(f"CCref of NetAddr {gotten_addr}")
            return gotten_addr
        raise IndexError("No such NetAddr value [%s]" % name)

    def setaddr(self, name, value):
        """Set the @ref NetAddr associated with "name\""""
        self._Cstruct[0].setaddr(self._Cstruct, name, value._Cstruct)

    def getframe(self, name):
        """Return the Frame associated with "name\""""
        faddr = self._Cstruct[0].getframe(self._Cstruct, name)
        if faddr:
            # Cstruct2Frame already calls CCref()
            return pyFrame.Cstruct2Frame(faddr)
        raise IndexError("No such Frame value [%s]" % name)

    def setframe(self, name, value):
        """Set the @ref Frame associated with "name\""""
        self._Cstruct[0].setframe(self._Cstruct, name, cast(value._Cstruct, Frame_p))

    def getconfig(self, name):
        """Return the pyConfigContext object associated with "name\""""
        caddr = self._Cstruct[0].getconfig(self._Cstruct, name)
        if caddr:
            caddr = cast(caddr, cClass.ConfigContext)
            # We're creating a new reference to the pre-existing NetAddr
            CCref(caddr)
            return pyConfigContext(Cstruct=caddr)
        raise IndexError("No such ConfigContext value [%s]" % name)

    def setconfig(self, name, value):
        """Set the @ref ConfigContext associated with "name\""""
        self._Cstruct[0].setconfig(self._Cstruct, name, value._Cstruct)

    def getstring(self, name):
        """Return the string associated with "name\""""
        ret = self._Cstruct[0].getstring(self._Cstruct, name)
        if ret is not None:
            assert not isinstance(u_string_at(ret), bytes)
            return u_string_at(ret)
        raise IndexError("No such String value [%s]" % name)

    def setstring(self, name, value):
        """Set the string associated with "name\""""
        self._Cstruct[0].setstring(self._Cstruct, name, value)

    def getarray(self, name):
        """Return the array value associated with 'name' """
        curlist = cast(self._Cstruct[0].getarray(self._Cstruct, name), cClass.GSList)
        # print("CURLIST(initial) = %s" % curlist, file=stderr)
        ret = []
        while curlist:
            # print("CURLIST = %s" % curlist, file=stderr)
            # cfgval = pyConfigValue(cast(cClass.ConfigValue, curlist[0].data).get())
            data = cast(curlist[0].data, cClass.ConfigValue)
            # print("CURLIST->data = %s" % data, file=stderr)
            CCref(data)
            cfgval = pyConfigValue(data).get()
            if isinstance(cfgval, pyNetAddr):
                cfgval = str(cfgval)  # Work around an issue in object lifetime
            ret.append(cfgval.encode("utf8") if isinstance(cfgval, bytes) else cfgval)
            curlist = g_slist_next(curlist)
        return ret

    def setarray(self, name, value):
        """Set a ConfigContext key value to be a sequence of values from an iterable"""
        self._Cstruct[0].setarray(self._Cstruct, name, None)
        for elem in value:
            if isinstance(elem, bool):
                self._Cstruct[0].appendbool(self._Cstruct, name, elem)
                continue
            if isinstance(elem, int):
                self._Cstruct[0].appendint(self._Cstruct, name, elem)
                continue
            if isinstance(elem, float):
                self._Cstruct[0].appendfloat(self._Cstruct, name, elem)
                continue
            if isinstance(elem, str):
                self._Cstruct[0].appendstring(self._Cstruct, name, elem)
                continue
            if isinstance(elem, pyNetAddr):
                self._Cstruct[0].appendaddr(self._Cstruct, name, elem)
                continue
            if isinstance(elem, pyConfigContext):
                self._Cstruct[0].appendconfig(self._Cstruct, name, elem._Cstruct)
                continue
            if isinstance(elem, dict):
                cfgctx = pyConfigContext.from_dict(elem)
                self._Cstruct[0].appendconfig(self._Cstruct, name, cfgctx._Cstruct)
                continue
            raise ValueError("Cannot append/include array elements of type %s" % type(elem))

    @staticmethod
    def from_dict(dictval):
        """Construct a pyConfigContext from a dict-like object"""
        newobj = pyConfigContext()
        for key in list(dictval.keys()):
            keyval = dictval[key]
            if hasattr(keyval, "keys"):
                keyval = pyConfigContext.from_dict(dictval[key])
            newobj[key] = dictval[key]
        return newobj

    def keys(self):
        """Return the set of keys for this object"""
        l = []
        keylist = cast(self._Cstruct[0].keys(self._Cstruct), POINTER(GSList))
        curkey = keylist
        while curkey:
            l.append(u_string_at(curkey[0].data))
            curkey = g_slist_next(curkey)
        g_slist_free(keylist)
        return l

    def __iter__(self):
        """Iterate over self.keys()"""
        for key in self.keys():
            yield key

    def items(self):
        """
        Iterate over the (key, value) pairs in the top level dict-like structure
        :yield: (str(key), value)
        """
        for key in self.keys():
            yield key, self.get(key)

    def gettype(self, name):
        """Return the enumeration type of this particular key
        @todo Convert these enums to python types"""
        # print('gettype(%s)' % str(name), file=stderr)
        return self._Cstruct[0].gettype(self._Cstruct, str(name))

    def get(self, key, alternative=None):
        """return value if object contains the given key - 'alternative' if not"""
        if self._Cstruct[0].gettype(self._Cstruct, str(key)) == CFG_EEXIST:
            return alternative
        return self[key]

    # pylint R0911: too many returns (9)
    # pylint: disable=R0911
    def deepget(self, key, alternative=None):
        """return value if object contains the given *structured* key - 'alternative' if not"""
        try:
            (prefix, suffix) = key.split(".", 1)
        except ValueError:
            suffix = None
            prefix = key
        print(f"prefix {prefix} suffix {suffix}")
        if prefix not in self:
            print(f"prefix {prefix} NOT IN self {self}")
            # Note that very similar code exists in GraphNodes get member function
            if not prefix.endswith("]"):
                return alternative
            else:
                # Looks like we have an array index
                proper = prefix[0 : len(prefix) - 1]
                try:
                    (preprefix, idx) = proper.split("[", 1)
                    print(f"preprefix {preprefix} idx {idx}")
                except ValueError:
                    return alternative
                print(f"preprefix in self? {preprefix in self}")
                if preprefix not in self:
                    return alternative
                try:
                    array = self[preprefix]
                    idx = int(idx)  # Possible ValueError
                    print(f"ARRAY IS {type(array)}, {array}", file=stderr)
                    print(f"INDEX IS {idx}", file=stderr)
                    value = array[idx]  # possible IndexError or TypeError
                    assert not isinstance(value, bytes)
                    if suffix is None:
                        assert not isinstance(value, bytes)
                        return value
                except (TypeError, IndexError, ValueError):
                    return alternative
                return value.deepget(suffix, alternative)

        print(f"prefix {prefix} IN self {self}")
        prefixvalue = self[prefix]
        assert not isinstance(prefixvalue, bytes)
        if suffix is None:
            return prefixvalue
        if not isinstance(prefixvalue, pyConfigContext):
            return alternative
        gotten = prefixvalue.deepget(suffix, alternative)
        assert not isinstance(gotten, bytes)
        return gotten

    def has_key(self, key):
        """return True if it has the given key"""
        return self.__contains__(key)

    def __contains__(self, key):
        """return True if our object contains the given key"""
        ktype = self._Cstruct[0].gettype(self._Cstruct, str(key))
        return ktype != CFG_EEXIST

    def __len__(self):
        """Return the number of items in this pyConfigContext"""
        keylist = cast(self._Cstruct[0].keys(self._Cstruct), POINTER(GSList))
        llen = g_slist_length(keylist)
        g_slist_free(keylist)
        return llen

    def __delitem__(self, key):
        """Delete the given item"""
        self._Cstruct[0].delkey(self._Cstruct, str(key))

    def __getitem__(self, name):
        """Return a value associated with "name\""""
        name = str(name)
        ktype = self.gettype(name)
        # print('*********** GETITEM[%s] => %d *********************' % (name, ktype), file=stderr)
        if ktype == CFG_EEXIST:
            traceback.print_stack()
            raise IndexError("No such value [%s] in [%s]" % (name, str(self)))
        elif ktype == CFG_CFGCTX:
            return self.getconfig(name)
        elif ktype == CFG_STRING:
            return self.getstring(name)
        elif ktype == CFG_NETADDR:
            return self.getaddr(name)
        elif ktype == CFG_FRAME:
            return self.getframe(name)
        elif ktype == CFG_INT64:
            return self.getint(name)
        elif ktype == CFG_FLOAT:
            return self.getfloat(name)
        elif ktype == CFG_BOOL:
            return self.getbool(name)
        elif ktype == CFG_ARRAY:
            # print('*********** GETITEM[%s] => getarray(%s) *********************' \, file=stderr)
            #   %   (name, name)
            return self.getarray(name)
        return None

    def __setitem__(self, name, value):
        """Set a value associated with "name" - in the appropriate table"""
        if isinstance(value, six.string_types):
            return self.setstring(name, str(value))
        if isinstance(value, pyNetAddr):
            return self.setaddr(name, value)
        if isinstance(value, pyFrame):
            return self.setframe(name, value)
        if isinstance(value, pyConfigContext):
            return self.setconfig(name, value)
        if isinstance(value, dict):
            return self.setconfig(name, pyConfigContext(value))
        if isinstance(value, (list, tuple)) or hasattr(value, "__iter__"):
            return self.setarray(name, value)
        if isinstance(value, float):
            return self.setfloat(name, value)
        if isinstance(value, dict):
            return self.setconfig(name, pyConfigContext.from_dict(value))
        if isinstance(value, bool):
            return self.setbool(name, value)
        self.setint(name, int(value))


class pyConfigValue(pyAssimObj):
    """A Python wrapper for a C implementation of something like a Python Dictionary"""

    def __init__(self, Cstruct):
        """Initializer for pyConfigValue - now a subclass of pyAssimObj"""
        pyAssimObj.__init__(self, Cstruct=Cstruct)

    def __str__(self):
        """Convert the given pyConfigValue to a String"""
        str(self.get())

    # Too many returns
    # pylint: disable=R0911
    def get(self):
        """Return the value of this object"""
        ret = None
        vtype = self._Cstruct[0].valtype
        if vtype == CFG_BOOL:
            return self._Cstruct[0].u.intvalue != 0
        elif vtype == CFG_INT64:
            return int(self._Cstruct[0].u.intvalue)
        elif vtype == CFG_STRING:
            strval = self._Cstruct[0].u.strvalue
            value = strval.data.decode("utf8") if isinstance(strval, String) else strval
            assert isinstance(value, str)
            return value
            # return u_string_at(self._Cstruct[0].u.strvalue)
            return str(self._Cstruct[0].u.strvalue)
        elif vtype == CFG_FLOAT:
            return float(self._Cstruct[0].u.floatvalue)
        elif vtype == CFG_CFGCTX:
            # We're creating a new reference to the pre-existing ConfigContext value
            CCref(self._Cstruct[0].u.cfgctxvalue)
            return pyConfigContext(Cstruct=self._Cstruct[0].u.cfgctxvalue)
        elif vtype == CFG_NETADDR:
            net = pyNetAddr(None, Cstruct=self._Cstruct[0].u.addrvalue)
            # We're creating a new reference to the pre-existing NetAddr
            CCref(net._Cstruct)
            return net
        elif vtype == CFG_FRAME:
            #       Cstruct2Frame calls CCref() - so we don't need to
            return pyFrame.Cstruct2Frame(self._Cstruct[0].u.framevalue)
        elif vtype == CFG_ARRAY:
            # An Array is a linked list (GSList) of ConfigValue objects...
            ret = []
            this = self._Cstruct[0].u.arrayvalue
            while this:
                dataptr = cast(this[0].data, struct__GSList._fields_[0][1])
                dataptr = cast(dataptr, cClass.ConfigValue)
                CCref(dataptr)
                thisobj = pyConfigValue(cast(dataptr, cClass.ConfigValue)).get()
                ret.append(thisobj)
                this = g_slist_next(this)
            return ret
        elif vtype == CFG_NULL:
            return None
        raise ValueError("Invalid valtype (%s)in pyConfigValue object" % self._Cstruct.valtype)


class pyNetIO(pyAssimObj):
    """A Network I/O object - with a variety of subclasses"""

    CONN_NONE = 0  # FSPR_NONE  -- Apparently ctypesgen doesn't do enum values...
    CONN_INIT = 1  # FSPR_INIT
    CONN_UP = 2  # FSPR_UP
    CONN_SHUT1 = 3  # FSPR_SHUT1
    CONN_SHUT2 = 4  # FSPR_SHUT2
    CONN_SHUT3 = 5  # FSPR_SHUT3

    def __init__(self, configobj, packetdecoder, Cstruct=None):
        """Initializer for pyNetIO"""
        self._Cstruct = None  # Keep error legs from complaining.
        if Cstruct is None:
            Cstruct = netio_new(0, configobj._Cstruct, packetdecoder._Cstruct)
            self.config = configobj
        else:
            self._Cstruct = Cstruct
            base = self._Cstruct[0]
            while not hasattr(base, "_configinfo"):
                base = base.baseclass
            self.config = pyConfigContext(Cstruct=base._configinfo)
            CCref(base._configinfo)
        pyAssimObj.__init__(self, Cstruct=cast(Cstruct, NetIO_p))

    def setup_config(self, bind_addr_str: str) -> None:
        bind_addr = pyNetAddr(bind_addr_str)
        if not self.bindaddr(bind_addr):
            raise NameError(f"Cannot bind to address {bind_addr}")
        if not self.mcastjoin(pyNetAddr(CMAADDR)):
            print(f"WARNING: Failed to join multicast at {CMAADDR}", file=stderr)
        self.setblockio(False)

    def setblockio(self, mode):
        """Set this NetIO object to blocking IO mode"""
        base = self._Cstruct[0]
        while not hasattr(base, "setblockio"):
            base = base.baseclass
        return base.setblockio(self._Cstruct, int(mode))

    def fileno(self):
        """Return the file descriptor for this pyNetIO object"""
        base = self._Cstruct[0]
        while not hasattr(base, "getfd"):
            base = base.baseclass
        return base.getfd(self._Cstruct)

    def bindaddr(self, addr, silent=False):
        """Bind the socket underneath this NetIO object to the given address"""
        base = self._Cstruct[0]
        while not hasattr(base, "bindaddr"):
            base = base.baseclass
        return base.bindaddr(self._Cstruct, addr._Cstruct, silent)

    def boundaddr(self):
        """Return the socket underlying this NetIO object"""
        base = self._Cstruct[0]
        while not hasattr(base, "bindaddr"):
            base = base.baseclass
        boundaddr = base.boundaddr(self._Cstruct)
        # We're creating a new reference to the pre-existing NetAddr
        ret = pyNetAddr(None, Cstruct=boundaddr)
        CCref(boundaddr)
        return ret

    def getrcvbufsize(self):
        """Return the receive buffer size for this socket"""
        base = self._Cstruct[0]
        while not hasattr(base, "getsockbufsize"):
            base = base.baseclass
        return base.getsockbufsize(self._Cstruct, True)

    def setrcvbufsize(self, bufsize):
        """Set and return the receive buffer size for this socket"""
        base = self._Cstruct[0]
        while not hasattr(base, "setsockbufsize"):
            base = base.baseclass
        return base.setsockbufsize(self._Cstruct, True, bufsize)

    def getsendbufsize(self):
        """Return the output buffer size for this socket"""
        base = self._Cstruct[0]
        while not hasattr(base, "getsockbufsize"):
            base = base.baseclass
        return base.getsockbufsize(self._Cstruct, False)

    def setsendbufsize(self, bufsize):
        """Return the output buffer size for this socket"""
        base = self._Cstruct[0]
        while not hasattr(base, "setsockbufsize"):
            base = base.baseclass
        return base.setsockbufsize(self._Cstruct, False, bufsize)

    def mcastjoin(self, addr):
        """Join the underlying socket to the given multicast address"""
        base = self._Cstruct[0]
        while not hasattr(base, "mcastjoin"):
            base = base.baseclass
        return base.mcastjoin(self._Cstruct, addr._Cstruct, None)

    def getmaxpktsize(self):
        """Return the max packet size for this pyNetIO"""
        base = self._Cstruct[0]
        while not hasattr(base, "getmaxpktsize"):
            base = base.baseclass
        return base.getmaxpktsize(self._Cstruct)

    def setmaxpktsize(self, size):
        """Set the max packet size for this pyNetIO"""
        base = self._Cstruct[0]
        while not hasattr(base, "setmaxpktsize"):
            base = base.baseclass
        return base.setmaxpktsize(self._Cstruct, int(size))

    def compressframe(self):
        """Return the compression frame for this pyNetIO - may be None"""
        # Doesn't make a py class object out of it yet...
        base = self._Cstruct[0]
        while not hasattr(base, "compressframe"):
            base = base.baseclass
        return base.compressframe(self._Cstruct)

    def signframe(self):
        """Return the digital signature frame for this pyNetIO"""
        base = self._Cstruct[0]
        while not hasattr(base, "signframe"):
            base = base.baseclass
        return pySignFrame(0, Cstruct=cast(base.signframe(self._Cstruct), cClass.SignFrame))

    def sendframesets(self, destaddr, framesetlist):
        """Send the (collection of) frameset(s) out on this pyNetIO"""
        if destaddr.port() == 0:
            raise ValueError("Zero Port in sendframesets: destaddr=%s" % str(destaddr))
        if not isinstance(framesetlist, collections.abc.Sequence):
            framesetlist = (framesetlist,)
        base = self._Cstruct[0]
        while not hasattr(base, "sendaframeset"):
            base = base.baseclass
        # We ought to eventually construct a GSList of them and then call sendframesets
        # But this is easy for now...
        for frameset in framesetlist:
            base.sendaframeset(self._Cstruct, destaddr._Cstruct, frameset._Cstruct)

    def sendreliablefs(self, destaddr, framesetlist, qid=DEFAULT_FSP_QID):
        """Reliably send the (collection of) frameset(s) out on this pyNetIO (if possible)"""
        if destaddr.port() == 0:
            raise ValueError("Zero Port in sendreliablefs: destaddr=%s" % str(destaddr))
        if not isinstance(framesetlist, collections.abc.Sequence):
            framesetlist = (framesetlist,)
        base = self._Cstruct[0]
        while not hasattr(base, "sendaframeset"):
            base = base.baseclass
        for frameset in framesetlist:
            success = base.sendareliablefs(
                self._Cstruct, cast(destaddr._Cstruct, cClass.NetAddr), qid, frameset._Cstruct
            )
            if not success:
                raise IOError("sendareliablefs(%s, %s) failed." % (destaddr, frameset))

    def ackmessage(self, destaddr, frameset):
        """ACK (acknowledge) this frameset - (presumably sent reliably)."""

        base = self._Cstruct[0]
        while not hasattr(base, "ackmessage"):
            base = base.baseclass
        base.ackmessage(self._Cstruct, destaddr._Cstruct, frameset._Cstruct)

    def closeconn(self, qid, destaddr):
        """Close (reset) our connection to this address"""
        base = self._Cstruct[0]
        while not hasattr(base, "closeconn"):
            base = base.baseclass
        print("RESETTING CONNECTION (closeconn) TO %s" % str(destaddr), file=stderr)
        base.closeconn(self._Cstruct, qid, destaddr._Cstruct)

    def addalias(self, fromaddr, toaddr):
        """Close (reset) our connection to this address"""

        base = self._Cstruct[0]
        while not hasattr(base, "addalias"):
            base = base.baseclass
        base.addalias(self._Cstruct, fromaddr._Cstruct, toaddr._Cstruct)

    def recvframesets(self):
        """Receive a collection of framesets read from this pyNetIO - all from the same Address.
         @return The return value is a tuple (address, framesetlist). """
        # GSList * 	_netio_recvframesets (NetIO *self,NetAddr **src)

        base = self._Cstruct[0]
        while not hasattr(base, "recvframesets"):
            base = base.baseclass
        # Create a dummy IPaddr "shell"
        netaddrint = netaddr_ipv4_new(create_string_buffer(4), 101)
        netaddr = cast(netaddrint, cClass.NetAddr)
        netaddr[0].baseclass.unref(netaddr)  # We're about to replace it...
        # Basically we needed a pointer to pass, and this seemed like a good way to do it...
        # Maybe it was -- maybe it wasn't...  It's a pretty expensive way to get this effect...
        fs_gslistint = base.recvframesets(self._Cstruct, byref(netaddr))
        # recvframesets gave us that 'netaddr' for us to dispose of - there are no other refs
        # to it so we should NOT 'CCref' it.  It's a new object - not a pointer to an old one.
        # fslist_to_pyfs_array will dispose of the underlying frameset list.
        # The underlying frames themselves will not be freed - they wind up
        # being pointed to by the result of fslist_to_pyfs_array...
        fslist = pyPacketDecoder.fslist_to_pyfs_array(fs_gslistint)
        if netaddr and len(fslist) > 0:
            address = pyNetAddr(None, Cstruct=netaddr)
        else:
            address = None
        return (address, fslist)

    @staticmethod
    def is_dual_ipv4v6_stack():
        """Return True if our OS supports a dual IPv4/IPv6 stack"""
        return netio_is_dual_ipv4v6_stack()


class pyNetIOudp(pyNetIO):
    """UDP version of the pyNetIO abstract base class"""

    def __init__(self, config, packetdecoder, Cstruct=None):
        """Initializer for pyNetIOudp"""
        self._Cstruct = None  # Keep error legs from complaining.
        if Cstruct is None:
            Cstruct = netioudp_new(0, config._Cstruct, packetdecoder._Cstruct)
        if not Cstruct:
            raise ValueError("Invalid parameters to pyNetIOudp constructor")
        pyNetIO.__init__(self, config, packetdecoder, Cstruct=Cstruct)


class pyReliableUDP(pyNetIOudp):
    """Reliable UDP version of the pyNetIOudp abstract base class"""

    def __init__(self, config, packetdecoder, rexmit_timer_uS=0, Cstruct=None):
        """Initializer for pyReliableUDP"""
        self._Cstruct = None  # Keep error legs from complaining.
        if Cstruct is None:
            Cstruct = reliableudp_new(0, config._Cstruct, packetdecoder._Cstruct, rexmit_timer_uS)
        else:
            print(f"Relable__init__ from parameter: {Cstruct}", file=stderr)
        if not Cstruct:
            raise ValueError("Invalid parameters to pyReliableUDP constructor")
        pyNetIOudp.__init__(self, config, packetdecoder, Cstruct=Cstruct)
        #
        # At this point NetIO will have cast self._Cstruct as a NetIO object
        # because most of the calls are NetIO calls. The few that are unique to
        # ReliableUDP have to cast their arguments as ReliableUDP
        #
        print(f"Reliable__init__: CLASS OF {self._Cstruct} BASE: {type(self._Cstruct)}",
              file=stderr)

    def log_conn(self, destaddr, qid=DEFAULT_FSP_QID):
        """Log connection status/info to system logs"""
        cstruct = cast(self._Cstruct, ReliableUDP_p)
        cstruct[0].log_conn(cstruct, qid, destaddr._Cstruct)

    def connstate(self, peeraddr, qid=DEFAULT_FSP_QID):
        """Return the state of this connection - return value is one of the pyNetIO constants"""
        fsproto = cast(self._Cstruct, ReliableUDP_p)[0]._protocol
        return fsproto[0].connstate(fsproto, qid, peeraddr._Cstruct)

    def connactive(self, peeraddr, qid=DEFAULT_FSP_QID):
        """Return TRUE if this connection is active.
        That is, if it's established and not in shutdown.
        Note that the presence of timeouts doesn't make a connection inactive.
        We can time out for days and still think the connection is active.
        """
        connstate = self.connstate(peeraddr, qid)
        return connstate == pyNetIO.CONN_INIT or connstate == pyNetIO.CONN_UP


class CMAlib(object):
    """Miscellaneous functions to create certain useful pyFrameSets"""

    def __init__(self):
        """Do-nothing init function"""
        pass

    @staticmethod
    def create_setconfig(cfg):
        """Create a setconfig FrameSet"""
        fs = cast(create_setconfig(cfg._Cstruct), cClass.FrameSet)
        return pyFrameSet(None, Cstruct=fs)

    @staticmethod
    def create_sendexpecthb(cfg, msgtype, address):
        """Create a Send/Expect heartbeat FrameSet"""
        ucfs = create_sendexpecthb(cfg._Cstruct, int(msgtype), address._Cstruct, 1)
        fs = cast(ucfs, cClass.FrameSet)
        return pyFrameSet(None, Cstruct=fs)


class pyPcapCapture(object):
    """Class to read binary packets from pcap packet  capture files"""

    def __init__(self, filename):
        print("READING PCAP CAPTURE FILE", filename, file=stderr)
        self._Cstruct = pcap_capture_iter_new(filename)
        if not self._Cstruct:
            raise ValueError("Invalid parameters to pyPcapCapture constructor")
        # I'm saving this here because for some unclear reason it goes to None...
        self.destructor = pcap_capture_iter_del

    def __del__(self):
        """Clean up our pcap capture file descriptor"""
        if self._Cstruct:
            self.destructor(self._Cstruct)
            self._Cstruct = None

    def __iter__(self):
        pktlen = c_uint()
        pktend = cClass.guint8()
        ret = pcap_capture_iter_next(self._Cstruct, byref(pktend), byref(pktlen))
        if not ret:
            self.destructor(self._Cstruct)
            self._Cstruct = None
            return
        yield (cast(ret, cClass.guint8), pktend, int(pktlen.value))


def dump_c_objects():
    """Dump out live objects to help locate memory leaks"""
    print("GC Garbage: [%s]" % str(gc.garbage), file=stderr)
    print("***************LOOKING FOR pyAssimObjs***********", file=stderr)
    get_referrers = True
    cobjcount = 0
    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, (pyAssimObj, pyCstringFrame)):
            cobjcount += 1
            cobj = "None"
            if hasattr(obj, "_Cstruct") and obj._Cstruct is not None:
                cobj = "0x%x" % addressof(getattr(obj, "_Cstruct")[0])
            print(
                "FOUND C object class(%s): %s -> %s"
                % (obj.__class__.__name__, str(obj)[:512], cobj),
                file=stderr,
            )
            if get_referrers:
                follow_referrer_back(obj)

    print(
        "%d python wrappers referring to %d C-objects"
        % (cobjcount, proj_class_live_object_count()),
        file=stderr,
    )
    proj_class_dump_live_objects()


def follow_referrer_back(obj, level=0, maxlevel=4):
    """Follow and print object referrer chains back through "maxlevel" levels"""
    print("++++%sREFERRERS" % (level * "**"), file=stderr)
    for referrer in gc.get_referrers(obj):
        if isinstance(referrer, (list, types.FrameType)):
            continue
        print(
            "++++%sReferred to by(%s): %s" % (level * "**", type(referrer), str(referrer)[:512]),
            file=stderr,
        )
        if level < maxlevel:
            follow_referrer_back(referrer, level + 1)


if __name__ == "__main__":

    def test_pcap_captures():
        """Code to minimally exercise the pyPcapCapture class"""
        for f in ("../pcap/cdp_v2.pcap", "../pcap/lldp.detailed.pcap"):
            print("Capture file: %s" % f)
            capture = pyPcapCapture(f)
            for results in capture:
                (pkt, pktend, pktlen) = results
                print("Pkt", pkt, "pktend", pktend, "pktlen", pktlen)

    test_pcap_captures()
