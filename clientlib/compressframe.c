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

#include  <glib.h>
#include  <fcntl.h>
#include  <memory.h>
#include  <compressframe.h>
#include  <frameset.h>
#include  <generic_tlv_min.h>
#include  <tlvhelper.h>

#if HAVE_ZLIB_H
#	include  <zlib.h>
#endif /* HAVE_ZLIB_H */

DEBUGDECLARATIONS;

FSTATIC void _compressframe_finalize(AssimObj * self);
FSTATIC gsize _compressframe_dataspace(const Frame* f);
FSTATIC void _compressframe_setvalue(Frame *, gpointer, guint16, GDestroyNotify valnotify);
FSTATIC void _compressframe_updatedata(Frame *, gpointer, gconstpointer, FrameSet*);
FSTATIC gboolean _compressframe_isvalid(const Frame *, gconstpointer,	gconstpointer);
FSTATIC int	_compressframe_findmethod(int method);

#if HAVE_ZLIB_H
FSTATIC gpointer z_compressbuf(gpointer inbuf, int insize, int offset, int maxout, int *actualsize, int level);
FSTATIC gpointer z_decompressbuf(gpointer inbuf, int insize, int offset, int maxout, int *uncompsize);
#endif /* HAVE_ZLIB_H */

/// Set of all know compression methods
static struct compression_types {
	guint8	   compression_type;		///< Type of compression
	gpointer (*compress)(gpointer inbuf, int insize, int offset, int maxout, int *actualsize, int level);
						///< Compression function for this compression type
	gpointer (*decompress)(gpointer inbuf, int insize, int offset, int maxout, int *uncompsize);
						///< Decompression function for this compression type
}allcompressions [] = {
#if HAVE_ZLIB_H
	{COMPRESS_ZLIB,	z_compressbuf,		z_decompressbuf},
#endif
};

FSTATIC int
_compressframe_findmethod(int method)
{
	unsigned	j;
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

	if ((cmpindex = _compressframe_findmethod(compression_method)) >= 0) {
		g_warning("%s.%d: Unknown compression type: %d"
		,	__FUNCTION__, __LINE__, compression_method);
		return(NULL);
	}
	fself = frame_new(frame_type, sizeof(CompressFrame));
	self = NEWSUBCLASS(CompressFrame, fself);
	self->compression_index = cmpindex;
	fself->length = 4;
	fself->dataspace = _compressframe_dataspace;
	fself->setvalue = _compressframe_setvalue;
	fself->updatedata = _compressframe_updatedata;
	fself->isvalid = _compressframe_isvalid;
#if 0
	if (NULL == parentfinalize) {
		parentfinalize = fself->baseclass._finalize;
	}
	fself->baseclass->_finalize = _compressframe_finalize;
#endif
	return self;
}
/// Return TRUE if this is a valid CompressFrame - either an object or on-the-wire version
FSTATIC gboolean
_compressframe_isvalid(const Frame *fself, gconstpointer tlvstart, gconstpointer pktend)
{
	const CompressFrame*	self = CASTTOCONSTCLASS(CompressFrame, fself);
	gconstpointer		origlen_p;
	guint8			compresstype;
	guint32			origlen;
	const guint8*		valptr;
	if (tlvstart == NULL) {
		return self->compression_index < DIMOF(allcompressions)
	&&	allcompressions[self->compression_index].compression_type == self->compression_method;
	}
	if (	((const guint8*)pktend-(const guint8*)tlvstart) < 12
	|| 	get_generic_tlv_len(tlvstart, pktend) <= 8) {
		return FALSE;
	}
	valptr = get_generic_tlv_value(tlvstart, pktend);
	compresstype = tlv_get_guint8(valptr, pktend);
	if (_compressframe_findmethod(compresstype) < 0) {
		return FALSE;
	}
	origlen = tlv_get_guint24(valptr+1, pktend);
	if (origlen > 1024*1024 || origlen < 32) { // 32 is a guess at min len
		return FALSE;
	}
	return TRUE;
}
FSTATIC gsize
_compressframe_dataspace(const Frame* f)
{
	return 4 + f->length;
}

FSTATIC void
_compressframe_setvalue(Frame *f, gpointer value, guint16 len, GDestroyNotify valnotify)
{
	g_warning("%s:%d: Not possible to set the value of a CompressFrame", __FUNCTION__, __LINE__);
}

#define COMPFRAMESIZE	4

