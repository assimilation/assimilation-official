/**
 * @file
 * @brief FrameSet queueing class
 * @details This includes code to implement FrameSet queueing for reliable communication
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2012 - Alan Robertson <alanr@unix.sh>
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
 *
 */
#include <string.h>
#include <projectcommon.h>
#include <fsprotocol.h>
#include <framesettypes.h>
#include <frametypes.h>
#include <seqnoframe.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

FSTATIC void		_fsprotocol_protoelem_destroy(gpointer fsprotoelemthing);
FSTATIC gboolean	_fsprotocol_protoelem_equal(gconstpointer lhs, gconstpointer rhs);
FSTATIC guint		_fsprotocol_protoelem_hash(gconstpointer fsprotoelemthing);
FSTATIC gboolean	_fsprotocol_timeoutfun(gpointer userdata);

FSTATIC void		_fsprotocol_finalize(AssimObj* aself);
FSTATIC FsProtoElem*	_fsprotocol_addconn(FsProtocol*self, guint16 qid, NetAddr* destaddr);
FSTATIC void		_fsprotocol_closeconn(FsProtocol*self, guint16 qid, const NetAddr* destaddr);
FSTATIC FsProtoState	_fsprotocol_connstate(FsProtocol*self, guint16 qid, const NetAddr* destaddr);
FSTATIC FsProtoElem*	_fsprotocol_find(FsProtocol* self, guint16 qid, const NetAddr* destaddr);
FSTATIC FsProtoElem*	_fsprotocol_findbypkt(FsProtocol* self, NetAddr*, FrameSet*);
FSTATIC gboolean	_fsprotocol_iready(FsProtocol*);
FSTATIC gboolean	_fsprotocol_outputpending(FsProtocol*);
FSTATIC FrameSet*	_fsprotocol_read(FsProtocol*, NetAddr**);
FSTATIC void		_fsprotocol_receive(FsProtocol*, NetAddr*, FrameSet*);
FSTATIC gboolean	_fsprotocol_send1(FsProtocol*, FrameSet*, guint16 qid, NetAddr*);
FSTATIC gboolean	_fsprotocol_send(FsProtocol*, GSList*, guint16 qid, NetAddr*);
FSTATIC void		_fsprotocol_ackmessage(FsProtocol* self, NetAddr* destaddr, FrameSet* fs);
FSTATIC void		_fsprotocol_ackseqno(FsProtocol* self, NetAddr* destaddr, SeqnoFrame* seq);
FSTATIC void		_fsprotocol_closeall(FsProtocol* self);
FSTATIC int		_fsprotocol_activeconncount(FsProtocol* self);
FSTATIC void		_fsprotocol_xmitifwecan(FsProtoElem*);
FSTATIC void		_fsproto_sendconnak(FsProtoElem* fspe, NetAddr* dest);
FSTATIC void		_fsprotocol_fspe_closeconn(FsProtoElem* self);
FSTATIC void		_fsprotocol_fspe_reinit(FsProtoElem* self);

FSTATIC void		_fsprotocol_auditfspe(const FsProtoElem*, const char * function, int lineno);
FSTATIC void		_fsprotocol_auditiready(const char * fun, unsigned lineno, const FsProtocol* self);

#define AUDITFSPE(fspe)	{ if (fspe) _fsprotocol_auditfspe(fspe, __FUNCTION__, __LINE__); }
#define AUDITIREADY(self) {_fsprotocol_auditiready(__FUNCTION__, __LINE__, self);}


DEBUGDECLARATIONS
/// @defgroup FsProtocol FsProtocol class
///@{
/// @ingroup C_Classes

typedef enum _FsProtoInput	FsProtoInput;
/**
 * Inputs are:
 *
 */
enum _FsProtoInput {
	FSPROTO_GOTSTART	= 0,	///< Received a packet with sequence number 1 and a valid (new) session id
	FSPROTO_REQSEND		= 1,	///< Got request to send a packet
	FSPROTO_GOTACK		= 2,	///< Received a legitimate ACK
	FSPROTO_GOTCONN_NAK	= 3,	///< Received a CONN_NAK packet
	FSPROTO_REQSHUTDOWN	= 4,	///< Got request to shut down
	FSPROTO_RCVSHUTDOWN	= 5,	///< Received a CONNSHUT packet
	FSPROTO_ACKTIMEOUT	= 6,	///< Timed out waiting for an ACK.
	FSPROTO_OUTALLDONE	= 7,	///< All output has been ACKed
	FSPROTO_INVAL,			///< End marker -- invalid input
};

static const FsProtoState nextstates[FSPR_INVALID][FSPROTO_INVAL] = {
//	    START     REQSEND	  GOTACK      GOTC_NAK    REQSHUTDOWN RCVSHUT,    ACKTIMEOUT OUTALLDONE
/*NONE*/ {FSPR_UP,    FSPR_INIT,  FSPR_NONE,  FSPR_NONE,  FSPR_NONE,  FSPR_NONE, FSPR_NONE, FSPR_NONE},
/*INIT*/ {FSPR_INIT,  FSPR_INIT,  FSPR_UP,    FSPR_INIT,  FSPR_INIT, FSPR_SHUT2, FSPR_NONE, FSPR_UP},
/*UP*/	 {FSPR_UP,    FSPR_UP,    FSPR_UP,    FSPR_NONE,  FSPR_SHUT1,FSPR_SHUT2,   FSPR_UP,   FSPR_UP},
// SHUT1: No ACK, no CONNSHUT
/*SHUT1*/{FSPR_SHUT1, FSPR_SHUT1, FSPR_SHUT1, FSPR_SHUT1, FSPR_NONE, FSPR_SHUT2, FSPR_NONE, FSPR_SHUT3},
// SHUT2: got CONNSHUT, Waiting for ACK
/*SHUT2*/{FSPR_UP,    FSPR_SHUT2, FSPR_SHUT2, FSPR_NONE,  FSPR_NONE, FSPR_SHUT2, FSPR_NONE, FSPR_NONE},
// SHUT3: got ACK, waiting for CONNSHUT
/*SHUT3*/{FSPR_SHUT3, FSPR_SHUT3, FSPR_SHUT3, FSPR_SHUT3, FSPR_NONE, FSPR_NONE,  FSPR_NONE, FSPR_SHUT3},
};
#define	A_CLOSE			(1<<0)
#define	A_OOPS			(1<<1)
#define	A_SNDNAK		(1<<2)
#define	A_SNDSHUT		(1<<3)
#define	A_ACKTO			(1<<4)
#define	A_ACKME			(1<<5)

