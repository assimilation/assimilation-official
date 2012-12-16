#!/usr/bin/python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab
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
'''
A collection of classes which wrap our @ref C-Classes and provide Pythonic interfaces to these C-classes.
'''

from AssimCtypes import *
from frameinfo import FrameTypes, FrameSetTypes
import collections
import traceback
import sys

class cClass:
    NetAddr = POINTER(NetAddr)
    Frame = POINTER(Frame)
    AddrFrame = POINTER(AddrFrame)
    IntFrame = POINTER(IntFrame)
    SeqnoFrame = POINTER(SeqnoFrame)
    CstringFrame = POINTER(CstringFrame)
    UnknownFrame = POINTER(UnknownFrame)
    SignFrame = POINTER(SignFrame)
    FrameSet = POINTER(FrameSet)
    ConfigContext = POINTER(ConfigContext)
    ConfigValue = POINTER(ConfigValue)
    IpPortFrame = POINTER(IpPortFrame)
    guint8 = POINTER(guint8)
    GSList = POINTER(GSList)

def CCref(obj):
    base = obj[0]
    while (type(base) is not AssimObj):
        base=base.baseclass
    base.ref(obj)

def CCunref(obj):
    base = obj[0]
    while (type(base) is not AssimObj):
        base=base.baseclass
    base.unref(obj)

class SwitchDiscovery:
    lldpnames = {
            LLDP_TLV_END:           ('END', True),
            LLDP_TLV_CHID:          ('ChassisId', True),
            LLDP_TLV_PID:           ('PortId', True),
            LLDP_TLV_TTL:           ('TTL', True),
            LLDP_TLV_PORT_DESCR:    ('PortDescription', False),
            LLDP_TLV_SYS_NAME:      ('SystemName', True),
            LLDP_TLV_SYS_DESCR:     ('SystemDescription', True),
            LLDP_TLV_SYS_CAPS:      ('SystemCapabilities', True),
            LLDP_TLV_MGMT_ADDR:     ('ManagementAddress', True),
            LLDP_TLV_ORG_SPECIFIC:  ('(OrgSpecific)', True),
    }
    lldp802_1names = {
            LLDP_ORG802_1_VLAN_PVID:        ('VlanPvId', False),
            LLDP_ORG802_1_VLAN_PORTPROTO:   ('VlanPortProtocol', False),
            LLDP_ORG802_1_VLAN_NAME:        ('VlanName', False),
            LLDP_ORG802_1_VLAN_PROTOID:     ('VlanProtocolId', False),
    }
    lldp802_3names = {
            LLDP_ORG802_3_PHY_CONFIG:   ('PhysicalConfiguration', False),
            LLDP_ORG802_3_POWERVIAMDI:  ('PowerViaMDI', False),
            LLDP_ORG802_3_LINKAGG:      ('LinkAggregation', False),
            LLDP_ORG802_3_MTU:          ('MTU', False),
    }

    @staticmethod
    def _byte0(pktstart):
        return int(cast(pktstart, cClass.guint8)[0])

    @staticmethod
    def _byte1addr(pktstart):
        addr = addressof(pktstart.contents) + 1
        return pointer(type(pktstart.contents).from_address(addr))

    @staticmethod
    def _byteN(pktstart, n):
        return int(cast(pktstart, cClass.guint8)[n])

    @staticmethod
    def _byteNaddr(pktstart, n):
        addr = addressof(pktstart.contents) + n
        return pointer(type(pktstart.contents).from_address(addr))

    @staticmethod
    def _decode_netaddr(addrstart, addrlen):
        byte0 = SwitchDiscovery._byte0(addrstart)
        byte1addr = SwitchDiscovery._byte1addr(addrstart)
        CnetAddr = None
        if byte0 == ADDR_FAMILY_IPV6:
            if addrlen != 17:    return None
            Cnetaddr = netaddr_ipv6_new(byte1addr, 0)
        elif byte0 == ADDR_FAMILY_IPV4:
            if addrlen != 5:     return None
            Cnetaddr = netaddr_ipv4_new(byte1addr, 0)
        elif byte0 == ADDR_FAMILY_802:
            if addrlen == 7:
                Cnetaddr = netaddr_mac48_new(byte1addr)
            elif addrlen == 9:
                Cnetaddr = netaddr_mac64_new(byte1addr)
        if Cnetaddr is not None:
            return str(pyNetAddr(None, Cstruct=Cnetaddr))
        return None

    @staticmethod
    def decode_discovery(host, interface, wallclock, pktstart, pktend):
        if is_valid_lldp_packet(pktstart, pktend):
            return SwitchDiscovery._decode_lldp(host, interface, wallclock, pktstart, pktend)
        if is_valid_cdp_packet(pktstart, pktend):
            return SwitchDiscovery._decode_cdp(host, interface, wallclock, pktstart, pktend)
        raise ValueError('Malformed Switch Discovery Packet')

    @staticmethod
    def _decode_lldp(host, interface, wallclock, pktstart, pktend):
        'Decode LLDP packet into a JSON discovery packet'
        thisportinfo = pyConfigContext(init={
                'ConnectsToHost':       host,
                'ConnectsToInterface':  interface,
            }
        )
        switchinfo = pyConfigContext(init = {'ports': pyConfigContext()})
        metadata = pyConfigContext(init={
                'discovertype':         '#LinkDiscovery',
                'description':          'Link Level Switch Discovery (lldp)',
                'source':               '_decode_lldp()',
                'host':                 host,
                'localtime':            str(wallclock),
                'data':                 switchinfo,
            }
        )

        sourcemacptr = SwitchDiscovery._byteNaddr(cast(pktstart, cClass.guint8), 6)
        if not sourcemacptr:
            return metadata
        Cmacaddr = netaddr_mac48_new(sourcemacptr)
        sourcemac = pyNetAddr(None, Cstruct=Cmacaddr)


        this = get_lldptlv_first(pktstart, pktend)
        while this and this < pktend:
            tlvtype = get_lldptlv_type(this, pktend)
            tlvlen = get_lldptlv_len(this, pktend)
            tlvptr = cast(get_lldptlv_body(this, pktend), cClass.guint8)
            value = None
            if tlvtype not in SwitchDiscovery.lldpnames:
                print >>sys.stderr, 'Cannot find tlvtype %d' % tlvtype
                tlvtype = None
            else:
                (tlvname,isswitchinfo)  = SwitchDiscovery.lldpnames[tlvtype]

            if (tlvtype == LLDP_TLV_PORT_DESCR or tlvtype == LLDP_TLV_SYS_NAME or 
                tlvtype == LLDP_TLV_SYS_DESCR): #########################################
                value = string_at(tlvptr, tlvlen)

            elif tlvtype == LLDP_TLV_PID: ###############################################
                pidtype = SwitchDiscovery._byte0(tlvptr)
                if (pidtype == LLDP_PIDTYPE_ALIAS or pidtype == LLDP_PIDTYPE_IFNAME
                or  pidtype == LLDP_PIDTYPE_LOCAL):
                    sloc = SwitchDiscovery._byte1addr(tlvptr)
                    value = string_at(sloc, tlvlen-1)

            elif tlvtype == LLDP_TLV_CHID: #############################################
                chidtype = SwitchDiscovery._byte0(tlvptr)

                if (chidtype == LLDP_CHIDTYPE_COMPONENT or chidtype == LLDP_CHIDTYPE_ALIAS
                or      chidtype == LLDP_CHIDTYPE_IFNAME or chidtype == LLDP_CHIDTYPE_LOCAL):
                    sloc = SwitchDiscovery._byte1addr(tlvptr)
                    value = string_at(sloc, tlvlen-1)
                elif chidtype == LLDP_CHIDTYPE_MACADDR:
                    byte1addr = SwitchDiscovery._byte1addr(tlvptr)
                    Cmacaddr = None
                    if tlvlen == 7:
                        Cmacaddr = netaddr_mac48_new(byte1addr)
                    elif tlvlen == 9:
                        Cmacaddr = netaddr_mac64_new(byte1addr)
                    if Cmacaddr is not None:
                        value = pyNetAddr(None, Cstruct=Cmacaddr)
                elif chidtype == LLDP_CHIDTYPE_NETADDR:
                    byte1addr = SwitchDiscovery._byte1addr(tlvptr)
                    value = SwitchDiscovery._decode_netaddr(byte1addr, tlvlen-1)

            elif tlvtype == LLDP_TLV_MGMT_ADDR: #########################################
                addrlen = SwitchDiscovery._byte0(tlvptr)
                byte1addr = SwitchDiscovery._byte1addr(tlvptr)
                value = SwitchDiscovery._decode_netaddr(byte1addr, addrlen)

            elif tlvtype == LLDP_TLV_ORG_SPECIFIC: ######################################
                print >>sys.stderr, 'Found LLDP org-specific extensions (not processed)'

            if value is not None:
                if tlvtype == LLDP_TLV_PID:
                    switchinfo['ports'][value] = thisportinfo
                    numericpart = value
                    while len(numericpart) > 0 and not numericpart.isdigit():
                        numericpart = numericpart[1:]
                    if len > 0 and numericpart.isdigit():
                        thisportinfo['_PORTNO'] = int(numericpart)
                else:
                    if isswitchinfo:
                        switchinfo[tlvname] = value
                    else:
                        thisportinfo[tlvname] = value
            this = get_lldptlv_next(this, pktend)
        thisportinfo['sourceMAC'] = sourcemac
        return metadata
        
        
    @staticmethod
    def _decode_cdp(host, interface, wallclock, pktstart, pktend):
        'Decode CDP packet into a JSON discovery packet'
        thisportinfo = pyConfigContext(init={
                'ConnectsToHost':       host,
                'ConnectsToInterface':  interface,
            }
        )
        switchinfo = pyConfigContext(init = {'ports': pyConfigContext()})
        metadata = pyConfigContext(init={
                'discovertype':         '#LinkDiscovery',
                'description':          'Link Level Switch Discovery (cdp)',
                'source':               '_decode_cdp()',
                'host':                 host,
                'localtime':            str(wallclock),
                'data':                 switchinfo,
            }
        )
        return metadata

    


