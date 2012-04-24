#!/usr/bin/python
'''
A collection of classes which wrap our @ref C-Classes and provide Pythonic interfaces to these C-classes.
'''

from AssimCtypes import *

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
    guint8 = POINTER(guint8)

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
    def from_buf(Class):
	'Abstract member function - effectively a constructor which is passed the underlying C structure'
        raise NotImplementedError("Abstract Member Function")


class GenericTLV(TLV):
    '''Our local (generic) TLV implementation with 2 bytes for type and 2 for length - very simple.
       This is all implemented by our underlying C implementation'''
    def get_buf(self):
        'Return a string_buffer containing the value of this TLV field'
        bufsize = sizeof(guint16)+sizeof(guint16)+len(self.value)
        buf = create_string_buffer(bufsize)
        bufend= cast(buf, cClass.guint8)+bufsize
        set_generic_tlv_type(buf, self.tlvtype, buf, bufend)
        set_generic_tlv_len(buf, self.tlvlen, bufend)
        set_generic_tlv_value(buf, self.value, bufend)
        return buf

    @classmethod
    def from_buf(Class, buf):
        'Construct a GenericTLV from a string_buffer containing the value to initalize it to'
        ptype = cClass.guint8
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
        ptype = cClass.guint8
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
        ptype = cClass.guint8
        bufend= cast(buf, ptype)+len(buf)
        tlvtype = get_lldp_tlv_type(buf, bufend)
        tlvlen = get_lldp_tlv_vlen(buf, bufend) # vlen is the length of the value portion only
        valptr = cast(get_lldp_tlv_value(buf, bufend), ptype);
        value = create_string_buffer(tlvlen)
        for i in range(0, vlen-1):
            value[i] =  chr(valptr[i])
        return Class(tlvtype, value)

class pyAssimObj:
    def __init__(self, Cstruct=None):
        'Create a base pyAssimObj object'
        self._Cstruct = None
        if (Cstruct is not None):
            assert type(Cstruct) is not int
            self._Cstruct = Cstruct
            return
        self._Cstruct = assimobj_new(0)

    def cclassname(self):
        return proj_class_classname(self._Cstruct)

    def __str__(self):
        'Convert this AssimObj into a printable string'
        base = self._Cstruct[0]
        while (type(base) is not AssimObj):
	    base=base.baseclass
        cstringret = base.toString(self._Cstruct)
        ret = string_at(cstringret)
        g_free(cstringret)
        return ret

    def __del__(self):
        'Free up the underlying Cstruct for this pyAssimObj object.'
        if self._Cstruct is None:
            return
	base=self._Cstruct[0]
	# I have no idea why the type(base) is not Frame doesn't work here...
	# This 'hasattr' construct only works because we are a base C-class
        while (hasattr(base, 'baseclass')):
	    base=base.baseclass
        base.unref(self._Cstruct)

    def _ref(self):
	base=self._Cstruct[0]
        while (type(base) is not AssimObj):
	    base=base.baseclass
        base.ref(self._Cstruct)

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
            self._Cstruct = Cstruct
            return
        alen = len(addrstring)
        addr = create_string_buffer(alen)
        #print "ADDRTYPE:", type(addr)
        for i in range(0, alen):
            asi = addrstring[i]
            if type(asi) is str:
                addr[i] = asi
            else:
                addr[i] = chr(asi)
        if port == None:
            port = 0
        if alen == 4:		# ipv4
            self._Cstruct = netaddr_ipv4_new(addr, port)
        elif alen == 16:	# ipv6
            self._Cstruct = netaddr_ipv6_new(addr, port)
        elif alen == 6:		# "Normal" 48-bit MAC address
            assert port == 0
            self._Cstruct = netaddr_mac48_new(addr)
        elif alen == 8:		# Extended 64-bit MAC address
            assert port == 0
            self._Cstruct = netaddr_mac64_new(addr)
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

    def __eq__(self, rhs):
        'Compare this pyNetAddr to another pyNetAddr'
        lhsbase = self._Cstruct[0]
        while (type(lhsbase) is not NetAddr):
	    lhsbase=lhsbase.baseclass
        return lhsbase.equal(self._Cstruct, rhs._Cstruct)
         

    # Do we need to define an addrbody() member function?
    def __eq__(self, other):
        "Return True if the two pyNetAddrs are equal"
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
    Similarly, I don't think the Python level code needs the valuefinalize, ref and unref member functions.
    The __del__ member function below should deal with all those things one way or another...
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
            self._Cstruct = frame_new(frametype, 0)
        else:
            self._Cstruct = Cstruct

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
        'Return a C-style pointer (as an int) to the underlying raw TLV data (if any)'
	base=self._Cstruct[0]
        while (type(base)is not Frame):
	    base=base.baseclass
        return cast(base.value, c_char_p)

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

    @staticmethod
    def Cstruct2Frame(frameptr):
        frameptr = cast(frameptr, cClass.Frame)
        frametype = frameptr[0].type
        Cclassname = proj_class_classname(frameptr)
        pyclassname = "py" + Cclassname
        frameptr[0].baseclass.ref(frameptr)
        if Cclassname == "NetAddr":
            statement = "%s(%d, None, Cstruct=cast(frameptr, cClass.%s))" % (pyclassname, frametype, Cclassname)
        else:
            statement = "%s(%d, Cstruct=cast(frameptr, cClass.%s))" % (pyclassname, frametype, Cclassname)
        #print "EVAL:", statement
        return eval(statement)