///
/// We update the data in the packet from our CompressFrame object AND ALSO have the
/// side-effect of compressing all the frames already put into the packet.  Note that
/// this only works because we always construct the packet from the end back to the
/// beginning.
FSTATIC void
_compressframe_updatedata(Frame *f, gpointer tlvstart, gconstpointer pktend, FrameSet* fs)
{
	CompressFrame*	self		= CASTTOCLASS(CompressFrame, f);
	guint8*		pktstart	= fs->packet;
	guint8*		tlvstart8	= tlvstart;
	const guint8*	pktend8		= pktend;
	guint8*		valptr;
	guint32		offset;
	gpointer	newpacket;
	guint32		compressedsize;
	
	// Write our type and length into the packet
	set_generic_tlv_type(tlvstart, f->type, pktend);
	valptr = get_generic_tlv_nonconst_value(tlvstart, pktend);
	// Our value consists of the compression method followed by a 3 byte
	// packet length.  This restricts us to a 16M uncompressed original
	// packet.  That should be big enough for a while...
	// Of course, the fact that this has to compress down to a single UDP
	// packet makes this a very reasonable assumption...
	// In practice, our JSON seems to be limited to about 300K uncompressed.
	tlv_set_guint8(valptr, self->compression_method, pktend);
	self->uncompressed_size = pktend8 - pktstart;
	tlv_set_guint24(valptr+1, self->uncompressed_size, pktend);

	// Now on to our side effect - compressing the frames that follow us...
	offset = (tlvstart8+COMPFRAMESIZE)-pktstart;
	newpacket = allcompressions[self->compression_index].compress
		(pktstart, self->uncompressed_size, offset, MAXUDPSIZE, &compressedsize, 0);
	if (NULL == newpacket) {
		g_warning("%s:%d: Unable to compress %d byte packet to %d byte UDP packet"
		,	__FUNCTION__, __LINE__, self->uncompressed_size, MAXUDPSIZE);
	}
	set_generic_tlv_len(tlvstart, COMPFRAMESIZE+compressedsize, pktend);
	fs->packet = newpacket;
}

FSTATIC Frame*
compressframe_tlvconstructor(gconstpointer tlvstart, gconstpointer pktend)
{
}

#if HAVE_ZLIB_H
/// Single-packet compression using zlib (-lz).
/// Our goal here is to compress the data as cheaply as possible so that the <i>total</i> output size
/// is less than or equal to 'maxout' bytes.  Maxout is normally the maximum size of a UDP packet.
/// This is our definition of optimal compression - the cheapest that fits.
gpointer
z_compressbuf(gpointer inbuf	///<[in] Input buffer
,	int insize		///<[in] size of 'inbuf'
,	int offset		///<[in] Offset to beginning of data to be compressed
,	int maxout		///<[in] Maximum size of compressed output [UDP packet size]
,	int *actualsize		///<[out] Actual size of compressed output
,	int level) {		///<[in] Compression level: (normally zero)

	gpointer	outbuf;
	z_stream	stream;
	int		ret;
	int		space;
	double		ratio;

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
		fprintf(stderr, "OOPS, got a deflateInit return of %d", ret);
		return NULL;
	}
	outbuf = malloc(maxout);
	if (NULL == outbuf) {
		fprintf(stderr, "OOPS, out of space.");
		return NULL;
	}
	stream.avail_in = insize-offset;	stream.next_in = inbuf+offset;
	stream.avail_out = maxout;		stream.next_out = outbuf+offset;

	/* Compress it */
	ret = deflate(&stream, Z_FINISH);
	if (ret != Z_STREAM_END) {
		free(outbuf);
		if (level < 9) {
			return z_compressbuf(inbuf, insize, offset, maxout, actualsize, 9);
		}
		fprintf(stderr, "Got return code of %d from deflate (!= Z_STREAM_END)", ret);
		return NULL;
	}
	space = insize - stream.avail_out;
	(void)deflateEnd(&stream);
#if 0
	ratio = ((double)stream.total_in/((double)stream.total_out));
	//return 0;
	fprintf(stderr, "Compressing %ld bytes into %ld bytes with level %d ratio %.2f:1\n", stream.total_in
	, stream.total_out, level, ratio);
#endif
	outbuf = realloc(outbuf, stream.total_out);
	*actualsize = stream.total_out;
	return outbuf;
}

/// Single-packet decompression using zlib (-lz).
/// Return NULL on failure.
gpointer
z_decompressbuf(gpointer inbuf	///<[in] compressed input buffer
,	int insize		///<[in] size of compressed input buffer
,	int offset		///<[in] start of compressed data - the first "offset" bytes
				///< from inbuf are copied into output w/o uncompression
,	int maxout		///<[in] maximum size of uncompressed output.
				///< nice if it's uncompressed size if you know it.
,	int *uncompsize) {	///<[out] actual uncompressed size
	gpointer	outbuf;
	int		outsize;
	int		ret;
	z_stream	stream;
	/* Set up libz */
	stream.zalloc = Z_NULL;
	stream.zfree = Z_NULL;
	stream.opaque = Z_NULL;
	stream.avail_in = insize-offset;
	stream.next_in = ((unsigned char *)inbuf) + offset;
	if (Z_OK != inflateInit(&stream)) {
		return NULL;
	}
	outbuf = malloc(maxout);
	stream.avail_out = maxout;
	stream.next_out = ((unsigned char *)outbuf) + offset;
	// Decompress our input buffer.
	ret = inflate(&stream, Z_FINISH);
	if (ret != Z_STREAM_END) {
		fprintf(stderr, "GOT RETURN OF %d, size=%d totalsize=%ld: (Z_OK == %d, Z_STREAM_END=%d)\n", ret, outsize
		,	stream.total_out, Z_OK, Z_STREAM_END);
		free(outbuf);
		return NULL;
	}
	outsize = maxout - stream.avail_out;
	if (outsize > maxout) {
		outbuf = realloc(outbuf, outsize);
	}
	if (offset > 0) {
		memcpy(outbuf, inbuf, offset);
	}
	*uncompsize = outsize;
	return outbuf;
}
#endif /* HAVE_ZLIB_H */