class pyAssimObj:
    def __init__(self, Cstruct=None):
        'Create a base pyAssimObj object'
        self._Cstruct = None
        if (Cstruct is not None):
            assert type(Cstruct) is not int
            self._Cstruct = Cstruct
        else:
            self._Cstruct = assimobj_new(0)
        #print 'ASSIMOBJ:init: %s' % (Cstruct)
        #CCref(Cstruct)

    def cclassname(self):
        return proj_class_classname(self._Cstruct)

    def __str__(self):
        'Convert this AssimObj into a printable string'
        if not self._Cstruct:
            return "[None]"
        base = self._Cstruct[0]
        while (type(base) is not AssimObj):
            base=base.baseclass
        cstringret = base.toString(self._Cstruct)
        ret = string_at(cstringret)
        g_free(cstringret)
        return ret

    def __del__(self):
        'Free up the underlying Cstruct for this pyAssimObj object.'
        if not self._Cstruct or self._Cstruct is None:
            return
        base=self._Cstruct[0]
        # I have no idea why the type(base) is not Frame doesn't work here...
        # This 'hasattr' construct only works because we are a base C-class
        while (hasattr(base, 'baseclass')):
            base=base.baseclass
        global badfree
        badfree=0
        base.unref(self._Cstruct)
        if badfree != 0:
            print >>sys.stderr, "Attempt to free something already freed(%s)" % str(self._Cstruct)
            traceback.print_stack()
            badfree = 0
        self._Cstruct = None

    def _ref(self):
        CCref(self)

