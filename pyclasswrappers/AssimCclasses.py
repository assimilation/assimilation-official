#!/usr/bin/python
'''
A collection of classes which wrap our @ref C-Classes and provide Pythonic interfaces to these C-classes.
'''

from AssimCtypes import *

class TLV:
    '''Type/Length/Value abstract class.
    We expect to create IEEE (LLDP), Cisco (CDP) and our local variants (generic) subclasses...
    '''
    def __init__(self, tlvtype, tlvvalue):
        'Initialize the TLV using a string_buffer or similar'
        assert tlvtype >= 0
        self.tlvtype = tlvtype
        self.length = len(self.value)
        vlen = len(tlvvalue)
        self.value = create_string_buffer(vlen)
        for i in range(0, vlen-1):
            self.value[i] =  chr(tlvvalue[i])

    def get_tlvtype(self):
        'Return the TLV type of this TLV object'
        return self.tlvtype;

    def get_tlvlen(self):
        'Return the length of this TLV value'
        return self.length;

    def get_tlvvalue(self):
        'Return the string buffer corresponding to the value of this TLV object'
        return self.value;

    def get_buf(self):
	'Abstract member function - returns the internal data representation of this TLV object'
        raise NotImplementedError("Abstract Member Function")

    @classmethod
    def from_buf(self):
	'Abstract member function - effectively a constructor which is passed the internal layout of this TLV object'
        raise NotImplementedError("Abstract Member Function")


class GenericTLV(TLV):
    '''Our local (generic) TLV implementation with 2 bytes for type and 2 for length - very simple.
       This is all implemented by our underlying C implementation'''
    def get_buf(self):
        'Return a string_buffer containing the value of this TLV field'
        bufsize = sizeof(guint16)+sizeof(guint16)+len(self.value)
        buf = create_string_buffer(bufsize)
        bufend= cast(buf, POINTER(guint8))+bufsize
        set_generic_tlv_type(buf, self.tlvtype, buf, bufend)
        set_generic_tlv_len(buf, self.tlvlen, bufend)
        set_generic_tlv_value(buf, self.value, bufend)
        return buf

    @classmethod
    def from_buf(Class, buf):
        'Construct a GenericTLV from a string_buffer containing the value to initalize it to'
        ptype = POINTER(guint8)
        bufend= cast(buf, ptype)+len(buf)
        tlvtype = get_generic_tlv_type(buf, bufend)
        tlvlen = get_generic_tlv_len(buf, bufend)
        valptr = cast(get_generic_tlv_value(buf, bufend), ptype);
        value = create_string_buffer(tlvlen)
        for i in range(0, vlen-1):
            value[i] =  chr(valptr[i])
        return Class(tlvtype, value)

class CDPTLV(TLV):
    '''A TLV implementation based on the Cisco TLV layout as used by their CDP protocol
       It has a checksum at the beginning followed by a sequence of one byte types and 2-byte lengths.
       This is all implemented by our underlying C code.'''

    @classmethod
    def from_buf(Class, buf):
        'Construct a CDPTLV from a string_buffer containing the value to initialize it to'
        ptype = POINTER(guint8)
        bufend= cast(buf, ptype)+len(buf)
        tlvtype = get_cdptlv_type(buf, bufend)
        tlvlen = get_cdptlv_len(buf, bufend)
        valptr = cast(get_cdptlv_value(buf, bufend), ptype);
        value = create_string_buffer(tlvlen)
        for i in range(0, vlen-1):
            value[i] =  chr(valptr[i])
        return Class(tlvtype, value)

class LLDPTLV(TLV):
    '''A TLV implementation based on the IEEE TLV layout as used by the LLDP protocol
       It has a 7-bit type followed by a 9-bit length field.
       This is all implemented by our underlying C code.'''
    @classmethod
    def from_buf(Class, buf):
        'Construct a LLDPTLV from a string_buffer containing the value to initialize it to'
        ptype = POINTER(guint8)
        bufend= cast(buf, ptype)+len(buf)
        tlvtype = get_lldp_tlv_type(buf, bufend)
        tlvlen = get_lldp_tlv_vlen(buf, bufend) # vlen is the length of the value portion only
        valptr = cast(get_lldp_tlv_value(buf, bufend), ptype);
        value = create_string_buffer(tlvlen)
        for i in range(0, vlen-1):
            value[i] =  chr(valptr[i])
        return Class(tlvtype, value)

