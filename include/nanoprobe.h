/**
 * @file
 * @brief include file defining functions to be called by a main to instantiate a nanoprobe.
 * @details This implements the code necessary to start (and stop) a nanoprobe.
 *
 * @author &copy; 2012 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
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
};
extern NanoHbStats nano_hbstats;

void				nano_start_full(const char *initdiscoverpath, guint discover_interval
,						NetGSource* io, ConfigContext* config);
void				nano_shutdown(gboolean statreport);
WINEXPORT PacketDecoder*	nano_packet_decoder(void);

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

#endif /* _NANOPROBE_H */