class pyNetAddr(pyAssimObj):
    '''This class represents the Python version of our C-class @ref NetAddr - represented by the struct _NetAddr.
    '''
    def __init__(self, addrstring, port=None, Cstruct=None):
        '''This constructor needs a list of integers of the right length as its first argument.
        The length of the list determines the type of address generated.
         4 bytes == ipv4
         6 bytes == MAC address
         8 bytes == MAC address
         16 bytes == ipv6 address
        This is slightly sleazy but it should work for the forseeable future.
        '''

        self._Cstruct = None	# Silence error messages in failure cases

        if (Cstruct is not None):
            assert type(Cstruct) is not int
            pyAssimObj.__init__(self, Cstruct=Cstruct)
            return

        if port is None: port = 0

        if isinstance(addrstring, unicode):
           addrstring = str(addrstring)
        if isinstance(addrstring, str) or isinstance(addrstring, unicode):
            cs = netaddr_string_new(addrstring, port)
            if not cs:
                raise ValueError('Illegal NetAddr initial value: "%s"' % addrstring)
            pyAssimObj.__init__(self, Cstruct=cs)
            return
        
        alen = len(addrstring)
        addr = create_string_buffer(alen)
        #print >>sys.stderr, "ADDRTYPE:", type(addr)
        #print >>sys.stderr, "ADDRSTRINGTYPE:", type(addrstring)
        for i in range(0, alen):
            asi = addrstring[i]
            #print >>sys.stderr, "ASI_TYPE: (%s,%s)" % (type(asi), asi)
            if type(asi) is str:
                addr[i] = asi
            elif type(asi) is unicode:
                addr[i] = str(asi)
            else:
                addr[i] = chr(asi)
        #print >>sys.stderr, 'ADDR = %s'  % addr
        if alen == 4:		# ipv4
            NA = netaddr_ipv4_new(addr, port)
            pyAssimObj.__init__(self, Cstruct=NA)
        elif alen == 16:	# ipv6
            pyAssimObj.__init__(self, netaddr_ipv6_new(addr, port))
        elif alen == 6:		# "Normal" 48-bit MAC address
            assert port == 0
            pyAssimObj.__init__(self, netaddr_mac48_new(addr, port))
        elif alen == 8:		# Extended 64-bit MAC address
            assert port == 0
            pyAssimObj.__init__(self, netaddr_mac64_new(addr, port))
        else:
            raise ValueError("Invalid address length - not 4, 6, 8, or 16")

    def port(self):
        "Return the port (if any) for this pyNetAddr object"
        base=self._Cstruct[0]
        while (type(base) is not NetAddr):
            base=base.baseclass
        return base.port(self._Cstruct)

    def setport(self, port):
        "Return the port (if any) for this pyNetAddr object"
        base=self._Cstruct[0]
        while (type(base) is not NetAddr):
            base=base.baseclass
        base.setport(self._Cstruct, port)

    def addrtype(self):
        "Return the type of address for this pyNetAddr object"
        base=self._Cstruct[0]
        while (type(base) is not NetAddr):
            base=base.baseclass
        return base.addrtype(self._Cstruct)

    def addrlen(self):
        "Return the number of bytes necessary to represent this pyNetAddr object on the wire."
        base=self._Cstruct[0]
        while (type(base) is not NetAddr):
            base=base.baseclass
        return base._addrlen

    def __repr__(self):
        'Return a canonical representation of this NetAddr'
        base=self._Cstruct[0]
        while (type(base) is not NetAddr):
            base=base.baseclass
        cstringret =  base.canonStr(self._Cstruct)
        ret = string_at(cstringret)
        g_free(cstringret)
        return ret


    def __eq__(self, rhs):
        'Compare this pyNetAddr to another pyNetAddr'
        lhsbase = self._Cstruct[0]
        while (type(lhsbase) is not NetAddr):
            lhsbase=lhsbase.baseclass
        return lhsbase.equal(self._Cstruct, rhs._Cstruct)
         

    # Do we need to define an addrbody() member function?
    def __eq__(self, other):
        "Return True if the two pyNetAddrs are equal"
        if not other._Cstruct or not self._Cstruct:
            return False
        base=self._Cstruct[0]
        while (type(base) is not NetAddr):
            base=base.baseclass
        return base.equal(self._Cstruct, other._Cstruct)



class pyFrame(pyAssimObj):
    '''This class represents the Python version of our C-class @ref Frame - represented by the struct _Frame.
    This class is a base class for several different pyFrame subclasses.
    Each of these various pyFrame subclasses have a corresponding C-class @ref Frame subclass.
    The purpose of these pyFrames and their subclasses is to talk on the wire with our C code in our
    nanoprobes.

    Deliberately leaving out the updatedata() C-class member function - at least for mow.
    I suspect that the Python code will only need the corresponding calls in a @ref FrameSet - which would
    then update the corresponding @ref Frame member functions...
    '''
    #
    #	Our subclasses need to implement these methods:
    #		__init__ - subclass initializer
    #		from_Cstruct classmethod - call the corresponding xxxframe_tlvconstructor() function
    #			to act as a pseudo-constructor.  This method/constructor is used to create
    #			Python objects from incoming packet data.
    #
    def __init__(self, initval, Cstruct=None):
        "Initializer for the pyFrame object."
        if Cstruct is None:
            try:
                frametype = initval.tlvtype
            except:
                frametype = int(initval)
            # If we don't do this, then a subclass __init__ function must do it instead...
            pyAssimObj.__init__(self, Cstruct=frame_new(frametype, 0))
        else:
            pyAssimObj.__init__(self, Cstruct=Cstruct)

    def frametype(self):
        "Return the TLV type for the pyFrame object."
        base=self._Cstruct[0]
        while (type(base)is not Frame):
            base=base.baseclass
        return base.type

    def framelen(self):
        "Return the length of this frame in bytes (TLV length)."
        base=self._Cstruct[0]
        while (type(base)is not Frame):
            base=base.baseclass
        return base.length
   
    def framevalue(self):
        'Return a C-style pointer to the underlying raw TLV data (if any)'
        base=self._Cstruct[0]
        while (type(base)is not Frame):
            base=base.baseclass
        return cast(base.value, c_char_p)

    def frameend(self):
        'Return a C-style pointer to the underlying raw TLV data (if any)'
        base=self._Cstruct[0]
        while (type(base)is not Frame):
            base=base.baseclass
        return cast(base.value+base.length, c_char_p)

    def dataspace(self):
        'Return the amount of space this frame needs - including type and length'
        base=self._Cstruct[0]
        while (type(base) is not Frame):
            base=base.baseclass
        return base.dataspace(self._Cstruct)

    def isvalid(self):
        "Return True if this Frame is valid"
        base=self._Cstruct[0]
        while (type(base) is not Frame):
            base=base.baseclass
        pstart = pointer(cast(base.value, c_char_p))