#define NAKOOPS			(A_SNDNAK|A_OOPS)

static const unsigned actions[FSPR_INVALID][FSPROTO_INVAL] = {
//	  START	    REQSEND GOTACK  GOTCONN_NAK  REQSHUTDOWN          RCVSHUTDOWN       ACKTIMEOUT  OUTDONE
/*NONE*/ {0,	         0, A_OOPS,     A_CLOSE,          0,        A_ACKME|A_OOPS,  A_ACKTO|A_OOPS,   A_OOPS},
/*INIT*/ {0,	         0,	 0,     A_CLOSE,          0,     A_ACKME|A_SNDSHUT, A_ACKTO|A_CLOSE,       0},
/*UP*/   {0,	         0,	 0,     A_CLOSE,  A_SNDSHUT,     A_ACKME|A_SNDSHUT,         A_ACKTO,       0},
// SHUT1: no ACK, no CONNSHUT 
/*SHUT1*/{NAKOOPS,  A_OOPS,	 0,      A_OOPS,    A_CLOSE,     A_ACKME,           A_ACKTO|A_CLOSE,       0},
// SHUT2: got CONNSHUT, Waiting for ACK
/*SHUT2*/{NAKOOPS,  A_OOPS,	 0,           0,    A_CLOSE,     A_ACKME,           A_ACKTO|A_CLOSE, A_CLOSE},
// SHUT3: Got ACK, waiting for CONNSHUT
/*SHUT3*/{NAKOOPS,  A_OOPS, A_OOPS,      A_OOPS,    A_CLOSE,     A_ACKME|A_CLOSE,    A_ACKTO|A_OOPS,  A_OOPS},
};

FSTATIC void	_fsproto_fsa(FsProtoElem* fspe, FsProtoInput input, FrameSet* fs);

/// FsProtocol Finite state Automaton modelling connection establishment and shutdown.
FSTATIC void
_fsproto_fsa(FsProtoElem* fspe,	///< The FSPE we're processing
	     FsProtoInput input,///< The input for the FSA
	     FrameSet* fs)	///< The FrameSet we've been given (or NULL)
{
	FsProtocol*	parent		= fspe->parent;
	FsProtoState	curstate;
	FsProtoState	nextstate;
	unsigned	action;

	(void)parent;
	g_return_if_fail(fspe->state < FSPR_INVALID);
	g_return_if_fail(input < FSPROTO_INVAL);

	curstate = fspe->state;
	nextstate = nextstates[fspe->state][input];
	action = actions[fspe->state][input];



	DUMP2("_fsproto_fsa: endpoint ", &fspe->endpoint->baseclass, NULL);
	DEBUGMSG2("%s.%d: (state %d, input %d) => (state %d, actions 0x%x)", __FUNCTION__, __LINE__
	,	curstate, input, nextstate, action);

	// Complain about an ACK timeout
	if (action & A_ACKTO) {
		char *	deststr = fspe->endpoint->baseclass.toString(&fspe->endpoint->baseclass);
		g_warning("%s.%d: Timed out waiting for an ACK while communicating with %s/%d in state %d."
		,	__FUNCTION__, __LINE__, deststr, fspe->_qid, curstate);
		FREE(deststr); deststr = NULL;
		DUMP3("_fsproto_fsa: Output Queue", &fspe->outq->baseclass, NULL);
	}

	// Tell other endpoint we don't like their packet
	if (action & A_SNDNAK) {
		FrameSet*	fset = frameset_new(FRAMESETTYPE_CONNNAK);
		SeqnoFrame*	seq;
		if (fs && NULL != (seq = fs->getseqno(fs))) {
			frameset_append_frame(fset, &seq->baseclass);
		}else{
			g_critical("%s.%d: A_SNDNAK action either without valid FrameSet or valid seqno"
			" in state %d with input %d", __FUNCTION__, __LINE__, curstate, input);
			action |= A_OOPS;
		}
		parent->send1(parent, fset, fspe->_qid, fspe->endpoint);
		UNREF(fset);
	}
	if (action & A_ACKME) {
		SeqnoFrame*	seq;
		if (fs == NULL || NULL == (seq = fs->getseqno(fs))) {
			g_critical("%s.%d: A_ACKME action either without valid FrameSet or valid seqno"
			" in state %d with input %d", __FUNCTION__, __LINE__, curstate, input);
			action |= A_OOPS;
		}else{
			_fsprotocol_ackseqno(parent, fspe->endpoint, seq);
		}
	}

	// Notify other endpoint we're going away
	if (action & A_SNDSHUT) {
		FrameSet*	fset = frameset_new(FRAMESETTYPE_CONNSHUT);
		parent->send1(parent, fset, fspe->_qid, fspe->endpoint);
		UNREF(fset);
	}

	// Should remain the second-to-the-last action in the FSA function
	// This is because a previous action might want to OR in an A_OOPS into action
	// to trigger this action - if something is out of whack.
	if (action & A_OOPS) {
		char *	deststr = fspe->endpoint->baseclass.toString(&fspe->endpoint->baseclass);
		char *	fsstr = (fs ? fs->baseclass.toString(&fs->baseclass) : NULL);
		g_warning("%s.%d: Got a %d input for %s/%d while in state %d", __FUNCTION__, __LINE__
		,	(int)input, deststr, fspe->_qid, (int)nextstate);
		FREE(deststr); deststr = NULL;
		if (fsstr) {
			g_warning("%s.%d: Frameset given was: %s", __FUNCTION__, __LINE__, fsstr);
			FREE(fsstr);
			fsstr = NULL;
		}
	}


	if (action & A_CLOSE) {
		/// @todo Want to eventually clean these out, but can't do that right now
		_fsprotocol_fspe_reinit(fspe);
	}
	fspe->state = nextstate;
}

