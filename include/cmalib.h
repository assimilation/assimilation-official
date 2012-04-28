/**
 * @file
 * @brief Basic utility functins for the CMA.  Small enough to leave in the client code.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 *
 */

#ifndef _CMALIB_H
#include <projectcommon.h>
#include <configcontext.h>
#include <netaddr.h>
#include <frameset.h>


FrameSet* create_sendexpecthb(ConfigContext*, guint16 msgtype, NetAddr* addrs, int addrcount);
FrameSet* create_setconfig(ConfigContext * cfg);
#endif /* _CMALIB_H */