#        if pstart[0] is None:
#            return False
        return (int(base.isvalid(self._Cstruct, None, None)) != 0)

    def setvalue(self, value):
        'Assign a chunk of memory to the Value portion of this Frame'
        vlen = len(value)
        if type(value) is str:
            valbuf = create_string_buffer(vlen+1)
            for i in range(0, vlen):
                vi = value[i]
                valbuf[i] =  vi
            valbuf[vlen] = chr(0)
            vlen += 1
        else:
            valbuf = create_string_buffer(vlen)
            for i in range(0, vlen):
                vi = value[i]
                valbuf[i] =  int(vi)
        base=self._Cstruct[0]
        valptr = MALLOC(vlen)
        memmove(valptr, valbuf, vlen)
        while (type(base) is not Frame):
            base=base.baseclass
        base.setvalue(self._Cstruct, valptr, vlen, cast(None, GDestroyNotify))

    def dump(self, prefix):
        'Dump out this Frame (using C-class "dump" member function)'
        base=self._Cstruct[0]
        while (type(base) is not Frame):
            base=base.baseclass
        base.dump(self._Cstruct, cast(prefix, c_char_p))

    def __str__(self):
        base = self._Cstruct[0]
        while (type(base) is not AssimObj):
            base=base.baseclass
        cstringret = base.toString(self._Cstruct)
        ret = string_at(cstringret)
        g_free(cstringret)
        return '%s: %s' % (FrameTypes.get(self.frametype())[1] , ret)

    @staticmethod
    def Cstruct2Frame(frameptr):
        frameptr = cast(frameptr, cClass.Frame)
        CCref(frameptr)
        frametype = frameptr[0].type
        Cclassname = proj_class_classname(frameptr)
        pyclassname = "py" + Cclassname
        if Cclassname == 'NetAddr':
            statement = "%s(%d, None, Cstruct=cast(frameptr, cClass.%s))" % (pyclassname, frametype, Cclassname)
        elif Cclassname == Cclassname == 'IpPortFrame':
            statement = "%s(%d, None, None, Cstruct=cast(frameptr, cClass.%s))" % (pyclassname, frametype, Cclassname)
        else:
            statement = "%s(%d, Cstruct=cast(frameptr, cClass.%s))" % (pyclassname, frametype, Cclassname)
        #print >>sys.stderr, "EVAL:", statement
        return eval(statement)

class pyAddrFrame(pyFrame):
    '''This class represents the Python version of our C-class AddrFrame - represented by the struct _AddrFrame.
    '''
    def __init__(self, frametype, addrstring=None, port=None, Cstruct=None):
        "Initializer for the pyAddrFrame object."
        self._Cstruct = None # Keep error legs from complaining.
        if Cstruct is None:
            if isinstance(addrstring, pyNetAddr):
                self._pyNetAddr = addrstring
            else:
                self._pyNetAddr = pyNetAddr(addrstring, port=port)
            Cstruct=addrframe_new(frametype, 0)
            if addrstring is not None:
                Cstruct[0].setnetaddr(Cstruct, self._pyNetAddr._Cstruct)
        else:
            assert port is None
            assert addrstring is None
            addrlen = Cstruct[0].baseclass.length - 2 # Allow for prefixed address type - two bytes
            assert addrlen == 4 or addrlen == 6 or addrlen == 8 or addrlen == 16, ("addrlen is %d" % addrlen)
            addrstr = Cstruct[0].baseclass.value+2
            addrstring = create_string_buffer(addrlen)
            memmove(addrstring, addrstr, addrlen)
            self._pyNetAddr = pyNetAddr(addrstring, port=None)
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)

    def addrtype(self):
        return self._pyNetAddr.addrtype()

    def getnetaddr(self):
        return self._pyNetAddr

    def __str__(self):
       return ("pyAddrFrame(%s, (%s))" % (FrameTypes.get(self.frametype())[1], str(self._pyNetAddr)))

class pyIpPortFrame(pyFrame):
    '''This class represents the Python version of our C-class IpPortFrame - represented by the struct _IpPortFrame.
    '''
    def __init__(self, frametype, addrstring, port, Cstruct=None):
        "Initializer for the pyIpPortFrame object."
        self._Cstruct = None # Keep error legs from complaining.
        if Cstruct is None:
            if isinstance(addrstring, pyNetAddr):
                self._pyNetAddr = addrstring
            else:
                addrlen = len(addrstring)
                self._pyNetAddr = pyNetAddr(addrstring, port=port)

                addrstr = create_string_buffer(addrlen)
                for j in range(0, addrlen):
                    addrstr[j] = chr(addrstring[j])
                if addrlen == 4:
                    Cstruct=ipportframe_ipv4_new(frametype, port, addrstr)
                elif addrlen == 16:
                    Cstruct=ipportframe_ipv6_new(frametype, port, addrstr)
                else:
                    raise ValueError('Bad address length: %d' % addrlen)
                self.port = port
        else:
            assert port is None
            assert addrstring is None
            addrlen = Cstruct[0].baseclass.length - 4 # Allow for prefixed port and address type
            if addrlen != 4 and addrlen != 16:
                raise ValueError("Bad addrlen: %d" % addrlen)
            port = Cstruct[0].port
            self.port = port
            addrstr = Cstruct[0].baseclass.value+4
            addrstring = create_string_buffer(addrlen)
            memmove(addrstring, addrstr, addrlen)
            self._pyNetAddr = pyNetAddr(addrstring, port=port)
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)

    def addrtype(self):
        return self._pyNetAddr.addrtype()

    def getnetaddr(self):
        return self._pyNetAddr

    def __str__(self):
       return ("pyIpPortFrame(%s, (%s))" % (FrameTypes.get(self.frametype())[1], str(self._pyNetAddr)))


