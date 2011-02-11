/**
@file 
@page InfrastructureArch Infrastructure Architecture
@section EventDrivenProgramming Event Driven Programming
Most of the core code in this project is event driven - that is, it does little or nothing unless
an event happens which triggers it to take action.
To manage this kind of program it is helpful to have an dispatcher of some kind to 
observe events and dispatch the appropriate code to handle a given event.
For this purpose we use the glib
<a href="http://library.gnome.org/devel/glib/unstable/glib-The-Main-Event-Loop.html#glib-The-Main-Event-Loop.description">
main event loop</a> construct.
<a href="http://library.gnome.org/devel/glib/unstable/">Glib</a> is a base library
used by the GTK+ graphics library, but glib has nothing to do with graphics,
and is available on every UNIX-like platform and also Windows.
In addition, Glib is not related to the GNU C library - glibc.  Sorry for the confusion.
@section WireDataFormats Data Formats on the wire
@{
Our packet formats are based on the <a href="http://en.wikipedia.org/wiki/Type-length-value">TLV</a>
(Type, Length, Value) concept found in a variety of protocols.
I started this project looking at the LLDP and CDP protocols,
and am pretty happy with how LLDP is organized - and it is reasonably
consistent with my past methodology, where I used name/value pairs and netstring formats.
Both have the property of being self-describing.
Having the packets be self-describing is vital, as the maintenance of thousands of servers with
non-identical versions of software is otherwise impossible.
TLV formats are much simpler and more compact than formats like XML.

I also want the packets to be efficient, with the ability to piggyback acknowledgements onto requests and so on.
In my current view, there would be a nesting a minimum of three layers of hierarchy in a packet.
The bottom two layers in the hierarchy are based on a TLV (Type, Length, Value) paradigm - similar to LLDP and CDP.

I refer to them as:
 - datagram - the collection of data sent in a single UDP datagram.  Each datagram consists of one or more @ref FrameSet "FrameSet"s.
 - @ref FrameSet "FrameSet" - this is the "logical packet".  Each frameset is a collection of one or more frames. It is at the frameset layer
 that packet sequence numbers appear and retransmissions are accomplished.
 In addition, this layer is the place where (optional) TLV entries indicating digital signatures, compression and encryption can be included.
 - @ref Frame "Frame" - this is the lowest level of TLV entries.

Since the type of each packet is known, and the structure is flexible, it is possible to include more
layers of hierarchy in the data than this.

@section C_TypeSystem  C Class System
@{
Our low-level code is written in C - so it is portable, and so that it is as small as possible.
However, parts of the <a href="http://library.gnome.org/devel/glib/unstable/">Glib</a> library
are very object-oriented, with base classes, derived classes and so on all in C.
In addition it makes extensive use of <b>void *</b> (or <b>gpointer</b>) pointers - which are
not at all type safe.
To deal with these problems and make the code much easier to debug and catch errors, 
we created a small Class management system for C.
The details of these capabilities are documented by the @ref ProjectClass documentation.

When you create an object, one associates an object with a type, typically using either the
@ref MALLOCCLASS or @ref MALLOCBASECLASS macros.  These macros record entries for those items
indicating what the class of the object was when it was created.  For the case where a base class constructor
(like @ref frame_new()) exists which allows mallocing the space for the a specific type of subclass object,
then one can use  @ref proj_class_register_subclassed() to register this object as being subclassed
from its original class.  This also registers that the <i>subclass</i> <b>ISA</b> <i>superclass</i> for
all such objects.

When one wants to cast a gpointer into one of these classes, one uses the @ref CASTTOCLASS
macro to cast it to the desired class.
This enables the class system will check that the object is of the proper class (type) to be cast
to that new class.

When one frees such an object, one uses the FREECLASSOBJ() macro.

Following these rules enables the system to track our major uses of memory to help find wrong
type errors, and can be used to help locate memory leaks, since the number of objects
of each of our major classes is tracked in this way.
@}
*/
