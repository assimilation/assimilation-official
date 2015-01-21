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
FSTATIC gboolean	_fsprotocol_shuttimeout(gpointer userdata);
FSTATIC gboolean	_fsprotocol_finalizetimer(gpointer userdata);

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
FSTATIC gboolean	_fsprotocol_canclose_immediately(gpointer unused_key, gpointer v_fspe, gpointer unused_user);
FSTATIC void		_fsprotocol_log_conn(FsProtocol* self, guint16 qid, NetAddr* destaddr);

typedef enum _FsProtoInput	FsProtoInput;

FSTATIC void		_fsprotocol_auditfspe(const FsProtoElem*, const char * function, int lineno);
FSTATIC void		_fsprotocol_auditiready(const char * fun, unsigned lineno, const FsProtocol* self);
FSTATIC void		_fsprotocol_fsa(FsProtoElem* fspe, FsProtoInput input, FrameSet* fs);
FSTATIC const char*	_fsprotocol_fsa_states(FsProtoState state);
FSTATIC const char*	_fsprotocol_fsa_inputs(FsProtoInput input);
FSTATIC const char*	_fsprotocol_fsa_actions(unsigned int actionbits);
FSTATIC void		_fsprotocol_flush_pending_connshut(FsProtoElem* fspe);

#define AUDITFSPE(fspe)	{ if (fspe) _fsprotocol_auditfspe(fspe, __FUNCTION__, __LINE__); }
#define AUDITIREADY(self) {_fsprotocol_auditiready(__FUNCTION__, __LINE__, self);}


DEBUGDECLARATIONS
/// @defgroup FsProtocol FsProtocol class
///@{
/// @ingroup C_Classes

/**
 * Inputs are:
 *
 */
enum _FsProtoInput {
	FSPROTO_GOTSTART	= 0,	///< Received a packet with sequence number 1
					///< and a valid (new) session id
	FSPROTO_REQSEND		= 1,	///< Got request to send a packet
	FSPROTO_GOTCONN_NAK	= 2,	///< Received a CONN_NAK packet
	FSPROTO_REQSHUTDOWN	= 3,	///< Got request to shut down
	FSPROTO_RCVSHUTDOWN	= 4,	///< Received a CONNSHUT packet
	FSPROTO_ACKTIMEOUT	= 5,	///< Timed out waiting for an ACK.
	FSPROTO_OUTALLDONE	= 6,	///< All output has been ACKed
	FSPROTO_SHUT_TO		= 7,	///< Got a timeout waiting for a SHUTDOWN
	FSPROTO_INVAL,			///< End marker -- invalid input
};

static const FsProtoState nextstates[FSPR_INVALID][FSPROTO_INVAL] = {
//	    START     REQSEND	  GOTC_NAK   REQSHUTDOWN RCVSHUT,    ACKTIMEOUT OUTALLDONE SHUT_TO
/*NONE*/ {FSPR_UP,    FSPR_INIT,  FSPR_NONE, FSPR_NONE,  FSPR_NONE,  FSPR_NONE, FSPR_NONE, FSPR_NONE},
/*INIT*/ {FSPR_INIT,  FSPR_INIT,  FSPR_INIT, FSPR_SHUT1, FSPR_SHUT2, FSPR_NONE, FSPR_UP,   FSPR_INIT},
/*UP*/	 {FSPR_UP,    FSPR_UP,    FSPR_NONE, FSPR_SHUT1, FSPR_SHUT2, FSPR_UP,   FSPR_UP,   FSPR_UP},
// SHUT1: No OUTDONE, no CONNSHUT
/*SHUT1*/{FSPR_SHUT1, FSPR_SHUT1, FSPR_NONE, FSPR_SHUT1, FSPR_SHUT2, FSPR_NONE, FSPR_SHUT3,FSPR_NONE},
// SHUT2: got CONNSHUT, Waiting for OUTDONE
/*SHUT2*/{FSPR_SHUT2, FSPR_SHUT2, FSPR_NONE, FSPR_SHUT2, FSPR_SHUT2, FSPR_NONE, FSPR_NONE, FSPR_NONE},
// SHUT3: got OUTDONE, waiting for CONNSHUT
/*SHUT3*/{FSPR_SHUT3, FSPR_SHUT3, FSPR_NONE, FSPR_SHUT3, FSPR_NONE,  FSPR_NONE, FSPR_SHUT3,FSPR_NONE},
};
#define	A_CLOSE			(1<<0)	///< 0x01 - set cleanup timer
#define	A_OOPS			(1<<1)	///< 0x02 - this should not happen - complain about it
#define	A_DEBUG			(1<<2)	///< 0x04 - print state info, etc
#define	A_SNDNAK		(1<<3)	///< 0x08 Don't appear to be using this action...
#define	A_SNDSHUT		(1<<4)	///< 0x10 Send CONNSHUT packet
#define	A_ACKTO			(1<<5)	///< 0x20 - Announce an ACK timeout	- 0x20
#define	A_ACKME			(1<<6)	///< 0x40 - Ack this packet
#define	A_TIMER			(1<<7)	///< 0x80 Start the FSPROTO_SHUT_TO timer - calls _fsprotocol_shuttimeout -
					///< which will eventually call the FSA with FSPROTO_SHUT_TO