class pyCstringFrame(pyFrame):
    '''This class represents the Python version of our C-class CstringFrame - represented by the struct _CstringFrame
    This class represents a Frame standard NUL-terminated C string.
    '''
    def __init__(self, frametype, initval=None, Cstruct=None):
        'Constructor for pyCstringFrame object - initial value should be something that looks a lot like a Python string'
        if Cstruct is None:
            Cstruct=cstringframe_new(frametype, 0)
        pyFrame.__init__(self, frametype, Cstruct)
        if initval is not None:
            self.setvalue(initval)

    def getstr(self):
        base = self._Cstruct[0]
        while (not hasattr(base, 'value')):
            base=base.baseclass
        return string_at(base.value)

class pyIntFrame(pyFrame):
    '''This class represents the Python version of our IntFrame C-class - represented by the struct _IntFrame
    This class represents an integer of 1, 2, 3, 4 or 8 bytes.
    '''
    def __init__(self, frametype, initval=None, intbytes=4, Cstruct=None):
        'Constructor for pyIntFrame object - initial value should be something that looks a lot like an integer'
        self._Cstruct = None
        if Cstruct is None:
            Cstruct=intframe_new(frametype, intbytes)
        if not Cstruct:
            raise ValueError, ("Invalid integer size (%d) in pyIntFrame constructor" % intbytes)
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)
        if initval is not None:
            self.setint(initval)

    def __int__(self):
        'Return the integer value of this pyIntFrame. (implemented by the underlying IntFrame object)'
        return self._Cstruct[0].getint(self._Cstruct)

    def __str__(self):
        'Return a string representation of this pyIntFrame (the integer value).'
        return ("pyIntFrame(%s, (%d))" % (FrameTypes.get(self.frametype())[1], int(self)))

    def getint(self):
        'Return the integer value of this pyIntFrame - same as __int__.'
        return int(self)

    def setint(self, intval):
        '''Set the value of this pyIntFrame to the given integer value.
        Note that this value is range checked by the underlying IntFrame implementation.
        '''
        self._Cstruct[0].setint(self._Cstruct, int(intval))

    def intlength(self):
        '''Return the number of bytes in the integer underlying this pyIntFrame object.
           (implemented by underlying IntFrame object)'''
        return self._Cstruct[0].intlength(self._Cstruct)

class pyUnknownFrame(pyFrame):
    "Class for a Frame type we don't recognize"
    def __init__(self, frametype, Cstruct=None):
        'Initializer for pyUnknownFrame'
        if Cstruct is None:
            Cstruct=unknownframe_new(frametype)
        pyFrame.__init__(self, frametype, Cstruct)

class pySeqnoFrame(pyFrame):
    'Class for a Sequence Number Frame - for reliable UDP packet transmission.'
    def __init__(self, frametype, initval=None, Cstruct=None):
        'Initializer for pySeqnoFrame'
        self._Cstruct = None
        # TODO(?): Need to allow for initialization of seqno frames.
        if Cstruct is None:
            Cstruct=seqnoframe_new(frametype, 0)
        if not Cstruct:
            raise ValueError, "Constructor error for PySeqnoFrame()"
        pyFrame.__init__(self, frametype, Cstruct=Cstruct)
        if initval is not None:
            self.setqid(initval[0])
            self.setreqid(initval[1])

    def setreqid(self, reqid):
        self._Cstruct[0].setreqid(self._Cstruct, reqid)

    def setqid(self, qid):
        self._Cstruct[0].setqid(self._Cstruct, qid)

    def getreqid(self):
        return self._Cstruct[0].getreqid(self._Cstruct)

    def getqid(self):
        return self._Cstruct[0].getqid(self._Cstruct)

    def __eq__(self, rhs):
        'Compare this pySeqnoFrame to another pySeqnoFrame'
        lhsbase = self._Cstruct[0]
        while (type(lhsbase) is not SeqnoFrame):
            lhsbase=lhsbase.baseclass
        return lhsbase.equal(self._Cstruct, rhs._Cstruct)

    def __str__(self):
        return ("pySeqNo(%s: (%d, %d))" % (FrameTypes.get(self.frametype())[1], self.getqid(), self.getreqid()))

class pySignFrame(pyFrame):
    'Class for Digital Signature Frames - for authenticating data (subclasses will authenticate senders)'
    def __init__(self, gchecksumtype, Cstruct=None):
        'Initializer for pySignFrame'
        self._Cstruct = None
        if Cstruct is None:
            Cstruct=signframe_new(gchecksumtype, 0)
        if not Cstruct:
            raise ValueError, ("Invalid checksum type (%s) for PySignFrame()" % gchecksumtype)
        pyFrame.__init__(self, initval=FRAMETYPE_SIG, Cstruct=Cstruct)

class pyNVpairFrame(pyFrame):
    'Class for a Frame containing a single name/value pair'
    def __init__(self, frametype, name, value, Cstruct=None):
        'Initializer for pyNVpairFrame'
        self._Cstruct = None
        if Cstruct is None:
            Cstruct=nvpairframe_new(frametype, name, value, 0)
        if not Cstruct:
            raise ValueError, ("Invalid NVpair initializer for pyNVPairFrame()")
        pyFrame.__init__(self, initval=frametype, Cstruct=Cstruct)

    def name(self):
        'Return the name portion of a pyNVpairFrame'
        return string_at(self._Cstruct[0].name)

    def value(self):
        'Return the name portion of a pyNVpairFrame'
        return string_at(self._Cstruct[0].value)
        


