/**
 * @file
 * @brief Implements CompressFrame Object - the comprssion frame
 * @details Implements the CompressFrame object for on-the-wire compression and decompression.
 * This includes the code to link to the available compression libraries - currently only zlib (-lz).
 *
 * @author  Alan Robertson <alanr@unix.sh> - Copyright &copy; 2013 - Assimilation Systems Limited
 * Free support is available from the Assimilation Project community - http://assimproj.org
 * Paid support is available from Assimilation Systems Limited - http://assimilationsystems.com
 *
 * @n
 *  This file is part of the Assimilation Project.
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

///@defgroup CompressFrame CompressFrame class
/// Class implementing Compression/decompression on the wire.
///@{
///@ingroup C_Classes
///@ingroup Frame


///@}
#define KBYTES(n)	((n)*1024)
/// In practice, our max JSON decompressed size is under 325K, so 1M seems safe
/// more or less not matter what compression method one uses -- on JSON...
#define	MAXUNCOMPRESSEDSIZE	KBYTES(1024)

#include  <glib.h>
#include  <fcntl.h>
#include  <memory.h>
#include  <malloc.h>
#include  <compressframe.h>
#include  <frameset.h>
#include  <generic_tlv_min.h>
#include  <tlvhelper.h>

#ifdef HAVE_ZLIB_H
#	define ZLIB_CONST 1 /* Enable const definitions where appropriate */
#	include  <zlib.h>
#endif /* HAVE_ZLIB_H */
#if ZLIB_VER_MAJOR > 1 || ZLIB_VER_MINOR > 2 || ZLIB_VER_REVISION > 7
	// At least version 1.2.8 has the ZLIB_CONST #define to fix this
#	define ZLIB_CONSTANT(e)	((const guint8*)(e))
#else
	// Older zlib header files didn't declare things const like they should
	// So we use a sleazy trick to deal with the broken header file :-(
#	define ZLIB_CONSTANT(e)	((guint8*)(GSIZE_TO_POINTER(GPOINTER_TO_SIZE(e))))
#endif

DEBUGDECLARATIONS;

FSTATIC void _compressframe_finalize(AssimObj * self);
FSTATIC void _compressframe_setvalue(Frame *, gpointer, guint32, GDestroyNotify valnotify);
FSTATIC void _compressframe_updatedata(Frame *, gpointer, gconstpointer, FrameSet*);
FSTATIC gboolean _compressframe_isvalid(const Frame *, gconstpointer,	gconstpointer);
FSTATIC int	_compressframe_findmethod(int method);
FSTATIC gchar * _compressframe_toString(gconstpointer);
FSTATIC	void	assim_dump_bytes(char * prefix, gconstpointer p, int len);

#define COMPFRAMESIZE	4	// one-byte compression type + 3 byte uncompressed length

#ifdef HAVE_ZLIB_H
FSTATIC gpointer z_compressbuf(gconstpointer inbuf, int insize, int offset, int maxout, int *actualsize, int level);
FSTATIC gpointer z_decompressbuf(gconstpointer inbuf, int insize, int offset, int maxout, int *uncompsize);
#endif /* HAVE_ZLIB_H */

/// Set of all know compression methods
static struct compression_types {
	guint8	   compression_type;		///< Type of compression
	gpointer (*compress)(gconstpointer inbuf, int insize, int offset, int maxout, int *actualsize, int level);
						///< Compression function for this compression type
	gpointer (*decompress)(gconstpointer inbuf, int insize, int offset, int maxout, int *uncompsize);
						///< Decompression function for this compression type
	const char*	name;
}allcompressions [] = {
#ifdef HAVE_ZLIB_H
	{COMPRESS_ZLIB,	z_compressbuf,		z_decompressbuf, "zlib"},
#endif
};

#include <stdio.h>
FSTATIC	void
assim_dump_bytes(char * prefix, gconstpointer p, int len)
{
	int j;
	const char * space = "";
	fprintf(stderr, "%s", prefix);
	
	for (j=0; j < len; ++j) {
		fprintf(stderr, "%s%02x", space, *(((const guint8*)p)+j));
		space=" ";
	}
	fprintf(stderr, " [%d bytes]\n", len);
}
FSTATIC int
_compressframe_findmethod(int method)
{
	gsize	j;
	for (j=0; j < DIMOF(allcompressions); ++j) {
		if (method == allcompressions[j].compression_type) {
			return j;
		}
	}
	return -1;
}