/** Try and transmit a packet after auditing the FSPE data structure */
#define		TRYXMIT(fspe)	{AUDITFSPE(fspe); _fsprotocol_xmitifwecan(fspe);}



/// Audit a FsProtoElem object for consistency */
FSTATIC void
_fsprotocol_auditfspe(const FsProtoElem* self, const char * function, int lineno)
{
	guint		outqlen = self->outq->_q->length;
	FsProtocol*	parent = self->parent;
	gboolean	in_unackedlist = (g_list_find(parent->unacked, self) != NULL);

	if (outqlen != 0 && !in_unackedlist) {
		g_warning("%s:%d: outqlen is %d but not in unacked list"
		,	function, lineno, outqlen);
		DUMP("WARN: previous unacked warning was for this address", &self->endpoint->baseclass, NULL);
	}
	if (outqlen == 0 && in_unackedlist) {
		g_warning("%s:%d: outqlen is zero but it IS in the unacked list"
		,	function, lineno);
		DUMP("WARN: previous unacked warning was for this address", &self->endpoint->baseclass, NULL);
	}
}
FSTATIC void
_fsprotocol_auditiready(const char * fun, unsigned lineno, const FsProtocol* self)
{
	GHashTableIter	iter;
	gpointer	key;
	gpointer	value;
	unsigned	hashcount = 0;

	g_hash_table_iter_init(&iter, self->endpoints);

	while(g_hash_table_iter_next(&iter, &key, &value)) {
		FsProtoElem*	fspe = (FsProtoElem*)key;
		FsQueue*	iq = fspe->inq;
		FrameSet*	fs = iq->qhead(iq);
		SeqnoFrame*	seq;
		// We can read the next packet IF:
		// it doesn't have a sequence number, OR it is the seqno we expect
		if (NULL == fs) {
			continue;
		}
		seq = fs->getseqno(fs);
		if (seq == NULL || seq->_reqid == iq->_nextseqno) {
			++hashcount;
		}
	}
	if (g_queue_get_length(self->ipend) != hashcount) {
		g_warning("%s.%d: ipend queue length is %d, but should be %d"
		,	fun, lineno, g_queue_get_length(self->ipend), hashcount);
	}
}

/// Locate the FsProtoElem structure that corresponds to this (destaddr, qid) pair
/// Convert everything to v6 addresses before lookup.
FSTATIC FsProtoElem*
_fsprotocol_find(FsProtocol*self		///< typical FsProtocol 'self' object
,		 guint16 qid			///< Queue id of far endpoint
,		 const NetAddr* destaddr)	///< destination address
{
	FsProtoElem*		retval = NULL;
	FsProtoElemSearchKey	elem;

	elem._qid	= qid;
	switch(destaddr->_addrtype) {

		case ADDR_FAMILY_IPV6:
			elem.endpoint	= destaddr;
			retval = (FsProtoElem*)g_hash_table_lookup(self->endpoints, &elem);
			break;

		case ADDR_FAMILY_IPV4: {
			NetAddr*	v6addr = destaddr->toIPv6(destaddr);

			elem.endpoint = v6addr;
			retval = (FsProtoElem*)g_hash_table_lookup(self->endpoints, &elem);
			UNREF(v6addr); elem.endpoint = NULL;
			break;
		}
	}
	return retval;
}

/// Find the FsProtoElem that corresponds to the given @ref FrameSet.
/// The FrameSet can have a sequence number - or not.
FSTATIC FsProtoElem*
_fsprotocol_findbypkt(FsProtocol* self		///< The FsProtocol object we're operating on
,		      NetAddr* addr		///< The Network address we're looking for
,		      FrameSet* fs)		///< The FrameSet whose queue id we'll use in looking for it
{
	SeqnoFrame*	seq = fs->getseqno(fs);
	guint16		qid = DEFAULT_FSP_QID;
	FsProtoElem*	ret;
	if (NULL != seq) {
		qid = seq->getqid(seq);
	}
	// Although we normally don't want to allow unsequenced packets to rest our port number,
	// the exception is a STARTUP packet.  They have to be unsequenced but are far more
	// important in terms of understanding the protocol than something like a heartbeat.
	//
	// This only comes up because we have this idea that we have two protocol endpoints
	// on the CMA - one for the CMA itself, and one for the nanoprobe which is running on it.
	//
	///@todo Should we <b>only</b> do this for the case where the frameset type is STARTUP?
	ret =  self->addconn(self, qid, addr);
	return ret;
}


