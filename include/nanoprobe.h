/**
 * @file
 * @brief include file defining functions to be called by a main to instantiate a nanoprobe.
 * @details This implements the code necessary to start (and stop) a nanoprobe.
 *
 * This file is part of the Assimilation Project.
 *
 * @author Copyright &copy; 2011, 2012 - Alan Robertson <alanr@unix.sh>
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
 */

#ifndef _NANOPROBE_H
#define _NANOPROBE_H
#include <projectcommon.h>
#include <hblistener.h>
#include <netio.h>
#include <netgsource.h>
#include <configcontext.h>
typedef struct _NanoHbStats NanoHbStats;
struct _NanoHbStats {
	guint64	heartbeat_count;
	guint	dead_count;
	guint	warntime_count;
	guint	comealive_count;
	guint	martian_count;
};
WINEXPORT extern NanoHbStats	nano_hbstats;
extern gboolean		nano_connected;
#define	CMA_KEY_PREFIX		"#CMA#"
#define	CMA_IDENTITY_NAME	"**CMA**"
extern CryptFramePublicKey*	preferred_cma_key_id;

WINEXPORT void				nano_start_full(const char *initdiscoverpath, guint discover_interval
,						NetGSource* io, ConfigContext* config);
WINEXPORT void				nano_shutdown(gboolean statreport);
WINEXPORT PacketDecoder*	nano_packet_decoder(void);
WINEXPORT gboolean		nano_initiate_shutdown(void);
WINEXPORT void			nanoprobe_report_upstream(guint16 reporttype, NetAddr* who, const char * sysname, guint64 howlate);
WINEXPORT void nanoprobe_initialize_keys(void);
WINEXPORT void nanoprobe_associate_cma_key(const char *key_id, ConfigContext *cfg);
extern const char *		procname;		///< process name
WINEXPORT extern int			errcount;	///< error count
WINEXPORT extern GMainLoop*		mainloop;
extern gboolean			nano_shutting_down;
extern GRand*			nano_random;

// Override this if you want to set up a non-standard deadtime agent. */
void (*nanoprobe_deadtime_agent)(HbListener*);
// Override this if you want to set up a non-standard receipt-of-heartbeat agent. */
void (*nanoprobe_heartbeat_agent)(HbListener*);
// Override this if you want to set up a non-standard late heartbeat agent. */
void (*nanoprobe_warntime_agent)(HbListener*, guint64 howlate);
// Override this if you want to set up a non-standard returned-from-the-dead agent. */
void (*nanoprobe_comealive_agent)(HbListener*, guint64 howlate);
// Override if you need to use an HbListener subclass...
extern HbListener* (*nanoprobe_hblistener_new)(NetAddr*, ConfigContext*);

#define	MARTIAN_TIMEOUT	10

#endif /* _NANOPROBE_H */