#define	A_NOTIME		(1<<8)	///< 0x100 Cancel the FSPROTO_SHUT_TO timer
#define	A_NOSHUT		(1<<9)	///< 0x200 Flush out any pending CONNSHUT packets

#define SHUTnTIMER		(A_SNDSHUT|A_TIMER)
#define	ACKnSHUT		(A_ACKME|SHUTnTIMER)
#define	ACKnCLOSE		(A_ACKME|A_CLOSE)
#define	CLOSEnNOTIME		(A_CLOSE|A_NOTIME)

static const unsigned actions[FSPR_INVALID][FSPROTO_INVAL] = {
//	 START REQSEND GOTCONN_NAK REQSHUTDOWN   RCVSHUTDOWN  ACKTIMEOUT      OUTDONE       SHUT_TO
/*NONE*/ {0,    0,      A_CLOSE,   A_CLOSE,       ACKnSHUT,  A_ACKTO|A_OOPS,   A_OOPS,      A_OOPS},
/*INIT*/ {0,    0, 	A_CLOSE,   SHUTnTIMER,    ACKnSHUT,  A_CLOSE,            0,         A_OOPS},
/*UP*/   {0,    0, 	A_CLOSE,   SHUTnTIMER,    ACKnSHUT,  A_ACKTO,            0,         A_OOPS},
//SHUT1: no OUTDONE, no CONNSHUT - only got REQSHUTDOWN
/*SHUT1*/{0,   A_DEBUG, A_OOPS,    0,             A_ACKME,  A_CLOSE|A_NOTIME,    0,         A_CLOSE},
//SHUT2: got CONNSHUT, Waiting for OUTDONE
/*SHUT2*/{0,   A_DEBUG, 0,         0,             A_ACKME,  A_CLOSE|A_NOTIME, CLOSEnNOTIME, A_CLOSE},
//SHUT3: Got OUTDONE, waiting for CONNSHUT
/*SHUT3*/{0,   A_DEBUG, A_OOPS,    0,      ACKnCLOSE|A_NOTIME, A_CLOSE|A_NOTIME,  0,        A_CLOSE},
};

/// Returns the state name (string) for state - returns static data
FSTATIC const char*
_fsprotocol_fsa_states(FsProtoState state)
{
	static char	unknown[32];
	switch (state) {
		case	FSPR_NONE:	return "NONE";
		case	FSPR_INIT:	return "INIT";
		case	FSPR_UP:	return "UP";
		case	FSPR_SHUT1:	return "SHUT1";
		case	FSPR_SHUT2:	return "SHUT2";
		case	FSPR_SHUT3:	return "SHUT2";
		case	FSPR_INVALID:	return "INVALID";
	}
	g_snprintf(unknown, sizeof(unknown), "UNKNOWN%d", (int)state);
	return unknown;
}

/// Returns the input name (string) for an input - returns static array
FSTATIC const char*
_fsprotocol_fsa_inputs(FsProtoInput input)
{
	static char	unknown[32];
	switch (input) {
		case FSPROTO_GOTSTART:		return "GOTSTART";
		case FSPROTO_REQSEND:		return "REQSEND";
		case FSPROTO_GOTCONN_NAK:	return "GOTCONN_NAK";
		case FSPROTO_REQSHUTDOWN:	return "GOTREQSHUTDOWN";
		case FSPROTO_RCVSHUTDOWN:	return "RCVSHUTDOWN";
		case FSPROTO_ACKTIMEOUT:	return "ACKTIMEOUT";
		case FSPROTO_OUTALLDONE:	return "OUTALLDONE";
		case FSPROTO_SHUT_TO:		return "SHUT_TO";
		case FSPROTO_INVAL:		return "INVAL";
	}
	g_snprintf(unknown, sizeof(unknown), "UNKNOWN%d", (int)input);
	return unknown;
}