/// Add and return a FsProtoElem connection to our collection of connections...
/// Note that if it's already there, the existing connection will be returned.
FSTATIC FsProtoElem*
_fsprotocol_addconn(FsProtocol*self	///< typical FsProtocol 'self' object
,		    guint16 qid		///< Queue id for the connection
,		    NetAddr* destaddr)	///< destination address
{
	FsProtoElem*	ret;


	if ((ret = self->find(self, qid, destaddr))) {
		return ret;
	}
	ret = MALLOCTYPE(FsProtoElem);
	if (ret) {
		ret->endpoint = destaddr->toIPv6(destaddr);	// No need to REF() again...
		ret->_qid = qid;
		ret->outq = fsqueue_new(0, ret->endpoint, qid);
		ret->inq  = fsqueue_new(0, ret->endpoint, qid);
		ret->lastacksent  = NULL;
		ret->lastseqsent  = NULL;
		ret->nextrexmit  = 0;
		ret->parent = self;
		g_warn_if_fail(NULL == g_hash_table_lookup(self->endpoints, ret));
		g_hash_table_insert(self->endpoints, ret, ret);
		DEBUGMSG3("%s: Creating new FSPE connection (%p) for qid = %d. Dest address follows."
		,	__FUNCTION__, ret, qid);
		DUMP3(__FUNCTION__, &ret->endpoint->baseclass, " is dest address for new FSPE");
	}
	return ret;
}

/// Close a specific connection - allowing it to be reopened by more communication -- effectively a reset
FSTATIC void
_fsprotocol_closeconn(FsProtocol*self		///< typical FsProtocol 'self' object
,		    guint16 qid			///< Queue id for the connection
,		    const NetAddr* destaddr)	///< destination address
{
	FsProtoElem*	fspe = _fsprotocol_find(self, qid, destaddr);
	DUMP3("_fsprotocol_closeconn() - closing connection to", &destaddr->baseclass, NULL);
	if (fspe) {
		DUMP3("_fsprotocol_closeconn: shutting down connection to", &destaddr->baseclass, NULL);
		_fsproto_fsa(fspe, FSPROTO_REQSHUTDOWN, NULL);
	}else if (DEBUG > 0) {
		char	suffix[16];
		snprintf(suffix, sizeof(suffix), "/%d", qid);
		DUMP("_fsprotocol_closeconn: Could not locate connection", &destaddr->baseclass, suffix);
	}
}
/// Start the process of shutting down all our connections
FSTATIC void
_fsprotocol_closeall(FsProtocol* self)
{
	GHashTableIter	iter;
	gpointer	key;
	gpointer	value;

	g_hash_table_iter_init(&iter, self->endpoints);

	while(g_hash_table_iter_next(&iter, &key, &value)) {
		FsProtoElem*	fspe = (FsProtoElem*)key;
		_fsprotocol_closeconn(self, fspe->_qid, fspe->endpoint);
	}
}
FSTATIC int
_fsprotocol_activeconncount(FsProtocol* self)
{
	GHashTableIter	iter;
	gpointer	key;
	gpointer	value;
	int		count = 0;

	g_hash_table_iter_init(&iter, self->endpoints);

	while(g_hash_table_iter_next(&iter, &key, &value)) {
		FsProtoElem*	fspe = (FsProtoElem*)key;
		FsProtoState	state = fspe->state;
		if (state != FSPR_NONE) {
			++count;
		}
	}
	return count;
}

FSTATIC FsProtoState
_fsprotocol_connstate(FsProtocol*self, guint16 qid, const NetAddr* destaddr)
{
	FsProtoElem*	fspe = _fsprotocol_find(self, qid, destaddr);
	if (fspe == NULL) {
		return FSPR_NONE;
	}
	return fspe->state;
}

// Reinitialize an FSPE into a no-connection state
FSTATIC void
_fsprotocol_fspe_reinit(FsProtoElem* self)
{

	if (!g_queue_is_empty(self->outq->_q)) {
		self->outq->flush(self->outq);
		self->parent->unacked = g_list_remove(self->parent->unacked, self);
		self->outq->isready = FALSE;
	}
	self->outq->_nextseqno = 1;
	self->outq->_sessionid = 0;

	if (!g_queue_is_empty(self->inq->_q)) {
		self->inq->flush(self->inq);
		g_queue_remove(self->parent->ipend, self);
		self->outq->isready = FALSE;
	}
	self->inq->_nextseqno = 1;
	self->inq->_sessionid = 0;

	if (self->lastacksent) {
		UNREF2(self->lastacksent);
	}
	if (self->lastseqsent) {
		UNREF2(self->lastseqsent);
	}
	self->nextrexmit = 0;
	self->acktimeout = 0;
	self->state = FSPR_NONE;
}

FSTATIC void
_fsprotocol_fspe_closeconn(FsProtoElem* self)
{
	DUMP3("_fsprotocol_fspe_closeconn: closing connection to", &self->endpoint->baseclass, NULL);
	g_hash_table_remove(self->parent->endpoints, self);
	self = NULL;
}