class pyFrameSet(pyAssimObj):
    'Class for Frame Sets - for collections of Frames making up a logical packet'
    def __init__(self, framesettype, Cstruct=None):
        'Initializer for pyFrameSet'
        if Cstruct is None:
            Cstruct=frameset_new(framesettype)
        pyAssimObj.__init__(self, Cstruct=Cstruct)

    def append(self, frame):
        'Append a frame to the end of a @ref FrameSet'
        frameset_append_frame(self._Cstruct, frame._Cstruct)

    def prepend(self, frame):
        'Prepend a frame before the first frame in a @ref FrameSet'
        frameset_prepend_frame(self._Cstruct, frame._Cstruct)

    def construct_packet(self, signframe, cryptframe=None,  compressframe=None):
        'Construct packet from curent frameset + special prefix frames'
        cf = None
        cmpf = None
        if cryptframe is not None:
            cf = cryptframe._Cstruct
        if compressframe is not None:
            cmpf = compressframe._Cstruct
        frameset_construct_packet(self._Cstruct, signframe._Cstruct, cf, cmpf)

    def get_framesettype(self):
        'Return frameset type of this FrameSet'
        return self._Cstruct[0].fstype

    def get_flags(self):
        'Return current flags for this FrameSet'
        return frameset_get_flags(self._Cstruct)

    def set_flags(self, flags):
        "'OR' the given flags into the set of flags for this FrameSet"
        return frameset_set_flags(self._Cstruct, int(flags))

    def clear_flags(self, flags):
        "Clear the given flags for this FrameSet"
        return frameset_clear_flags(self._Cstruct, int(flags))

    def dump(self):
        'Dump out the given frameset'
        frameset_dump(self._Cstruct)

    def getpacket(self):
        if not self._Cstruct[0].packet:
            raise ValueError, "No packet constructed for frameset"
        return (self._Cstruct[0].packet, self._Cstruct[0].pktend)

    def __len__(self):
        curframe = self._Cstruct[0].framelist
        count=0
        while curframe:
            count += 1
            curframe=g_slist_next(curframe)
        return count

    def iter(self):
        'Generator yielding the set of pyFrames in this pyFrameSet'
        curframe = self._Cstruct[0].framelist
        while curframe:
            cast(curframe[0].data, struct__GSList._fields_[0][1])
            yieldval =  pyFrame.Cstruct2Frame(cast(curframe[0].data, cClass.Frame))
            if not yieldval.isvalid():
                print "OOPS!  Constructed frame from iter() is not valid"
            #print "Yielding:", str(yieldval), "<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<"
            yield yieldval
            curframe=g_slist_next(curframe)

    def __str__(self):
        'Convert pyFrameSet to string'
        result = '%s:{' % FrameSetTypes.get(self.get_framesettype())[0]
        comma=''
        for frame in self.iter():
            result += '%s%s' % (comma, str(frame))
            comma=', '
        result += "}"
        return result


class pyPacketDecoder(pyAssimObj):
    'Class for Decoding packets - for returning an array of FrameSets from a physical packet.'
    def __init__(self, FrameMap=None, Cstruct=None):
        'Initializer for pyPacketDecoder'
        if Cstruct is None:
            Cstruct=packetdecoder_new(0, None, 0)
        pyAssimObj.__init__(self, Cstruct=Cstruct)

    def fslist_from_pktdata(self, pktlocation):
        'Make a list of FrameSets out of a packet.'
        base=self._Cstruct[0]
        while (type(base)is not PacketDecoder):
            base=base.baseclass
        fs_gslistint = base.pktdata_to_framesetlist(self._Cstruct, pktlocation[0], pktlocation[1])
        return pyPacketDecoder.fslist_to_pyfs_array(fs_gslistint)

    @staticmethod
    def fslist_to_pyfs_array(listheadint):
        'Converts a GSList of FrameSets to a python array of pyFrameSets'
        fs_gslist = cast(listheadint, POINTER(GSList))
        frameset_list = []
        curfs = fs_gslist
        while curfs:
            cfs = cast(curfs[0].data, cClass.FrameSet)
            fs = pyFrameSet(None, Cstruct=cfs)
            frameset_list.append(fs)
            curfs = g_slist_next(curfs)
        g_slist_free(fs_gslist)
        return frameset_list