/// Returns a string representing a set of actions - static array returned
FSTATIC const char*
_fsprotocol_fsa_actions(unsigned actionmask)
{
	static char	result[512];
	char		leftovers[32];
	unsigned	actidx;
	struct {
		unsigned	bit;
		const char *	bitname;
	}map[] = {
		{A_CLOSE,	"CLOSE"},
		{A_OOPS,	"OOPS"},
		{A_DEBUG,	"DEBUG"},
		{A_SNDNAK,	"SNDNAK"},
		{A_SNDSHUT,	"SNDSHUT"},
		{A_ACKTO,	"ACKTO"},
		{A_ACKME,	"ACKME"},
		{A_TIMER,	"TIMER"},
		{A_NOTIME,	"NOTIME"},
		{A_NOSHUT,	"NOSHUT"},
	};
	if (actionmask == 0) {
		return "None";
	}
	result[0] = '\0';
	for (actidx=0; actidx < DIMOF(map); ++actidx) {
		if (actionmask & (map[actidx].bit)) {
			if (result[0] != '\0') {
				g_strlcat(result, "+", sizeof(result));
			}
			g_strlcat(result, map[actidx].bitname, sizeof(result));
			actionmask &= ~(map[actidx].bit);
		}
	}
	if (actionmask != 0) {
		g_snprintf(leftovers, sizeof(leftovers), "+0x%x", actionmask);
		g_strlcat(result, leftovers, sizeof(result));
	}
	return result;
}



/// FsProtocol Finite state Automaton modelling connection establishment and shutdown.
FSTATIC void
_fsprotocol_fsa(FsProtoElem* fspe,	///< The FSPE we're processing
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
	// DEBUG = 3;

#if 0
	if ((action & (A_CLOSE|A_SNDSHUT|A_NOSHUT))
	||	curstate >= FSPR_SHUT1		|| nextstate >= FSPR_SHUT1
	||	FSPROTO_RCVSHUTDOWN == input	|| FSPROTO_REQSHUTDOWN == input) {
		action |= A_DEBUG;
	}
#endif

	DUMP2("_fsprotocol_fsa() {: endpoint ", &fspe->endpoint->baseclass, NULL);
	if (DEBUG >= 2 || (action & A_DEBUG)) {
		DEBUGMSG("%s.%d: (state %s, input %s) => (state %s, actions %s)"
		,	__FUNCTION__, __LINE__
		,	_fsprotocol_fsa_states(curstate), _fsprotocol_fsa_inputs(input)
		,	_fsprotocol_fsa_states(nextstate), _fsprotocol_fsa_actions(action));
	}

	// Complain about an ACK timeout
	if (action & A_ACKTO) {
		char *	deststr = fspe->endpoint->baseclass.toString(&fspe->endpoint->baseclass);
		g_warning("%s.%d: Timed out waiting for an ACK while communicating with %s/%d in state %s."
		,	__FUNCTION__, __LINE__, deststr, fspe->_qid, _fsprotocol_fsa_states(curstate));
		FREE(deststr); deststr = NULL;
		DUMP3("_fsprotocol_fsa: Output Queue", &fspe->outq->baseclass, NULL);
		if (DEBUG < 2) {
			DEBUG = 2;
			//@FIXME: need to remove this when the protocol gets better...
			g_warning("%s.%d: RAISING DEBUG LEVEL TO 2", __FUNCTION__, __LINE__);
		}
	}

	// Tell other endpoint we don't like their packet (not currently used?)
	if (action & A_SNDNAK) {
		FrameSet*	fset = frameset_new(FRAMESETTYPE_CONNNAK);
		SeqnoFrame*	seq;
		if (fs && NULL != (seq = fs->getseqno(fs))) {
			frameset_append_frame(fset, &seq->baseclass);
		}else{
			g_critical("%s.%d: A_SNDNAK action either without valid FrameSet or valid seqno"
			" in state %s with input %s", __FUNCTION__, __LINE__
			,	_fsprotocol_fsa_states(curstate)
			,	_fsprotocol_fsa_inputs(input));
			action |= A_OOPS;
		}
		// Should this be being sent reliably?  Or w/o protocol?
		parent->send1(parent, fset, fspe->_qid, fspe->endpoint);
		UNREF(fset);
	}
	if (action & A_ACKME) {
		SeqnoFrame*	seq;
		if (fs == NULL || NULL == (seq = fs->getseqno(fs))) {
			g_critical("%s.%d: A_ACKME action either without valid FrameSet or valid seqno"
			" in state %s with input %s", __FUNCTION__, __LINE__
			,	_fsprotocol_fsa_states(curstate)
			,	_fsprotocol_fsa_inputs(input));
			action |= A_OOPS;
		}else{
			_fsprotocol_ackseqno(parent, fspe->endpoint, seq);
		}
	}

	// Notify other endpoint we're going away
	if (action & A_SNDSHUT) {
		FrameSet*	fset = frameset_new(FRAMESETTYPE_CONNSHUT);
		// Note that this will generate a recursive call to the FSA...
		parent->send1(parent, fset, fspe->_qid, fspe->endpoint);
		if (action & A_DEBUG) {
			DUMP("HERE IS THE CONNSHUT packet ", &fset->baseclass, "");
		}
		UNREF(fset);
	}

	// Flush any pending CONNSHUT packets 
	if (action & A_NOSHUT) {
		// This comes about if an ACK to our CONNSHUT gets lost, then the
		// CONNSHUT hangs around and causes us heartburn when the far end restarts
		// and we resend it.  Bad idea... https://trello.com/c/mLIA2fXJ
		_fsprotocol_flush_pending_connshut(fspe);
	}

	if (action & A_TIMER) {		// Start the FSPROTO_SHUT_TO timer
		if (fspe->shuttimer > 0) {
			g_warning("%s.%d: Adding SHUTDOWN timer when one is already running."
			,	__FUNCTION__, __LINE__);
			action |= A_DEBUG;
		}else{
			fspe->shuttimer = g_timeout_add_seconds(parent->acktimeout/1000000, _fsprotocol_shuttimeout, fspe);
		}
	}
	if (action & A_NOTIME) {	// Cancel the FSPROTO_SHUT_TO timer
		if (fspe->shuttimer > 0) {
			g_source_remove(fspe->shuttimer);
			fspe->shuttimer = 0;
		}
	}
	if (action & A_DEBUG) {
		char *	deststr = fspe->endpoint->baseclass.toString(&fspe->endpoint->baseclass);
		DEBUGMSG("%s.%d: Got a %s input for %s/%d while in state %s", __FUNCTION__, __LINE__
		,	_fsprotocol_fsa_inputs(input), deststr, fspe->_qid
		,	_fsprotocol_fsa_states(curstate));
		FREE(deststr); deststr = NULL;
	}


	// Should remain the second-to-the-last action in the FSA function
	// This is because a previous action might want to OR in an A_OOPS into action
	// to trigger this action - if something is out of whack.
	if (action & A_OOPS) {
		char *	deststr = fspe->endpoint->baseclass.toString(&fspe->endpoint->baseclass);
		char *	fsstr = (fs ? fs->baseclass.toString(&fs->baseclass) : NULL);
			
		g_warning("%s.%d: Got a %s input for %s/%d while in state %s", __FUNCTION__, __LINE__
		,	_fsprotocol_fsa_inputs(input), deststr, fspe->_qid
		,	_fsprotocol_fsa_states(curstate));
		FREE(deststr); deststr = NULL;
		if (fsstr) {
			g_warning("%s.%d: Frameset given was: %s", __FUNCTION__, __LINE__, fsstr);
			FREE(fsstr);
			fsstr = NULL;
		}
	}

	if (action & A_CLOSE) {
		DUMP3("CLOSING CONNECTION (A_CLOSE)", &fspe->endpoint->baseclass, "");
		_fsprotocol_fspe_reinit(fspe);
		fspe->shutdown_complete = TRUE;
		// Clean this up after a while
		// The time was chosen to occur after the other end will have given up on us and shut down anyway...
		/// Probably shouldn't clean this up, or we'll lose session id info
		fspe->finalizetimer = g_timeout_add_seconds(1+parent->acktimeout/1000000, _fsprotocol_finalizetimer, fspe);
	}
	fspe->state = nextstate;
	DEBUGMSG2("} /* %s:%d */", __FUNCTION__, __LINE__);
}