class pyNetAddr:
    '''This class represents the Python version of our C-class @ref NetAddr - represented by the struct _NetAddr.
    '''
    def __init__(self, addrstring, port=None):
        '''This constructor needs a list of integers of the right length as its first argument.
        The length of the list determines the type of address generated.
         4 bytes == ipv4
         6 bytes == MAC address
         8 bytes == MAC address
         16 bytes == ipv6 address
        This is slightly sleazy but it should work for the forseeable future.
        '''
        alen = len(addrstring)
        assert alen >= 4
        addr = create_string_buffer(alen)
        for i in range(0, alen-1):
            addr[i] =  chr(addrstring[i])
        if alen == 4:		# ipv4
            if port == None:
                port = 0
            self._Cstruct = netaddr_ipv4_new(addr, port)
        elif alen == 16:	# ipv6
            if port == None:
                port = 0
            self._Cstruct = netaddr_ipv6_new(addrstring, port)
        elif alen == 6:		# "Normal" 48-bit MAC address
            assert port == None
            self._Cstruct = netaddr_mac48_new(addrstring)
        elif alen == 8:		# Extended 64-bit MAC address
            assert port == None
            self._Cstruct = netaddr_mac64_new(addrstring)
        else:
            raise ValueError("Invalid address length - not 4, 6, 8, or 16")

    def port(self):
        "Return the port (if any) for this pyNetAddr object"
	base=self._Cstruct[0]
        while (type(base) is not NetAddr):
	    base=base.baseclass
        return base.port(self._Cstruct)

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

    # Do we need to define an addrbody() member function?
    def __eq__(self, other):
        "Return True if the two pyNetAddrs are equal"
	base=self._Cstruct[0]
        while (type(base) is not NetAddr):
	    base=base.baseclass
        return base.equal(self._Cstruct, other._Cstruct)

    def __del__(self):
        "Free up the underlying Cstruct for this pyNetAddr object"
	base=self._Cstruct[0]
	# I have no idea why the type(base) is not NetAddr doesn't work here...
	# This 'hasattr' construct only works because we are a base C-class
        while (hasattr(base, 'baseclass')):
	    base=base.baseclass
        base.unref(self._Cstruct)


class pyFrame:
    '''This class represents the Python version of our C-class @ref Frame - represented by the struct _Frame.
    This class is a base class for several different pyFrame subclasses.
    Each of these various pyFrame subclasses have a corresponding C-class @ref Frame subclass.
    '''
    def __init__(self, initval, makeCstruct=True):
        "Initializer for the pyFrame object."
        try:
            frametype = initval.tlvtype
        except:
            frametype = int(initval)
	if makeCstruct:
            # If we don't do this, then a subclass __init__ function must do it instead...
            self._CStruct = frame_new(frametype, 0)

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

    def dataspace(self):
        "Return the amount of space this frame needs - is this always the same as framelen?"
	base=self._Cstruct[0]
        while (type(base) is not Frame):
	    base=base.baseclass
        return base.dataspace(self._Cstruct)

    def isvalid(self):
        "Return True if this Frame is valid"
	base=self._Cstruct[0]
        while (type(base) is not Frame):
	    base=base.baseclass
        return (int(base.isvalid(self._Cstruct)) != 0)

    def setvalue(self, value):
        'Assign a chunk of memory to the Value portion of this Frame'
        vlen = len(value)
        valbuf = create_string_buffer(vlen)
        for i in range(0, vlen-1):
            valbuf[i] =  chr(value[i])
	base=self._Cstruct[0]
        while (type(base) is not Frame):
	    base=base.baseclass
        base.setvalue(self._Cstruct, vlen, None)
        

    def dump(self, prefix):
        'Dump out this Frame (using C-class "dump" member function)'
	base=self._Cstruct[0]
        while (type(base) is not Frame):
	    base=base.baseclass
        base.dump(self._Cstruct, cast(prefix, c_char_p))

    def __del__(self):
        'Free up the underlying Cstruct for this pyFrame object.'
	base=self._Cstruct[0]
	# I have no idea why the type(base) is not Frame doesn't work here...
	# This 'hasattr' construct only works because we are a base C-class
        while (hasattr(base, 'baseclass')):
	    base=base.baseclass
        base.unref(self._Cstruct)

class pyAddrFrame(pyFrame):
    '''This class represents the Python version of our C-class AddrFrame - represented by the struct _AddrFrame.
    '''
    def __init__(self, frametype, addrstring, port=None):
        "Initializer for the pyAddrFrame object."
        pyFrame.__init__(self, frametype, makeCstruct=False)
        self._Cstruct = addrframe_new(frametype, 0);
        self._pyAddr = pyAddr(initval, port)
        self._Cstruct[0]._setnetaddr(self._Cstruct, self._pyAddr._Cstruct)

class pyCstringFrame(pyFrame):
    '''This class represents the Python version of our C-class CstringFrame - represented by the struct _CstringFrame
    This class represents a Frame standard NUL-terminated C string.
    '''
    def __init__(self, frametype, initval=None):
	'Constructor for pyCstringFrame object - initial value should be something that looks a lot like a Python string'
        self._Cstruct=cstringframe_new(frametype, 0)
        if initval != None:
            self.setvalue(initval)
            
    def setvalue(self, value):
	'Assign a Python String to our C-string TLV value'
        vlen = len(value)
        self._Cstruct[0].baseclass.setvalue(self._Cstruct, cast(value, c_char_p), vlen+1, cast(None, GDestroyNotify))

    def __str__(self) :
	'Convert the underlying C-string Value into a Python String.'
	vlen = self.framelen()-1 # Ignore the required 'C' NUL character at the end of the string
        rawret =  cast(self._Cstruct[0].baseclass.value, POINTER(c_char))
	EOS=chr(0)
	ret=""
	for i in range(0,vlen):
	    if rawret[i] == EOS:
		break;
	    ret += rawret[i]
        return ret


addr = pyNetAddr([10,10,10,10],80)
print "port is ", addr.port()
print "addrtype is ", addr.addrtype()
print "addrlen is ", addr.addrlen()
print pyNetAddr([10,10,10,10],80)
print pyNetAddr([10,10,10,10],8080).port()
Sframe = pyCstringFrame(100,"Hello, world.")
print ("Sframe is [%s]"% str(Sframe))
HhGttGframe = pyCstringFrame(100, str(42))
print ("Iframe is [%s]"% str(HhGttGframe))

#print clientlib.netaddr_ipv4_new(None)