class pyConfigContext(pyAssimObj):
    'Class for Holding configuration information.'

    def __init__(self, init=None, Cstruct=None):
        'Initializer for pyConfigContext'
        self._Cstruct = None # Keep error legs from complaining.
        if Cstruct is None:
            if Cstruct is None and (isinstance(init, str) or isinstance(init, unicode)):
                Cstruct = configcontext_new_JSON_string(str(init))
                #CCref(Cstruct)
                if not Cstruct:
                    raise ValueError('Bad JSON [%s]' % str(init))
                init = None
            else:
                Cstruct=configcontext_new(0)
        else:
            CCref(Cstruct)
        pyAssimObj.__init__(self, Cstruct=Cstruct)
        if init is not None:
            for key in init.keys():
                self[key] = init[key]

    def getint(self, name):
        'Return the integer associated with "name"'
        return self._Cstruct[0].getint(self._Cstruct, name)

    def setint(self, name, value):
        'Set the integer associated with "name"'
        self._Cstruct[0].setint(self._Cstruct, name, value)

    def getbool(self, name):
        'Return the boolean associated with "name"'
        return self._Cstruct[0].getbool(self._Cstruct, name) != 0

    def setbool(self, name, value):
        'Set the boolean associated with "name"'
        self._Cstruct[0].setbool(self._Cstruct, name, int(value))

    def getaddr(self, name):
        'Return the NetAddr associated with "name"'
        naddr = self._Cstruct[0].getaddr(self._Cstruct, name)
        if naddr:
            naddr = cast(naddr, cClass.NetAddr)
            CCref(naddr)
            return pyNetAddr(None, Cstruct=naddr)
        raise IndexError("No such NetAddr value [%s]" % name)

    def setaddr(self, name, value):
        'Set the @ref NetAddr associated with "name"'
        self._Cstruct[0].setaddr(self._Cstruct, name, value._Cstruct)

    def getframe(self, name):
        'Return the Frame associated with "name"'
        faddr = self._Cstruct[0].getframe(self._Cstruct, name)
        if faddr:
            return pyFrame.Cstruct2Frame(faddr)
        raise IndexError("No such Frame value [%s]" % name)

    def setframe(self, name, value):
        'Set the @ref Frame associated with "name"'
        self._Cstruct[0].setframe(self._Cstruct, name, value._Cstruct)

    def getconfig(self, name):
        'Return the pyConfigContext object associated with "name"'
        caddr = self._Cstruct[0].getconfig(self._Cstruct, name)
        if caddr:
            caddr=cast(caddr, cClass.ConfigContext)
            return pyConfigContext(Cstruct=caddr)
        raise IndexError("No such ConfigContext value [%s]" % name)

    def setconfig(self, name, value):
        'Set the @ref ConfigContext associated with "name"'
        self._Cstruct[0].setconfig(self._Cstruct, name, value._Cstruct)

    def getstring(self, name):
        'Return the string associated with "name"'
        ret = self._Cstruct[0].getstring(self._Cstruct, name)
        if ret:
            return string_at(ret)
        raise IndexError("No such String value [%s]" % name)

    def setstring(self, name, value):
        'Return the string associated with "name"'
        self._Cstruct[0].setstring(self._Cstruct, name, value)

    def getarray(self, name):
        'Return the array value associated with "name"'
        l=  self._Cstruct[0].getarray(self._Cstruct, name)
        curlist = cast(self._Cstruct[0].getarray(self._Cstruct, name), cClass.GSList)
        #curlist = cast(POINTER(GSList), self._Cstruct[0].getarray(self._Cstruct, name))
        ret = []
        while curlist:
            #cfgval = pyConfigValue(cast(cClass.ConfigValue, curlist[0].data).get())
            data = cast(curlist[0].data, cClass.ConfigValue)
            cfgval = pyConfigValue(data).get()
            ret.append(cfgval)
            curlist=g_slist_next(curlist)
        return ret

    def keys(self):
        'Return the set of keys for this object'
        l = []
        keylist = cast(self._Cstruct[0].keys(self._Cstruct), POINTER(GSList))
        curkey = keylist
        while curkey:
            l.append(string_at(curkey[0].data))
            curkey=g_slist_next(curkey)
        g_slist_free(keylist)
        return l

    def has_key(self, key):
        'return True if it has the given key'
        ktype = self._Cstruct[0].gettype(self._Cstruct, str(key))
        return ktype != CFG_EEXIST

    def __contains__(self, key):
        'return True if our object contains the given key'
        ktype = self._Cstruct[0].gettype(self._Cstruct, str(key))
        return ktype != CFG_EEXIST
    
    def gettype(self, name):
        #print >>sys.stderr, 'gettype(%s)' % str(name)
        return self._Cstruct[0].gettype(self._Cstruct, str(name))
        

    def __getitem__(self, name):
        'Return a value associated with "name"'
        ktype = self.gettype(name)
        if ktype == CFG_EEXIST:
            raise IndexError("No such value [%s] in [%s]" % (name, str(self)))
        if ktype == CFG_CFGCTX:
            return self.getconfig(name)
        if ktype == CFG_STRING:
            return self.getstring(name)
        if ktype == CFG_NETADDR:
            return self.getaddr(name)
        if ktype == CFG_FRAME:
            return self.getframe(name)
        if ktype == CFG_INT64:
            return self.getint(name)
        if ktype == CFG_BOOL:
            return self.getbool(name)
        if ktype == CFG_ARRAY:
            return self.getarray(name)
            return None
        return None

    def __setitem__(self, name, value):
        'Set a value associated with "name" - in the appropriate table'
        if isinstance(value, str):
            return self.setstring(name, value)
        if isinstance(value, pyNetAddr):
            return self.setaddr(name, value)
        if isinstance(value, pyFrame):
            return self.setframe(name, value)
        if isinstance(value, pyConfigContext):
            return self.setconfig(name, value)
        self.setint(name, int(value))

class pyConfigValue:
    def __init__(self, Cstruct):
        'Initializer for pyConfigValue. NOTE: we make no provisions for object life...'
        self._Cstruct = Cstruct

    def get(self):
        vtype = self._Cstruct[0].valtype
        if vtype == CFG_BOOL:
            return self._Cstruct[0].u.intvalue != 0
        if vtype == CFG_INT64:
            return int(self._Cstruct[0].u.intvalue)
        if vtype == CFG_STRING:
            return str(self._Cstruct[0].u.strvalue)
        if vtype == CFG_FLOAT:
            return float(self._Cstruct[0].u.floatvalue)
        if vtype == CFG_CFGCTX:
            return pyConfigContext(Cstruct=self._Cstruct[0].u.cfgctxvalue)
        if vtype == CFG_NETADDR:
            return pyNetAddr(None, Cstruct=self._Cstruct[0].u.addrvalue)
        if vtype == CFG_FRAME:
            return pyFrame.Cstruct2Frame(self._Cstruct[0].u.framevalue)
        if vtype == CFG_ARRAY:
            # An Array is a linked list of ConfigValue objects...
            ret = []
            this = self._Cstruct.arrayvalue
            while this:
                dataptr = cast(this[0].data, struct__GSList._fields_[0][1])
                thisdata = pyConfigValue(cast(dataptr, cClass.ConfigValue))
                this = g_slist_next(this)
                ret.append(thisdata.get())
            return ret




        raise ValueError('Invalid valtype (%s)in pyConfigValue object' % self._Cstruct.valtype)