//static void(*parentfinalize)(AssimObj*) = NULL;
CompressFrame*
compressframe_new(guint16 frame_type, guint16 compression_method)
{
	Frame*		fself;
	CompressFrame*	self;
	int		cmpindex;

	BINDDEBUG(CompressFrame);

	if ((cmpindex = _compressframe_findmethod(compression_method)) < 0) {
		g_warning("%s.%d: Unknown compression type: %d"
		,	__FUNCTION__, __LINE__, compression_method);
		return(NULL);
	}
	fself = frame_new(frame_type, sizeof(CompressFrame));
	self = NEWSUBCLASS(CompressFrame, fself);
	self->compression_method = compression_method;
	self->compression_index = cmpindex;
	self->compression_threshold = DEFAULT_COMPRESSION_THRESHOLD;
	fself->length = COMPFRAMESIZE;
	fself->setvalue = _compressframe_setvalue;
	fself->updatedata = _compressframe_updatedata;
	fself->isvalid = _compressframe_isvalid;
	fself->baseclass.toString = _compressframe_toString;
#if 0
	if (NULL == parentfinalize) {
		parentfinalize = fself->baseclass._finalize;
	}
	fself->baseclass->_finalize = _compressframe_finalize;
#endif
	return self;
}

CompressFrame*
compressframe_new_string(guint16 frame_type, const char* compression_name)
{
	gsize	j;
	for (j=0; j < DIMOF(allcompressions); ++j) {
		if (strcmp(compression_name, allcompressions[j].name) == 0) {
			return compressframe_new(frame_type, allcompressions[j].compression_type);
		}
	}
	g_return_val_if_reached(NULL);
}
/// Return TRUE if this is a valid CompressFrame - either an object or on-the-wire version
FSTATIC gboolean
_compressframe_isvalid(const Frame *fself, gconstpointer tlvstart, gconstpointer pktend)
{
	const CompressFrame*	self = CASTTOCONSTCLASS(CompressFrame, fself);
	guint8			compresstype;
	guint32			origlen;
	const guint8*		valptr;
	if (NULL == tlvstart) {
		return ((gsize)self->compression_index) < DIMOF(allcompressions)
	&&	allcompressions[self->compression_index].compression_type == self->compression_method;
	}
	
	if (	((const guint8*)pktend-(const guint8*)tlvstart) < 12
	|| 	get_generic_tlv_len(tlvstart, pktend) <= 8) {
		return FALSE;
	}
	valptr = get_generic_tlv_value(tlvstart, pktend);
	compresstype = tlv_get_guint8(valptr, pktend);
	g_return_val_if_fail(_compressframe_findmethod(compresstype) >= 0, FALSE);
	origlen = tlv_get_guint24(valptr+1, pktend);
	// Trying to avoid a DOS attack using huge packets
	g_return_val_if_fail(origlen <= MAXUNCOMPRESSEDSIZE || origlen >= 16, FALSE);
	return TRUE;
}

FSTATIC void
_compressframe_setvalue(Frame *f, gpointer value, guint32 len, GDestroyNotify valnotify)
{
	(void)f;
	(void)value;
	(void)len;
	(void)valnotify;
	g_warning("%s:%d: Not possible to set the value of a CompressFrame", __FUNCTION__, __LINE__);
}

FSTATIC gchar *
_compressframe_toString(gconstpointer aself)
{
	const CompressFrame*	self = CASTTOCONSTCLASS(CompressFrame, aself);
	double		ratio;
	if (self->baseclass.length <= 4) {
		return g_strdup_printf("CompressFrame(frametype:%d, method:%s)"
		,	self->baseclass.type, allcompressions[self->compression_index].name);
	}
	ratio = (double)self->decompressed_size / ((double)(self->baseclass.length-4));
	return g_strdup_printf("CompressFrame(frametype:%d, method:%s, len:%d uncompsize:%d, ratio:%0.2f:1)"
	,	self->baseclass.type, allcompressions[self->compression_index].name
	,	self->baseclass.length, self->decompressed_size, ratio);
}


