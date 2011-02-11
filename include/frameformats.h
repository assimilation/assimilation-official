/**
 * @file
 * @brief Header file defining the data layouts for our Frames.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
/**
@addtogroup FrameFormats
@{
  Below is the set of frame formats and corresponding #defines
  This section will document the format of the individual frame types.
  The first frame in a frameset must be a signature frame.
  If an encryption frame is present, it must be the  frame in the frameset.
  If a compression frame is present, it must occur after the encryption frame
  if present, or after the signature frame, if there is no encryption frame.
 
  The final frame in a frameset must be an End frame (which will be
  added automatically).
@}
*/
/**
@defgroup IndividualFrameFormats Individual 'Frame' data types and layouts on the wire.
@{
Below is the set of individual frame types and data layouts.
@ingroup FrameFormats
@{
*/

/**
  End (frametype 0) Frame format - this frame is always last in a frameset.
<PRE>
+---------------+----------+
| frametype = 0 | f_length |
|   (16 bits)   |    0     |
+---------------+----------+
</PRE>
The last frame in a frameset is required to be an End frame.
End frames are of type zero and have length zero.
*/
#define	FRAMETYPE_END		0
/**
  Digital Signature (frametype 1) Frame Format - this frame is always first in a frameset
<PRE>
+---------------+-----------+-----------------+--------------------+
| frametype = 1 | f_length  | signature-type  | digital signature  |
|   (16 bits)   | (16-bits) | (16 bits)       | (f_length-2 bytes) |
+---------------+-----------+-----------------+--------------------+
</PRE>
The signature frame (<b>frametype = 1</b>) is mandatory and must be the first
frame in the frameset.
The digital signature computed in the digital signature field is computed
on all the bytes in the frameset beginning with the first byte after
the end of this frame, extending through and including the last byte of the frameset.
Note that this will include the encryption frame if present.
The format and length of the digital signature depends on the type of signature.
*/
#define	FRAMETYPE_SIG		1
/**
Encryption (frametype 2) Frame Format - this optional frame is always second in a frameset - when present.
<PRE>
+---------------+-----------+------------------------+
| frametype = 2 | f_length  | encryption information |
|   (16 bits)   | (16-bits) |    (f_length bytes)    |
+---------------+-----------+------------------------+
</PRE>
If an encryption frame is present (<b>frametype = 2</b>) it must be the second
frame in the frameset.  All frames in the frameset after this frame
are encrypted according information in the encryption information value segment.
The format of the encryption information value segment is not yet defined,
and will likely depend on the type of encryption method employed.
*/
#define	FRAMETYPE_CRYPT		2
/**
Compression (frametype 3) Frame Format - this optional frame is is either second or third in a frameset - when present.  It is second when there is no encryption frame, and third when there is an encryption frame.
<PRE>
+---------------+-----------+------------------------+
| frametype = 3 | f_length  | compression information |
|   (16 bits)   | (16-bits) |    (f_length bytes)    |
+---------------+-----------+------------------------+
</PRE>
If a compression frame is present (<b>frametype = 2</b>) it must be the second
or third frame in the frameset, and can only be preceded by a @ref FRAMETYPE_SIG
and @ref FRAMETYPE_CRYPT frames.
When this frame is present, then all the frames following
are compreseed according information in the compression information value segment.
The format of the compression information value segment will likely be a
single integer saying which compression method was used.
*/
#define	FRAMETYPE_COMPRESS		3
/**
  Request ID (frametype 4) Frame Format - this is basically a transaction sequence number
<PRE>
+---------------+---------------+-------------+-----------+
| frametype = 4 | f_length = 8  |  request id | queue id  |
|   (16 bits)   |   (16-bits)   |  (8 bytes)  | (2 bytes) |
+---------------+---------------+-------------+-----------+
</PRE>
Requests from the central authority are identified by a request id
(basically a sequence number) and a queue id.
The combination of the two is unique over a relatively long period of time - at least days.
Notifications from clients are sent with queue id 0, which will never be used by the
central authority.
At least that's what I think now ;-)

This frame type is used in only in request.  When included as part of a request frameset,
I may need to define some bit to be turned on in the flags indicating that this is a request so
that it will be repeated until a corresponding REPLYID is received.
*/
#define	FRAMETYPE_REQID		4

/**
  Reply ID (frametype 5) Frame Format - this is basically the transaction sequence number of a request
  being replied to.
<PRE>
+---------------+---------------+-------------+-----------+
| frametype = 5 | f_length = 8  |  request id | queue id  |
|   (16 bits)   |   (16-bits)   |  (8 bytes)  | (2 bytes) |
+---------------+---------------+-------------+-----------+
</PRE>
Requests from the central authority are identified by a request id
(basically a sequence number) and a queue id.
The combination of the two is unique over a relatively long period of time - at least a week.
Notifications from clients are sent with queue id 0, which will never be used by the
central authority.
At least that's what I think now ;-)
Note that this frame format is identical to that of a @ref FRAMETYPE_REQID (request id)
*/
#define	FRAMETYPE_REPLYID	5

/**
  Client Packet(frametype 6) Frame Format - this is what packets are encapsulated in.
<PRE>
+---------------+----------------+------------------+
| frametype = 6 | f_length = 'n' |  raw packet data |
|   (16 bits)   |   (16-bits)    |    ('n' bytes)   |
+---------------+----------------+------------------+
</PRE>
This frame format is normally used for a CDP or LLDP packet.
The data is kept exactly as it was received from the
network interface via libpcap.
*/
#define	FRAMETYPE_PKTDATA	6

/**
  Wall Clock time(frametype 7) Frame Format - 64-bit local time.
<PRE>
+---------------+--------------+--------------------------------+
| frametype = 7 | f_length = 8 | g_get_real_time() return value |
|   (16 bits)   |   (16-bits)  |      (8 bytes / 64 bits)       |
+---------------+--------------+--------------------------------+
</PRE>
This frame provides local time on the sending system
as gotten from the g_get_real_time() call - which
is a 64-bit time measured in microseconds.
Its corresponding @ref Frame class is @ref IntFrame.
*/
#define	FRAMETYPE_WALLCLOCK	7

/**
  Interface name (frametype 8) Frame Format - interface name as a string.
<PRE>
+---------------+----------------+----------------+
| frametype = 8 | f_length = 'n' | interface name |
|   (16 bits)   |    (16-bits)   |   (string)     |
+---------------+----------------+----------------+
</PRE>
This frame provides the name of the network interface
associated with the FrameSet.
*/
#define	FRAMETYPE_INTERFACE	8
///@}
///@}