/// Construct an FsQueue object
WINEXPORT FsProtocol*
fsprotocol_new(guint objsize		///< Size of object to be constructed
,	      NetIO* io			///< Pointer to NetIO for us to reference
,	      guint rexmit_timer_uS)	///< Retransmit timer in microseconds
{
	FsProtocol*		self;
	BINDDEBUG(FsProtocol);
	if (objsize < sizeof(FsProtocol)) {
		objsize = sizeof(FsProtocol);
	}
	self = NEWSUBCLASS(FsProtocol, assimobj_new(objsize));
	if (!self) {
		return NULL;
	}
	// Initialize our (virtual) member functions
	self->baseclass._finalize = _fsprotocol_finalize;
	self->find =		_fsprotocol_find;
	self->findbypkt =	_fsprotocol_findbypkt;
	self->addconn =		_fsprotocol_addconn;
	self->iready =		_fsprotocol_iready;
	self->outputpending =	_fsprotocol_outputpending;
	self->read =		_fsprotocol_read;
	self->receive =		_fsprotocol_receive;
	self->send1 =		_fsprotocol_send1;
	self->send =		_fsprotocol_send;
	self->ackmessage =	_fsprotocol_ackmessage;
	self->closeconn =	_fsprotocol_closeconn;
	self->closeall =	_fsprotocol_closeall;
	self->activeconncount =	_fsprotocol_activeconncount;
	self->connstate =	_fsprotocol_connstate;

	// Initialize our data members
	self->io =		io; // REF(io);
	// NOTE that the REF has been commented out to prevent
	// a circular reference chain - screwing up freeing things...

	/// The key and the data are in fact the same object
	/// Don't want to free the object twice ;-) - hence the final NULL argument
	self->endpoints = g_hash_table_new_full(_fsprotocol_protoelem_hash,_fsprotocol_protoelem_equal
        ,		_fsprotocol_protoelem_destroy, NULL);
	self->unacked = NULL;
	self->ipend = g_queue_new();
	self->window_size = FSPROTO_WINDOWSIZE;
	self->rexmit_interval = FSPROTO_REXMITINTERVAL;
	self->acktimeout = FSPROTO_ACKTIMEOUTINT;

	if (rexmit_timer_uS == 0) {
		rexmit_timer_uS = self->rexmit_interval/2;
	}


	if ((rexmit_timer_uS % 1000000) == 0) {
		self->_timersrc = g_timeout_add_seconds(rexmit_timer_uS/1000000, _fsprotocol_timeoutfun, self);
	}else{
		self->_timersrc = g_timeout_add(rexmit_timer_uS/1000, _fsprotocol_timeoutfun, self);
	}
	DEBUGMSG3("%s: Constructed new FsProtocol object (%p)", __FUNCTION__, self);
	return self;
}

/// Finalize function for our @ref FsProtocol objects
FSTATIC void
_fsprotocol_finalize(AssimObj* aself)	///< FsProtocol object to finalize
{
	FsProtocol*	self = CASTTOCLASS(FsProtocol, aself);

	DUMP3("_fsprotocol_finalize - this object", aself, NULL);
	if (self->_timersrc) {
		g_source_remove(self->_timersrc);
		self->_timersrc = 0;
	}

	// Free up our hash table of endpoints
	if (self->endpoints) {
		g_hash_table_destroy(self->endpoints);	// It will free the FsProtoElems contained therein
		self->endpoints = NULL;
	}

	// Free up the unacked list
	g_list_free(self->unacked);		// No additional 'ref's were taken for this list
	self->unacked = NULL;

	// Free up the input pending list
	g_queue_free(self->ipend);		// No additional 'ref's were taken for this list either
	self->ipend = NULL;


	// Lastly free our base storage
	FREECLASSOBJ(self);
}

/// Finalize function suitable for GHashTables holding FsProtoElems as keys (and values)
FSTATIC void
_fsprotocol_protoelem_destroy(gpointer fsprotoelemthing)	///< FsProtoElem to destroy
{
	FsProtoElem *	self = (FsProtoElem*)fsprotoelemthing;
	DUMP3("Destroying FsProtoElem", &self->endpoint->baseclass, __FUNCTION__);
	self->parent->unacked	= g_list_remove(self->parent->unacked, self);
	g_queue_remove(self->parent->ipend, self);
	UNREF(self->endpoint);
	DEBUGMSG3("UNREFing INPUT QUEUE");
	UNREF(self->inq);
	DEBUGMSG3("UNREFing OUTPUT QUEUE");
	UNREF(self->outq);
	if (self->lastacksent) {
		UNREF2(self->lastacksent);
	}
	if (self->lastseqsent) {
		UNREF2(self->lastseqsent);
	}
	self->parent = NULL;
	memset(self, 0, sizeof(*self));
	FREE(self);
}

/// Equal-compare function for FsProtoElem structures suitable for GHashTables
FSTATIC gboolean
_fsprotocol_protoelem_equal(gconstpointer lhs	///< FsProtoElem left hand side to compare
,			    gconstpointer rhs)	///< FsProtoElem right hand side to compare
{
	const FsProtoElem *	lhselem = (const FsProtoElem*)lhs;
	const FsProtoElem *	rhselem = (const FsProtoElem*)rhs;

	return 	lhselem->_qid == rhselem->_qid
	&&	lhselem->endpoint->equal(lhselem->endpoint, rhselem->endpoint);


}

/// Hash function over FsProtoElem structures suitable for GHashTables
FSTATIC guint
_fsprotocol_protoelem_hash(gconstpointer fsprotoelemthing)	///< FsProtoElem to hash
{
	const FsProtoElem *	key = (const FsProtoElem*)fsprotoelemthing;
	// One could imagine doing a random circular rotate on the Queue Id before xoring it...
	// But this is probably good enough...
	return (key->endpoint->hash(key->endpoint) ^ key->_qid);
}

/// Return TRUE if there are any packets available to read
FSTATIC gboolean	
_fsprotocol_iready(FsProtocol* self)	///< Our object
{
	AUDITIREADY(self);
	return !g_queue_is_empty(self->ipend);
}

