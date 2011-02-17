/**
 * @file
 * @brief Semi-Abstract class (yes, really) defining discovery objects
 * @details It is only instantiated by derived classes.
 *
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option.
 * excluding the provision allowing for relicensing under the GPL at your option.
 */

#ifndef _DISCOVERY_H
#define _DISCOVERY_H
#include <projectcommon.h>
///@{
/// @ingroup Discovery

typedef struct _Discovery Discovery;
struct _Discovery {
	const char*	(*discoveryname)	(Discovery* self);	///< Which discovery object is this?
	gboolean	(*discover)		(Discovery* self);	///< Perform the discovery
	void		(*finalize)		(Discovery* self);	///< called during object destruction
	guint		(*discoverintervalsecs)	(Discovery* self);	///< How often to re-discover this? (in seconds)
	guint		_timerid;				///< Timer id for repeating discovery
};

Discovery* discovery_new(gsize objsize);
void discovery_register(Discovery* self);

///@}

#endif /* _DISCOVERY_H */