class pyAddrFrame(pyFrame):
    '''This class represents the Python version of our C-class AddrFrame - represented by the struct _AddrFrame.
    '''
    def __init__(self, frametype, addrstring=None, port=None, Cstruct=None):
        "Initializer for the pyAddrFrame object."
        self._Cstruct = None # Keep error legs from complaining.
        if Cstruct is None:
            self._pyNetAddr = pyNetAddr(addrstring, port=port)
            Cstruct = addrframe_new(frametype, 0);
            if addrstring is not None:
                Cstruct[0].setnetaddr(Cstruct, self._pyNetAddr._Cstruct)
        else:
            assert port is None
            assert addrstring is None
            addrlen = Cstruct[0].baseclass.length
            assert addrlen == 4 or addrlen == 6 or addrlen == 8 or addrlen == 16, ("addrlen is %d" % addrlen)
            addrstr = Cstruct[0].baseclass.value
            addrstring = create_string_buffer(addrlen)
            memmove(addrstring, addrstr, addrlen)
            self._pyNetAddr = pyNetAddr(addrstring, port=None)
        pyFrame.__init__(self, frametype, Cstruct)

    def addrtype(self):
        return self._pyNetAddr.addrtype()

    def getnetaddr(self):
        return self._pyNetAddr

    def __str__(self):
       return ("pyAddrFrame(%d, (%s))" % (self.frametype(), str(self._pyNetAddr)))


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
        return str(int(self))

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
       return "(%d,%d)" % (self.getqid(), self.getreqid())

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
        self._Cstruct = Cstruct

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
        curframe = self._Cstruct[0].framelist;
        count=0
        while curframe:
            count += 1
            curframe=g_slist_next(curframe)
        return count

    def iter(self):
        'Generator yielding the set of pyFrames in this pyFrameSet'
        curframe = self._Cstruct[0].framelist;
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
        result = "{"
        for frame in self.iter():
            if result != "{":
                result += ", "
            result += str(frame)
        result += "}"
        return result


class pyPacketDecoder(pyAssimObj):
    'Class for Decoding packets - for returning an array of FrameSets from a physical packet.'
    def __init__(self, FrameMap=None, Cstruct=None):
        'Initializer for pyPacketDecoder'
        if Cstruct is None:
            Cstruct=packetdecoder_new(0, None, 0)
        self._Cstruct = Cstruct

    def fslist_from_pktdata(self, pktlocation):
        'Make a list of FrameSets out of a packet.'
        frameset_list = []
	base=self._Cstruct[0]
        while (type(base)is not PacketDecoder):
	    base=base.baseclass
        fs_gslistint = base.pktdata_to_framesetlist(self._Cstruct, pktlocation[0], pktlocation[1])
        fs_gslist = cast(fs_gslistint, POINTER(GSList))
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
        if Cstruct is None and isinstance(init, str):
            Cstruct = configcontext_new_JSON_string(init)
        if Cstruct is None:
            Cstruct=configcontext_new(0)
        self._Cstruct = Cstruct
        if init is not None and not isinstance(init, str):
            for key in init.keys():
                self[key] = init[key]

    def getint(self, name):
        'Return the integer associated with "name"'
        return self._Cstruct[0].getint(self._Cstruct, name)

    def setint(self, name, value):
        'Set the integer associated with "name"'
        self._Cstruct[0].setint(self._Cstruct, name, value)

    def getaddr(self, name):
        'Return the NetAddr associated with "name"'
        naddr = self._Cstruct[0].getaddr(self._Cstruct, name)
        if naddr:
            naddr = cast(naddr, cClass.NetAddr)
            naddr[0].baseclass.ref(naddr)
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
            caddr[0].baseclass.ref(caddr)
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

    def __getitem__(self, name):
        'Return a value associated with "name"'
        try:
            ret = self.getconfig(name)
            return ret
        except (IndexError):
            pass
        try:
            ret = self.getstring(name)
            return ret
        except (IndexError):
            pass
        try:
            ret = self.getaddr(name)
            return ret
        except (IndexError):
            pass
        try:
            ret = self.getframe(name)
            return ret
        except (IndexError):
            pass
        return self.getint(name)

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