/// Return TRUE if there are any unACKed packets in any output queue
FSTATIC gboolean	
_fsprotocol_outputpending(FsProtocol* self)	///< Our object
{
	return self->unacked != NULL;
}

/// Read the next available packet from any of our sources
FSTATIC FrameSet*
_fsprotocol_read(FsProtocol* self	///< Our object - our very self!
,		 NetAddr** fromaddr)	///< The IP address our result came from
{
	GList*	list;	// List of all our FsQueues which have input

	AUDITIREADY(self);
	// Loop over all the FSqueues which we think are ready to read...
	for (list=self->ipend->head; list != NULL; list=list->next) {
		FrameSet*	fs;
		SeqnoFrame*	seq;
		FsProtoElem*	fspe = (FsProtoElem*)list->data;
		FsQueue*	iq;
		if (NULL == fspe || (NULL == (iq = fspe->inq)) || (NULL == (fs = iq->qhead(iq)))) {
			g_warn_if_reached();
			continue;
		}
		if (!fspe->inq->isready) {
			g_warn_if_reached();
			// But trudge on anyway...
		}
		seq = fs->getseqno(fs);
		// Look to see if there is something ready to be read on this queue
		// There should be something ready to be read!
		if (seq == NULL || seq->_reqid == iq->_nextseqno) {
			FrameSet*	ret;
			gboolean	del_link = FALSE;
			REF(iq->_destaddr);
			*fromaddr = iq->_destaddr;
			ret = iq->deq(iq);
			if (seq != NULL) {
				iq->_nextseqno += 1;
			}else{
				DUMP4("fsprotocol_read: returning unsequenced frame", &ret->baseclass, NULL);
			}
			// Now look and see if there will _still_ be something
			// ready to be read on this input queue.  If not, then
			// we should remove this FsProtoElem from the 'ipend' queue
			fs = iq->qhead(iq);
			if (fs == NULL) {
				// Our FsQueue is empty. Remove our FsProtoElem from the ipend queue
				del_link = TRUE;
			}else{
				// We can read the next packet IF:
				// it doesn't have a sequence number, OR it is the seqno we expect
				seq = fs->getseqno(fs);
				if (seq != NULL && seq->_reqid != iq->_nextseqno) {
					del_link = TRUE;
				}
			}
			g_queue_remove(self->ipend, fspe);
			if (del_link) {
				fspe->inq->isready = FALSE;
			}else{
				// Give someone else a chance to have their packets read
				g_queue_push_tail(self->ipend, fspe);
			}
			TRYXMIT(fspe);
			self->io->stats.reliablereads++;
			AUDITIREADY(self);
			return ret;
		}
		AUDITIREADY(self);
		g_warn_if_reached();
		TRYXMIT(fspe);
	}
	AUDITIREADY(self);
	return NULL;
}

/// Enqueue a received packet - handling ACKs when they show up
FSTATIC void
_fsprotocol_receive(FsProtocol* self			///< Self pointer
,				NetAddr* fromaddr	///< Address that this FrameSet comes from
,				FrameSet* fs)		///< Frameset that was received
{
	SeqnoFrame*	seq = fs->getseqno(fs);
	FsProtoElem*	fspe;

	fspe = self->findbypkt(self, fromaddr, fs);
	UNREF(fromaddr);
	g_return_if_fail(fspe != NULL);
	AUDITFSPE(fspe);
	
	DEBUGMSG3("%s.%d: Received type FrameSet fstype=%d", __FUNCTION__, __LINE__, fs->fstype);
	switch(fs->fstype) {
		case FRAMESETTYPE_ACK: {
			guint64 now = g_get_monotonic_time();
			int ackcount = 0;
			// Find the packet being ACKed, remove it from the output queue, and send
			// out the  next packet in that output queue...
			self->io->stats.acksrecvd++;
			g_return_if_fail(seq != NULL);
			ackcount = fspe->outq->ackthrough(fspe->outq, seq);
			if (ackcount < 0) {
				// This can happen when shutting down - if we've already shut down
				// and got a duplicate ACK
				DUMP3("Received bad ACK from", &fspe->endpoint->baseclass, NULL);
				DUMP3(__FUNCTION__, &fs->baseclass, " was ACK received.");
			}else if (fspe->outq->_q->length == 0) {
				fspe->parent->unacked = g_list_remove(fspe->parent->unacked, fspe);
				fspe->nextrexmit = 0;
				TRYXMIT(fspe);
				fspe->acktimeout = 0;
				_fsproto_fsa(fspe, FSPROTO_OUTALLDONE, fs);
			}else{
				fspe->nextrexmit = g_get_monotonic_time() + fspe->parent->rexmit_interval;
				fspe->acktimeout = now + self->acktimeout;
				TRYXMIT(fspe);
				_fsproto_fsa(fspe, FSPROTO_GOTACK, fs);
			}
			return;
		}
		case FRAMESETTYPE_CONNNAK: {
			_fsproto_fsa(fspe, FSPROTO_GOTCONN_NAK, fs);
			return;
		}
		case FRAMESETTYPE_CONNSHUT: {
			_fsproto_fsa(fspe, FSPROTO_RCVSHUTDOWN, fs);
			return;
		}
		default:
			/* Process below... */
			break;
	}
	AUDITFSPE(fspe);
	// Queue up the received frameset
	DUMP3(__FUNCTION__, &fs->baseclass, "given to inq->inqsorted");
	if (fspe->inq->inqsorted(fspe->inq, fs)) {
		if (seq && seq->_reqid == 1) {
			_fsproto_fsa(fspe, FSPROTO_GOTSTART, fs);
		}
	}else{
		DUMP3(__FUNCTION__, &fs->baseclass, " Frameset failed to go into queue :-(.");
		DEBUGMSG3("%s.%d: seq=%p lastacksent=%p", __FUNCTION__, __LINE__
		,	seq, fspe->lastacksent);
		// One reason for not queueing it is that we've already sent it
		// to our client. If they have already ACKed it, then we will ACK
		// it again automatically - because th application won't be shown
		// this packet again - so they can't ACK it and our ACK might have
		// gotten lost, so we need to send it again...
		// 
		// On the other hand, we cannot re-send an ACK that the application hasn't given us yet...
		// We could wind up here if the app is slow to ACK packets we gave it
		if (seq && fspe->lastacksent) {
			if (seq->_sessionid == fspe->lastacksent->_sessionid
			&&	seq->compare(seq, fspe->lastacksent) <= 0) {
				// We've already ACKed this packet - send our highest seq# ACK
				DEBUGMSG3("%s.%d: Resending ACK", __FUNCTION__, __LINE__);
				_fsprotocol_ackseqno(self, fspe->endpoint, fspe->lastacksent);
			}
		}
	}
	AUDITFSPE(fspe);

	DEBUGMSG3("%s: isready: %d seq->_reqid:%d , fspe->inq->_nextseqno: "FMT_64BIT"d"
	,	__FUNCTION__, fspe->inq->isready, (seq ? (gint)seq->_reqid : -1), fspe->inq->_nextseqno);
	// If this queue wasn't shown as ready before - see if it is ready for reading now...
	if (!fspe->inq->isready) {
		if (seq == NULL || seq->_reqid == fspe->inq->_nextseqno) {
			// Now ready to read - put our fspe on the list of fspes with input pending
			g_queue_push_head(self->ipend, fspe);
			fspe->inq->isready = TRUE;
		}
	}
	AUDITFSPE(fspe);
	TRYXMIT(fspe);
}