class pyNetIO(pyAssimObj):
    def __init__(self, configobj, packetdecoder, Cstruct=None):
        'Initializer for pyNetIO'
        self._Cstruct = None # Keep error legs from complaining.
        if Cstruct is None:
            Cstruct=netio_new(0, configobj._Cstruct, packetdecoder._Cstruct)
            self.config = configobj
        else:
            self.config = pyConfigContext(Cstruct=Cstruct[0].baseclass._configinfo)
        pyAssimObj.__init__(self, Cstruct=Cstruct)

    def setblockio(self, mode):
        'Set this NetIO object to blocking IO mode'
        base = self._Cstruct[0]
        while (not hasattr(base, 'setblockio')):
            base=base.baseclass
        return base.setblockio(self._Cstruct, int(mode))

    def getfd(self):
        'Return the file descriptor for this pyNetIO object'
        base = self._Cstruct[0]
        while (not hasattr(base, 'getfd')):
            base=base.baseclass
        return base.getfd(self._Cstruct)

    def bindaddr(self, addr, silent=False):
        'Bind the socket underneath this NetIO object to the given address'
        base = self._Cstruct[0]
        while (not hasattr(base, 'bindaddr')):
            base=base.baseclass
        return base.bindaddr(self._Cstruct, addr._Cstruct, silent)

    def boundaddr(self):
        'Bind the socket underneath this NetIO object to the given address'
        base = self._Cstruct[0]
        while (not hasattr(base, 'bindaddr')):
            base=base.baseclass
        boundaddr = base.boundaddr(self._Cstruct)
        return pyNetAddr(None, Cstruct=boundaddr)

    def mcastjoin(self, addr):
        'Join the underlying socket to the given multicast address'
        base = self._Cstruct[0]
        while (not hasattr(base, 'mcastjoin')):
            base=base.baseclass
        return base.mcastjoin(self._Cstruct, addr._Cstruct, None)

    def getmaxpktsize(self):
        'Return the max packet size for this pyNetIO'
        base = self._Cstruct[0]
        while (not hasattr(base, 'getmaxpktsize')):
            base=base.baseclass
        return base.getmaxpktsize(self._Cstruct)

    def setmaxpktsize(self, size):
        'Set the max packet size for this pyNetIO'
        base = self._Cstruct[0]
        while (not hasattr(base, 'setmaxpktsize')):
            base=base.baseclass
        return base.setmaxpktsize(self._Cstruct, int(size))

    def compressframe(self):
        'Return the compression frame for this pyNetIO - may be None'
        # Doesn't make a py class object out of it yet...
        base = self._Cstruct[0]
        while (not hasattr(base, 'compressframe')):
            base=base.baseclass
        return base.compressframe(self._Cstruct)

    def cryptframe(self):
        'Return the encryption frame for this pyNetIO - may be None'
        # Doesn't make a py class object out of it yet...
        base = self._Cstruct[0]
        while (not hasattr(base, 'cryptframe')):
            base=base.baseclass
        return base.cryptframe(self._Cstruct)

    def signframe(self):
        'Return the digital signature frame for this pyNetIO'
        base = self._Cstruct[0]
        while (not hasattr(base, 'signframe')):
            base=base.baseclass
        return pySignFrame(0,Cstruct=cast(base.signframe(self._Cstruct), cClass.SignFrame))

    def sendframesets(self, destaddr, framesetlist):
        'Send the (collection of) frameset(s) out on this pyNetIO'
        if destaddr.port() == 0:
            raise ValueError("Zero Port in sendframesets: destaddr=%s" % str(destaddr))
        if not isinstance(framesetlist, collections.Sequence):
            framesetlist = (framesetlist, )
        base = self._Cstruct[0]
        while (not hasattr(base, 'sendaframeset')):
            base=base.baseclass
        # We ought to eventually construct a GSList of them and then call sendframesets
        # But this is easy for now...
        for frame in framesetlist:
            base.sendaframeset(self._Cstruct, destaddr._Cstruct, frame._Cstruct)
        
    def recvframesets(self):
        '''Receive a collection of framesets read from this pyNetIO - all from the same Address.
         @return The return value is a tuple (address, framesetlist). '''
         #GSList * 	_netio_recvframesets (NetIO *self,NetAddr **src)

        base = self._Cstruct[0]
        while (not hasattr(base, 'recvframesets')):
            base=base.baseclass
        netaddr =  netaddr_ipv4_new(create_string_buffer(4), 101)
        netaddr[0].baseclass.unref(netaddr)	# We're about to replace it...
        fs_gslistint = base.recvframesets(self._Cstruct, byref(netaddr))
        fslist = pyPacketDecoder.fslist_to_pyfs_array(fs_gslistint)
        address = pyNetAddr(None, Cstruct=netaddr)
        if netaddr:
            CCref(netaddr)
            address = pyNetAddr(None, Cstruct=netaddr)
        else:
            address = None
        return (address, fslist)

    @staticmethod
    def is_dual_ipv4v6_stack():
        return netio_is_dual_ipv4v6stack()

class pyNetIOudp(pyNetIO):
    'UDP version of the pyNetIO abstract base class'
    def __init__(self, config, packetdecoder, Cstruct=None):
        'Initializer for pyNetIOudp'
        self._Cstruct = None # Keep error legs from complaining.
        if Cstruct is None:
            Cstruct=netioudp_new(0, config._Cstruct, packetdecoder._Cstruct)
        if not Cstruct:
            raise ValueError, ("Invalid parameters to pyNetIOudp constructor")
        pyNetIO.__init__(self, config, packetdecoder, Cstruct=Cstruct)

class CMAlib:
    @staticmethod
    def create_setconfig(cfg):
        fs =  cast(create_setconfig(cfg._Cstruct), cClass.FrameSet)
        return pyFrameSet(None, Cstruct=fs)

    @staticmethod
    def create_sendexpecthb(cfg, msgtype, address):
        ucfs =  create_sendexpecthb(cfg._Cstruct, int(msgtype)
        ,	address._Cstruct, 1)
        fs = cast(ucfs, cClass.FrameSet)
        return pyFrameSet(None, Cstruct=fs)