/// Flush the leading CONNSHUT packet in the queue -- if any
FSTATIC void
_fsprotocol_flush_pending_connshut(FsProtoElem* fspe)
{
	FrameSet*	fs;
	g_return_if_fail(fspe != NULL);
	fs = fspe->outq->qhead(fspe->outq);
	if (NULL == fs) {
		return;
	}
	if (FRAMESETTYPE_CONNSHUT == fs->fstype) {
		DUMP3("_fsprotocol_flush_pending_connshut: FLUSHing this CONNSHUT packet: "
		,	&fs->baseclass, "");
		fspe->outq->flush1(fspe->outq);
	}else{
		DUMP3("_fsprotocol_flush_pending_connshut: NOT FLUSHing this packet: "
		,	&fs->baseclass, "");
	}
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
		g_critical("%s:%d: outqlen is %d but not in unacked list"
		,	function, lineno, outqlen);
		DUMP("WARN: previous unacked warning was for this address", &self->endpoint->baseclass, NULL);
	}
	if (outqlen == 0 && in_unackedlist) {
		g_critical("%s:%d: outqlen is zero but it IS in the unacked list"
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
		FsProtoElem*	fspe = CASTTOCLASS(FsProtoElem, key);
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
			if (!fspe->inq->isready) {
				g_critical("%s.%d: Queue is ready but not marked 'isready'"
				,	fun, lineno);
				DUMP("Queue with problems", &fspe->inq->baseclass, NULL);
			}
		}else if (fspe->inq->isready) {
			g_critical("%s.%d: Queue is NOT ready but IS marked 'isready'"
			,	fun, lineno);
			DUMP("Problematic Queue", &fspe->inq->baseclass, NULL);
		}
	}
	if (g_queue_get_length(self->ipend) != hashcount) {
		g_critical("%s.%d: ipend queue length is %d, but should be %d"
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
			retval = CASTTOCLASS(FsProtoElem, g_hash_table_lookup(self->endpoints, &elem));
			break;

		case ADDR_FAMILY_IPV4: {
			NetAddr*	v6addr = destaddr->toIPv6(destaddr);

			elem.endpoint = v6addr;
			retval = CASTTOCLASS(FsProtoElem, g_hash_table_lookup(self->endpoints, &elem));
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
	ret = MALLOCCLASS(FsProtoElem, sizeof(FsProtoElem));
	if (ret) {
		ret->endpoint = destaddr->toIPv6(destaddr);	// No need to REF() again...
		ret->_qid = qid;
		ret->outq = fsqueue_new(0, ret->endpoint, qid);
		ret->inq  = fsqueue_new(0, ret->endpoint, qid);
		ret->lastacksent  = NULL;
		ret->lastseqsent  = NULL;
		ret->parent = self;
		ret->nextrexmit  = 0;
		ret->acktimeout = 0;
		ret->state = FSPR_NONE;
		ret->shuttimer = 0;
		ret->finalizetimer = 0;
		ret->shutdown_complete = FALSE;
		ret->is_encrypted = FALSE;
		ret->peer_identity = NULL;
		// This lookup assumes FsProtoElemSearchKey looks like the start of FsProtoElem
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
		_fsprotocol_fsa(fspe, FSPROTO_REQSHUTDOWN, NULL);

	}else if (DEBUG > 0) {
		char	suffix[16];
		g_snprintf(suffix, sizeof(suffix), "/%d", qid);
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

	DEBUGMSG("In %s.%d", __FUNCTION__, __LINE__);
	// Can't modify the table during an iteration...
	g_hash_table_foreach_remove(self->endpoints, _fsprotocol_canclose_immediately, NULL);
	g_hash_table_iter_init(&iter, self->endpoints);

	while(g_hash_table_iter_next(&iter, &key, &value)) {
		FsProtoElem*	fspe = CASTTOCLASS(FsProtoElem, key);
		_fsprotocol_closeconn(self, fspe->_qid, fspe->endpoint);
	}
}

/// Returns TRUE if the given FSPE can be closed immediately
FSTATIC gboolean
_fsprotocol_canclose_immediately(gpointer v_fspe, gpointer unused, gpointer unused_user)
{
	FsProtoElem*	fspe = CASTTOCLASS(FsProtoElem, v_fspe);
	gboolean		ret;
	(void)unused;
	(void)unused_user;
	ret =  (fspe->outq->_nextseqno <= 1 && fspe->inq->_nextseqno <= 1);
	if (ret) {
		DUMP3("IMMEDIATE REMOVE OF", CASTTOCLASS(AssimObj, &fspe->endpoint->baseclass), "");
	}
	return ret;
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
		FsProtoElem*	fspe = CASTTOCLASS(FsProtoElem, key);
		FsProtoState	state = fspe->state;
		if (state != FSPR_NONE
		&&	(fspe->inq->_nextseqno > 1 || fspe->outq->_nextseqno > 1)
		&&	!fspe->shutdown_complete) {
			DUMP5("THIS CONNECTION IS ACTIVE", CASTTOCLASS(AssimObj,&fspe->endpoint->baseclass), "");
			++count;
		}
	}
	if (count == 0) {
		g_hash_table_iter_init(&iter, self->endpoints);
		while(g_hash_table_iter_next(&iter, &key, &value)) {
			FsProtoElem*	fspe = CASTTOCLASS(FsProtoElem, key);
			fspe->shutdown_complete = FALSE;
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
		DUMP3("REINIT OF OUTQ", &self->outq->baseclass, __FUNCTION__);
		self->outq->flush(self->outq);
		self->parent->unacked = g_list_remove(self->parent->unacked, self);
		self->outq->isready = FALSE;
	}
	// See the code in _fsqueue_enq and also in seqnoframe_new_init for how all these pieces
	// fit together...
	self->outq->_nextseqno = 1;
	if (self->outq->_sessionid != 0) {
		self->outq->_sessionid += 1;
	}
	if (!g_queue_is_empty(self->inq->_q)) {
		self->inq->flush(self->inq);
		g_queue_remove(self->parent->ipend, self);
		self->inq->isready = FALSE;
	}
	self->inq->_nextseqno = 1;
	self->inq->_sessionid = 0;

	if (self->lastacksent) {
		UNREF2(self->lastacksent);
	}
	if (self->lastseqsent) {
		UNREF2(self->lastseqsent);
	}
	if (self->shuttimer > 0) {
		g_source_remove(self->shuttimer);
		self->shuttimer = 0;
	}
	if (self->finalizetimer > 0) {
		g_source_remove(self->finalizetimer);
		self->finalizetimer = 0;
	}
	self->nextrexmit = 0;
	self->acktimeout = 0;
	self->state = FSPR_NONE;
	self->shutdown_complete = FALSE;
	AUDITIREADY(self->parent);
}

/// Close down (destroy) an FSPE-level connection
/// Note that this depends on FsProtoElemSearchKey being the same as start of FsProtoElem
FSTATIC void
_fsprotocol_fspe_closeconn(FsProtoElem* self)
{
	DUMP5("_fsprotocol_fspe_closeconn: removing connection to", &self->endpoint->baseclass, NULL);
	g_hash_table_remove(self->parent->endpoints, self);
	self = NULL;
}



/// Construct an FsProtocol object
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
	self->log_conn	=	_fsprotocol_log_conn;

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
	FsProtoElem *	self = CASTTOCLASS(FsProtoElem, fsprotoelemthing);
	DUMP5("Destroying FsProtoElem", &self->endpoint->baseclass, __FUNCTION__);

	DUMP3("Destroying FsProtoElem", &self->endpoint->baseclass, __FUNCTION__);
	// This does a lot of our cleanup - but doesn't destroy anything important...
	_fsprotocol_fspe_reinit(self);

	// So let's get on with the destruction ;-)
	DUMP3("UNREFING FSPE: endpoint", &self->endpoint->baseclass, __FUNCTION__);
	UNREF(self->endpoint);
	DUMP3("UNREFING FSPE: INQ", &self->inq->baseclass, __FUNCTION__);
	UNREF(self->inq);
	DUMP3("UNREFING FSPE: OUTQ", &self->outq->baseclass, __FUNCTION__);
	UNREF(self->outq);
	self->parent = NULL;
	if (self->peer_identity) {
		FREE(self->peer_identity); self->peer_identity = NULL;
	}
	memset(self, 0, sizeof(*self));
	FREECLASSOBJ(self);
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

/// Read the next available FrameSet from any of our sources
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
		FsProtoElem*	fspe = CASTTOCLASS(FsProtoElem, list->data);
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
			DEBUGMSG3("%s.%d: Reading Frameset of type %d:"
			,	__FUNCTION__, __LINE__, fs->fstype);
			DUMP3("_fsprotocol_read: Dequeuing FrameSet from: ", &(*fromaddr)->baseclass, "");
			DUMP3("_fsprotocol_read: Dequeuing FrameSet: ", &ret->baseclass, "");
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
				// Give someone else a chance to get their packets read
				// Otherwise we get stuck reading the same endpoint(s) over and over
				// at least while reading initial discovery data.
				fspe->inq->isready = TRUE;
				g_queue_push_tail(self->ipend, fspe);
			}
			if (ret && FRAMESETTYPE_CONNSHUT == ret->fstype) {
				_fsprotocol_fsa(fspe, FSPROTO_RCVSHUTDOWN, ret);
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
	const char *	keyid = NULL;
	gpointer	maybecrypt;
	const char*	sender_id = NULL;

	fspe = self->findbypkt(self, fromaddr, fs);
	if (fspe == NULL) {
		goto badret;
	}
	AUDITIREADY(self);
	AUDITFSPE(fspe);
	
	DEBUGMSG3("%s.%d: Received type FrameSet fstype=%d", __FUNCTION__, __LINE__, fs->fstype);
	// Once we start talking encrypted on a channel, we make sure
	// that all future packets are encrypted.
	// If we know the identity of the far end, we make sure future packets
	// come from that identity.
	maybecrypt = g_slist_nth_data(fs->framelist, 1);
	if (maybecrypt && OBJ_IS_A(maybecrypt, "CryptFrame")) {
		 keyid = CASTTOCLASS(CryptFrame, maybecrypt)->sender_key_id;
	}
	if (keyid) {
		sender_id = cryptframe_whois_key_id(keyid);
		fspe->is_encrypted = TRUE;
		if (sender_id && !fspe->peer_identity) {
			fspe->peer_identity = g_strdup(sender_id);
		}
	}
	if (fs->fstype >= MIN_SEQFRAMESET) {
		// In this case, we enforce encryption and identity...
		if (fspe->peer_identity) {
			if (!sender_id || strcmp(sender_id, fspe->peer_identity) != 0) {
				char *	srcstr = fromaddr->baseclass.toString(&fromaddr->baseclass);
				g_warning("%s.%d: Discarded FrameSet %d from %s with wrong identity"
				": %s instead of %s [key id %s]"
				,	__FUNCTION__, __LINE__, fs->fstype, srcstr, sender_id
				,	fspe->peer_identity, keyid);
				g_free(srcstr); srcstr = NULL;
				DUMP("_fsprotocol_receive: FrameSet w/wrong identity: ", &fs->baseclass, "")
				// If any are bad - throw out the whole packet
				goto badret;
			}
		}else if (fspe->is_encrypted && !keyid) {
			char *	srcstr = fromaddr->baseclass.toString(&fromaddr->baseclass);
			g_warning("%s.%d: Discarded unencrypted FrameSet %d"
			" on encrypted channel from address %s."
			,	__FUNCTION__, __LINE__, fs->fstype, srcstr);
			g_free(srcstr); srcstr = NULL;
			DUMP("_fsprotocol_receive: unencrypted FrameSet is: ", &fs->baseclass, "")
			goto badret;
		}
	}
	UNREF(fromaddr);
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
				_fsprotocol_fsa(fspe, FSPROTO_OUTALLDONE, fs);
			}else{
				fspe->nextrexmit = now + self->rexmit_interval;
				fspe->acktimeout = now + self->acktimeout;
				TRYXMIT(fspe);
			}
			AUDITIREADY(self);
			return;
		}
		case FRAMESETTYPE_CONNNAK: {
			_fsprotocol_fsa(fspe, FSPROTO_GOTCONN_NAK, fs);
			AUDITIREADY(self);
			return;
		}
#if 0
		// We now process this when the client reads the packet (i.e., in order)
		case FRAMESETTYPE_CONNSHUT: {
			_fsprotocol_fsa(fspe, FSPROTO_RCVSHUTDOWN, fs);
			AUDITIREADY(self);
			return;
		}
#endif
		default:
			/* Process below... */
			break;
	}
	AUDITFSPE(fspe);
	AUDITIREADY(self);
	// Queue up the received frameset
	DUMP3(__FUNCTION__, &fs->baseclass, "given to inq->inqsorted");
	if (fspe->inq->inqsorted(fspe->inq, fs)) {
		// It inserted correctly.
		if (seq) {
			if (fspe->acktimeout == 0) {
				fspe->acktimeout = g_get_monotonic_time() + self->acktimeout;
			}
			if (seq->_reqid == 1) {
				_fsprotocol_fsa(fspe, FSPROTO_GOTSTART, fs);
			}
		}
	}else{
		DUMP3(__FUNCTION__, &fs->baseclass, " Frameset failed to go into queue :-(.");
		DEBUGMSG3("%s.%d: seq=%p lastacksent=%p", __FUNCTION__, __LINE__
		,	seq, fspe->lastacksent);
		// One reason for not queueing it is that we've already sent it
		// to our client. If they have already ACKed it, then we will ACK
		// it again automatically - because the application won't be shown
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
			AUDITIREADY(self);
		}
	}
	AUDITIREADY(self);
	AUDITFSPE(fspe);
	TRYXMIT(fspe);
	return;