/// Enqueue and send a single reliable frameset
FSTATIC gboolean
_fsprotocol_send1(FsProtocol* self	///< Our object
,		  FrameSet* fs		///< Frameset to send
,		  guint16   qid		///< Far endpoint queue id
,		  NetAddr* toaddr)	///< Where to send it
{
	FsProtoElem*	fspe;
	gboolean	ret;

	fspe = self->addconn(self, qid, toaddr);
	g_return_val_if_fail(NULL != fspe, FALSE);	// Should not be possible...
	AUDITFSPE(fspe);

	if (FSPR_INSHUTDOWN(fspe->state)) {
		return FALSE;
	}
	_fsproto_fsa(fspe, FSPROTO_REQSEND, NULL);

	if (fspe->outq->_q->length == 0) {
		///@todo: This might be slow if we send a lot of packets to an endpoint
		/// before getting a response, but that's not very likely.
		fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
		fspe->nextrexmit = g_get_monotonic_time() + fspe->parent->rexmit_interval;
	}
	ret =  fspe->outq->enq(fspe->outq, fs);
	self->io->stats.reliablesends++;
	TRYXMIT(fspe);
	AUDITFSPE(fspe);
	return ret;
}
/// Enqueue and send a list of reliable FrameSets (send all or none)
FSTATIC gboolean
_fsprotocol_send(FsProtocol* self	///< Our object
,		 GSList* framesets	///< Framesets to be sent
,		 guint16   qid		///< Far endpoint queue id
,		 NetAddr* toaddr)	///< Where to send them
{
	FsProtoElem*	fspe = self->addconn(self, qid, toaddr);
	gboolean	ret = TRUE;
	int		emptyq = fspe->outq->_q->length == 0;
	AUDITFSPE(fspe);
	if (FSPR_INSHUTDOWN(fspe->state)) {
		return FALSE;
	}
	// Send them all -- or none of them...
	ret =  fspe->outq->hasqspace(fspe->outq, g_slist_length(framesets));
	
	if (ret) {
		GSList*	this;
		int	count = 0;
		_fsproto_fsa(fspe, FSPROTO_REQSEND, NULL);
		// Loop over our framesets and send them ouit...
		for (this=framesets; this; this=this->next) {
			FrameSet* fs = CASTTOCLASS(FrameSet, this->data);
			g_return_val_if_fail(fs != NULL, FALSE);
			DEBUGMSG3("%s: queueing up frameset %d of type %d"
			,	__FUNCTION__, count, fs->fstype);
			fspe->outq->enq(fspe->outq, fs);
			self->io->stats.reliablesends++;
			if (emptyq) {
				fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
				emptyq = FALSE;
			}
			AUDITFSPE(fspe);
			++count;
		}
	}
	AUDITFSPE(fspe);
	TRYXMIT(fspe);
	AUDITFSPE(fspe);
	return ret;
}

/// Send an ACK packet that corresponds to this FrameSet
FSTATIC void
_fsprotocol_ackmessage(FsProtocol* self, NetAddr* destaddr, FrameSet* fs)
{
	SeqnoFrame*	seq = fs->getseqno(fs);
	if (seq != 0) {
		_fsprotocol_ackseqno(self, destaddr, seq);
	}
}