///
/// We update the data in the packet from our CompressFrame object AND ALSO have the
/// side-effect of compressing all the frames already put into the packet.  Note that
/// this only works because we always construct the packet from the end back to the
/// beginning.
FSTATIC void
_compressframe_updatedata(Frame *f,		//<[in] Our frame ("self")
			  gpointer tlvstart,	//<[in] Beginning of where to put our data (not really)
		          gconstpointer pktend,	//<[out] Where to put the final data (not really)
			  FrameSet* fs)		//<[in/out] Frameset to update the "packet" for
						//< once we compress this data
{
	CompressFrame*	self		= CASTTOCLASS(CompressFrame, f);
	guint8*		pktstart	= fs->packet;
	guint8*		tlvstart8	= tlvstart;
	const guint8*	pktend8		= pktend;
	guint8*		valptr;
	guint32		ouroffset;	// Offset to beginning of our packet
	guint32		cmpoffset;	// Offset to beginning of compressed data
	guint8*		newpacket;
	guint8*		newpktend;
	int		compressedsize;
	

	// Now on to our side effect - compressing the frames that follow us...
	ouroffset = (tlvstart8-pktstart);
	cmpoffset = ouroffset + COMPFRAMESIZE+FRAME_INITSIZE;
	newpacket = allcompressions[self->compression_index].compress
		(pktstart, pktend8-pktstart, cmpoffset, MAXUDPSIZE, &compressedsize, 0);
	self->decompressed_size = (pktend8 - pktstart) - cmpoffset;

	if (NULL == newpacket) {
		g_warning("%s:%d: Unable to compress %d byte packet to %d byte UDP packet"
		,	__FUNCTION__, __LINE__, self->decompressed_size, MAXUDPSIZE);
	}
	newpktend = newpacket + compressedsize;
	// Write our type and length into the (new) packet
	set_generic_tlv_type(newpacket+ouroffset, f->type, newpktend);
	self->baseclass.length = (compressedsize-cmpoffset) + COMPFRAMESIZE;
	set_generic_tlv_len(newpacket+ouroffset, self->baseclass.length, newpktend);
	valptr = get_generic_tlv_nonconst_value(newpacket+ouroffset, newpktend);
	// Our TLV value consists of the compression method followed by a 3 byte
	// packet length, followed by the compressed data (already in "newpacket").
	// This restricts us to a 16M decompressed original packet.
	// Since this has to compress down to a single UDP packet,
	// this a very reasonable assumption...
	// In practice, our JSON seems to be limited to about 300K decompressed.
	tlv_set_guint8(valptr, self->compression_method, newpktend);
	tlv_set_guint24(valptr+1, self->decompressed_size, newpktend);
	fs->packet = newpacket;
	fs->pktend = newpktend;
}

#define	COMPRESSFRAMEMIN	4
FSTATIC Frame*
compressframe_tlvconstructor(gpointer tlvstart,		///<[in] Start of the compression frame
			     gconstpointer pktend,	///<[in] First byte past the end of the packet
		             gpointer* newpacket,	///<[out] replacement packet
		             gpointer* newpacketend)	///<[out] end of replacement packet
{
	const guint8*	pktend8			= pktend;
	const guint8*	tlvstart8		= tlvstart;
	const guint8*	packet;			///< Start of compessed data
	const guint8*	valueptr;		///< Pointer to TLV Value
	guint32		cmppktsize;		///< Compressed packet size
	guint8		compression_type;	///< Type of compression from Value
	guint32		decompressed_size;	///< Size after decompression (from Value)
	int		actual_size;		///< Size after decompression (from decompression)
	int		compression_index;	///< Which compression method are we using?
						///< This is an index into allcompressions
	guint16		frametype;		///< Frametype of this frame - TLV Type
	CompressFrame*	ret;			///< Return value
	/* Our four bytes of real data are:
	 * 	1-byte compression type
	 * 	3-byte decompressed size
	 */
	frametype = get_generic_tlv_type(tlvstart, pktend);
	valueptr = get_generic_tlv_value(tlvstart, pktend);
	compression_type = tlv_get_guint8(valueptr, pktend);
	decompressed_size = tlv_get_guint24(valueptr+1, pktend);
	compression_index = _compressframe_findmethod(compression_type);
	// Trying to mitigate possible DOS attack using huge packets
	// In practice, our max JSON decompressed size is under 325K
	g_return_val_if_fail(decompressed_size <= MAXUNCOMPRESSEDSIZE, NULL);
	g_return_val_if_fail(decompressed_size > 16, NULL);
	g_return_val_if_fail(compression_index >= 0, NULL);
	packet = valueptr + COMPRESSFRAMEMIN;

	cmppktsize = pktend8 - tlvstart8;	// Compressed packet size
	
	*newpacket = allcompressions[compression_index].decompress
		(packet, cmppktsize, 0, decompressed_size, &actual_size);
	g_return_val_if_fail(*newpacket != NULL, NULL);
	*newpacketend = (guint8*)*newpacket + actual_size;

	ret = compressframe_new(frametype, compression_type);
	g_return_val_if_fail(ret != NULL, NULL);
	ret->decompressed_size = decompressed_size;
	return &ret->baseclass;
}