badret:
	if (fromaddr) {
		UNREF(fromaddr);
	}
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

	DEBUGMSG3("%s.%d: called", __FUNCTION__, __LINE__);
	DUMP3( __FUNCTION__, &fs->baseclass, " is frameset");
	DUMP3( __FUNCTION__, &toaddr->baseclass, " is dest address");

	fspe = self->addconn(self, qid, toaddr);
	if (NULL == fspe) {
		// This can happen if we're shutting down...
		DEBUGMSG3("%s.%d: NULL fspe", __FUNCTION__, __LINE__);
		return FALSE;
	}
	g_return_val_if_fail(NULL != fspe, FALSE);	// Should not be possible...
	AUDITFSPE(fspe);

	if (FSPR_INSHUTDOWN(fspe->state)) {
		DEBUGMSG2("%s.%d: Attempt to send FrameSet while link shutting down - FrameSet ignored."
		,	__FUNCTION__, __LINE__);
		return TRUE;
	}
	DEBUGMSG3("%s.%d: calling fsprotocol_fsa(FSPROTO_REQSEND)", __FUNCTION__, __LINE__);
	_fsprotocol_fsa(fspe, FSPROTO_REQSEND, NULL);

	if (fspe->outq->_q->length == 0) {
		guint64 now = g_get_monotonic_time();
		///@todo: This might be slow if we send a lot of packets to an endpoint
		/// before getting a response, but that's not very likely.
		fspe->parent->unacked = g_list_prepend(fspe->parent->unacked, fspe);
		fspe->nextrexmit = now + self->rexmit_interval;
		fspe->acktimeout = now + self->acktimeout;
	}
	DEBUGMSG4("%s.%d: calling fspe->outq->enq()", __FUNCTION__, __LINE__);
	ret =  fspe->outq->enq(fspe->outq, fs);
	self->io->stats.reliablesends++;
	DEBUGMSG4("%s.%d: calling TRYXMIT()", __FUNCTION__, __LINE__);
	TRYXMIT(fspe);
	AUDITFSPE(fspe);
	DEBUGMSG3("%s.%d: returning %s", __FUNCTION__, __LINE__, (ret ? "TRUE" : "FALSE"));
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
	AUDITFSPE(fspe);
	if (FSPR_INSHUTDOWN(fspe->state)) {
		return FALSE;
	}
	// Send them all -- or none of them...
	ret =  fspe->outq->hasqspace(fspe->outq, g_slist_length(framesets));
	
	if (ret) {
		GSList*	this;
		int	count = 0;
		// Loop over our framesets and send them ouit...
		for (this=framesets; this; this=this->next) {
			FrameSet* fs = CASTTOCLASS(FrameSet, this->data);
			g_return_val_if_fail(fs != NULL, FALSE);
			DEBUGMSG3("%s: queueing up frameset %d of type %d"
			,	__FUNCTION__, count, fs->fstype);
			_fsprotocol_send1(self, fs, qid, toaddr);
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
	// It is possible that this packet may not be in a queue at this point in time.
	// This can happen if there's been a protocol reset from the other end...
	// See code in _fsqueue_inqsorted
	// But if *our* idea of the session id is zero, then we've done a reset on the way out...
	// They may need our ACK for them to shut down properly...
	if (seq->_sessionid != fspe->inq->_sessionid && fspe->inq->_sessionid != 0) {
		DEBUGMSG2("%s.%d: NOT ACKing packet with session id %d - current session id is %d"
		,	__FUNCTION__, __LINE__, seq->_sessionid, fspe->inq->_sessionid);
		return;
	}
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
	GList*		qelem;
	FsQueue*	outq;
	FsProtocol*	parent;
	SeqnoFrame*	lastseq;
	NetIO*		io;
	guint		orig_outstanding;
	gint64		now;

	g_return_if_fail(fspe != NULL);
	outq = fspe->outq;
	parent = fspe->parent;
	lastseq = fspe->lastseqsent;
	io = parent->io;
	orig_outstanding = fspe->outq->_q->length;

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
			DUMP3(__FUNCTION__, &fs->baseclass, " is frameset");
			DUMP3(__FUNCTION__, &seq->baseclass.baseclass, " is frame being sent");
			DUMP3(__FUNCTION__, &fspe->endpoint->baseclass, " is destination endpoint");
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
			DUMP3(__FUNCTION__, &fspe->endpoint->baseclass, " Retransmission target");
			DUMP3(__FUNCTION__, &fs->baseclass, " is frameset being REsent");
			io->sendaframeset(io, fspe->endpoint, fs);
			AUDITFSPE(fspe);

			if (now > fspe->acktimeout) {
				_fsprotocol_fsa(fspe, FSPROTO_ACKTIMEOUT, NULL);
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
		FsProtoElem*	fspe = CASTTOCLASS(FsProtoElem, pending->data);
		next = pending->next;
		AUDITFSPE(fspe);
		TRYXMIT(fspe);
		AUDITFSPE(fspe);
	}
	return TRUE;
}

/// Channel shutdown timer - invokes the FSA with FSPROTO_SHUT_TO
FSTATIC gboolean
_fsprotocol_shuttimeout(gpointer userdata)
{
	FsProtoElem* fspe = CASTTOCLASS(FsProtoElem, userdata);
	_fsprotocol_fsa(fspe, FSPROTO_SHUT_TO, NULL);
	return FALSE;
}

/// Close down (free up) an FSPE object when the timer pops - provided its still closed...
FSTATIC gboolean
_fsprotocol_finalizetimer(gpointer userdata)
{
	FsProtoElem* fspe = CASTTOCLASS(FsProtoElem, userdata);

	if (fspe->state != FSPR_NONE) {
		AUDITFSPE(fspe);
		return FALSE;
	}
	_fsprotocol_fspe_closeconn(fspe);
	return FALSE;
}
/// Dump information about this connection to our logs
FSTATIC void
_fsprotocol_log_conn(FsProtocol* self, guint16 qid, NetAddr* destaddr)
{
	char *	deststr = destaddr->baseclass.toString(&destaddr->baseclass);
	char *	qstr;
	FsProtoElem*	fspe = self->find(self, qid, destaddr);
	if (fspe == NULL) {
		g_info("Cannot dump connection %s - not found.", deststr);
		g_free(deststr); deststr = NULL;
		return;
	}
	qstr = fspe->inq->baseclass.toString(&fspe->inq->baseclass);
	g_info("INPUT queue [%s] = %s", deststr, qstr);
	g_free(qstr);
	qstr = fspe->outq->baseclass.toString(&fspe->outq->baseclass);
	g_info("OUTPUT queue [%s] = %s", deststr, qstr);
	g_free(qstr); qstr = NULL;
	g_free(deststr); deststr = NULL;
}
///@}