/// Send an ACK packet that corresponds to this sequence number frame
FSTATIC void
_fsprotocol_ackseqno(FsProtocol* self, NetAddr* destaddr, SeqnoFrame* seq)
{
	FrameSet*	fs;
	FsProtoElem*	fspe;
	g_return_if_fail(seq != NULL);

	DUMP3(__FUNCTION__, &seq->baseclass.baseclass, " SENDING ACK.");
	fs = frameset_new(FRAMESETTYPE_ACK);

	frameset_append_frame(fs, &seq->baseclass);
	// Appending the seq frame will increment its reference count

	fspe = self->find(self, seq->_qid, destaddr);
	// sendaframeset will hang onto frameset and frames as long as it needs them
	AUDITFSPE(fspe);
	self->io->sendaframeset(self->io, destaddr, fs);
	self->io->stats.ackssent++;
	AUDITFSPE(fspe);
	UNREF(fs);

	if (NULL == fspe) {
		// We may have closed this connection
		DEBUGMSG3("Sending an ACK on a closed channel.");
		DUMP3(__FUNCTION__, &destaddr->baseclass, " is the destination for the ACK.");
		DUMP3(__FUNCTION__, &seq->baseclass.baseclass, " is the ACK sequence number.");
	}else if ((fspe->lastacksent == NULL || fspe->lastacksent->compare(fspe->lastacksent, seq) < 0)) {
		if (fspe->lastacksent) {
			UNREF2(fspe->lastacksent);
		}
		REF2(seq);
		fspe->lastacksent = seq;
	}
}

/// Our role in life is to send any packets that need sending.
///
///	Find every packet which is eligible to be sent and send it out
///
///	What makes a packet eligible to be sent?
///
///	It hasn't been sent yet and there are not too many ACKs outstanding on this fspe
///		Too many means: fspe->outstanding_acks >= parent->window_size.
///
///	OR it is time to retransmit.
///
///	When do we perform re-transmission of unACKed packets?
///		When it's been longer than parent->rexmit_period seconds
///			since the last re-transmission of this fspe
///
///	What do we do when it's time to perform a re-transmission?
///		We retransmit only the oldest FrameSet awaiting an ACK.
//
FSTATIC void
_fsprotocol_xmitifwecan(FsProtoElem* fspe)	///< The FrameSet protocol element to operate on
{
	FsQueue*	outq = fspe->outq;
	FsProtocol*	parent = fspe->parent;
	SeqnoFrame*	lastseq = fspe->lastseqsent;
	GList*		qelem;
	NetIO*		io = parent->io;
	guint		orig_outstanding = fspe->outq->_q->length;
	gint64		now;

	AUDITFSPE(fspe);
	// Look for any new packets that might have showed up to send
	// 	Check to see if we've exceeded our window size...
	if (fspe->outq->_q->length < parent->window_size) {
		// Nope.  Look for packets that we haven't yet sent.
		// This code is sub-optimal when congestion occurs and we have a larger
		// window size (i.e. when we have a number of un-ACKed packets)
		for (qelem=outq->_q->head; NULL != qelem; qelem=qelem->next) {
			FrameSet*	fs = CASTTOCLASS(FrameSet, qelem->data);
			SeqnoFrame*	seq = fs->getseqno(fs);
			if (NULL != lastseq && NULL != seq && seq->compare(seq, lastseq) <= 0) {
				// Not a new packet (we've sent it before)
				continue;
			}
			DUMP3(__FUNCTION__, &seq->baseclass.baseclass, " is frame being sent");
			io->sendaframeset(io, fspe->endpoint, fs);
			if (NULL == seq) {
				g_warn_if_reached();
				continue;
			}
			if (lastseq) {
				// lastseq is a copy of fspe->lastseqsent
				UNREF2(lastseq);
			}
			lastseq = fspe->lastseqsent = seq;
			REF2(lastseq);
			if (fspe->outq->_q->length >= parent->window_size) {
				break;
			}
		}
	}
	AUDITFSPE(fspe);
	now = g_get_monotonic_time();

	if (fspe->nextrexmit == 0 && fspe->outq->_q->length > 0) {
		// Next retransmission time not yet set...
		fspe->nextrexmit = now + parent->rexmit_interval;
		AUDITFSPE(fspe);
	} else if (fspe->nextrexmit != 0 && now > fspe->nextrexmit) {
		FrameSet*	fs = outq->qhead(outq);
		// It's time to retransmit something.  Hurray!
		if (NULL != fs) {
			// Update next retransmission time...
			fspe->nextrexmit = now + parent->rexmit_interval;
			DUMP3(__FUNCTION__, &fs->baseclass, " is frameset being REsent");
			io->sendaframeset(io, fspe->endpoint, fs);
			AUDITFSPE(fspe);

			if (now > fspe->acktimeout) {
				_fsproto_fsa(fspe, FSPROTO_ACKTIMEOUT, NULL);
				// No point in whining incessantly...
				fspe->acktimeout = now + parent->acktimeout;
			}
		}else{
			g_warn_if_reached();
			fspe->nextrexmit = 0;
		}
	}


	// Make sure we remember to check this periodicially for retransmits...
	if (orig_outstanding == 0 && fspe->outq->_q->length > 0) {
		// Put 'fspe' on the list of fspe's with unacked packets
		fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
		// See comment in the _send function regarding eventual efficiency concerns
	}
	AUDITFSPE(fspe);
}

/// Retransmit timer function...
FSTATIC gboolean
_fsprotocol_timeoutfun(gpointer userdata)
{
	FsProtocol*	self = CASTTOCLASS(FsProtocol, userdata);
	GList*		pending;
	GList*		next;

	g_return_val_if_fail(self != NULL, FALSE);

	DEBUGMSG4("%s: checking for timeouts: unacked = %p", __FUNCTION__, self->unacked);
	for (pending = self->unacked; NULL != pending; pending=next) {
		FsProtoElem*	fspe = (FsProtoElem*)pending->data;
		next = pending->next;
		AUDITFSPE(fspe);
		TRYXMIT(fspe);
		AUDITFSPE(fspe);
	}
	return TRUE;
}
///@}