#ifdef HAVE_ZLIB_H
/// Single-packet compression using zlib (-lz).
/// Our goal here is to compress the data as cheaply as possible so that the <i>total</i>
/// output size is less than or equal to 'maxout' bytes.
/// Maxout is normally the maximum size of a UDP packet.
/// This is our definition of optimal compression - the cheapest that fits.
gpointer
z_compressbuf(gconstpointer inbuf	///<[in] Input buffer
,	int insize			///<[in] size of 'inbuf'
,	int offset			///<[in] Offset to beginning of data to be compressed
,	int maxout			///<[in] Maximum size of compressed output [UDP packet size]
,	int *actualsize			///<[out] Actual size of compressed output
,	int level)			///<[in] Compression level: (normally zero)
{

	guint8*		outbuf;
	z_stream	stream;
	int		ret;
#if 0
	int		space;
	double		ratio;
#endif

	// Compute compression level
	// If our guess doesn't work, we'll escalate to max compression
	// This adds compression expense, this is mostly in the nanoprobe side, so we don't much care.
	if (level < 1) {
		if (insize < KBYTES(189)) {
			level = 1;
		}else if (insize < KBYTES(225)) {
			level = 6;
		}else{
			level = 9;
		}
	}

	/* Set up libz */
	stream.zalloc = Z_NULL;
	stream.zfree = Z_NULL;
	stream.opaque = Z_NULL;
	ret = deflateInit(&stream, level);

	if (ret != Z_OK) {
		g_warning("%s.%d: OOPS, got a deflateInit return of %d"
		,	__FUNCTION__, __LINE__, ret);
		return NULL;
	}
#if 0
	outbuf = g_malloc(maxout);
#else
	outbuf = calloc(maxout, 1);
#endif
	if (NULL == outbuf) {
		g_warning("%s.%d: OOPS out of space.",	__FUNCTION__, __LINE__);
		return NULL;
	}
	stream.avail_in = insize-offset;
	stream.next_in = ZLIB_CONSTANT(inbuf)+offset;
	stream.avail_out = maxout-offset;
	stream.next_out = outbuf+offset;

	/* Compress it */
	ret = deflate(&stream, Z_FINISH);
	if (ret != Z_STREAM_END) {
		g_free(outbuf);
		if (level < 9) {
			return z_compressbuf(inbuf, insize, offset, maxout, actualsize, 9);
		}
		g_warning("%s.%d: Got return code %d from deflate."
		,	__FUNCTION__, __LINE__, ret);
		return NULL;
	}
#if 0
	space = insize - stream.avail_out;
	ratio = ((double)stream.total_in/((double)stream.total_out));
	//return 0;
	fprintf(stderr, "Compressing %ld bytes into %ld bytes with level %d ratio %.2f:1\n", stream.total_in
	, stream.total_out, level, ratio);
#endif
	(void)deflateEnd(&stream);
	*actualsize = stream.total_out + offset;
	outbuf = g_realloc(outbuf, *actualsize);
	return outbuf;
}

/// Single-packet decompression using zlib (-lz).
/// Return NULL on failure.
gpointer
z_decompressbuf(gconstpointer inbuf	///<[in] compressed input buffer
,	int insize			///<[in] size of compressed input buffer
,	int offset			///<[in] start of compressed data - the first "offset" bytes
					///< from inbuf are copied into output w/o decompression
,	int maxout			///<[in] maximum size of decompressed output.
					///< nice if it's decompressed size if you know it.
,	int *uncompsize)		///<[out] actual decompressed size
{
	gpointer	outbuf;
	int		outsize;
	int		ret;
	z_stream	stream;
	/* Set up libz */
	stream.zalloc = Z_NULL;
	stream.zfree = Z_NULL;
	stream.opaque = Z_NULL;
	stream.avail_in = insize-offset;
	stream.next_in = ZLIB_CONSTANT(inbuf) + offset;
	g_return_val_if_fail (Z_OK == inflateInit(&stream), NULL);
	outbuf = g_malloc(maxout);
	if (offset > 0) {
		memcpy(outbuf, inbuf, offset);
	}
	stream.avail_out = maxout;
	stream.next_out = ((guint8 *)outbuf) + offset;
	// Decompress our input buffer.
	ret = inflate(&stream, Z_FINISH);
	(void)inflateEnd(&stream);
	if (ret != Z_STREAM_END) {
		g_warning( "%s.%d: GOT inflate RETURN OF %d"
		,	__FUNCTION__, __LINE__, ret);
		g_free(outbuf);
		return NULL;
	}
	outsize = maxout - stream.avail_out;
	if (outsize > maxout) {
		outbuf = g_realloc(outbuf, outsize);
	}
	(void)inflateEnd(&stream);
	*uncompsize = outsize;
	return outbuf;
}
#endif /* HAVE_ZLIB_H */
