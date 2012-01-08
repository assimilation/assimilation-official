/**
 * @file
 * @brief Implements basic stupid-level dumping capabilities for the server side of things
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <glib.h>
#include <lldp.h>
#include <server_dump.h>


//const gboolean is_all_ascii(const void*, const void *);
//void dump_mem(const void *, const void *);

/// return TRUE if this memory is all printable ASCII
EXP_FUNC
gboolean
is_all_ascii(const void* vmem, const void* vend)
{
	const guchar*	mem = vmem;
	const guchar*	end = vend;
	int	len = end - mem;
	if (len == 0) {
		return FALSE;
	}
	for (; mem < end; ++mem) {
		const guchar*	uc = mem;
		if (isspace(*uc) || (isascii(*uc) && !iscntrl(*uc)) || (mem == end-1 && *uc == 0x00 && len > 1)) {
			continue;
		}
		return FALSE;
	}
	if (len == 1) {
		--mem;
		fprintf(stderr, "STRING WITH 1 CHAR 0x%02x is ASCII\n", *((const unsigned char *)mem));
	}
	return TRUE;
}

/// Dump out memory
void
dump_mem(const void* vstart, const void* vend)
{
	const guchar*	start = vstart;
	const guchar*	end = vend;
	const guchar*	vp;

	if (is_all_ascii(start, end)) {
		fprintf(stdout, "{\"");
		while (start < end) {
			char  startchar = *((const char *)start);
			++start;
			if (startchar == 0x00) {
				break;
			}
			fprintf(stdout, "%c", startchar);
		}
		fprintf(stdout, "\"}");
		fflush(stdout);
		return;
	}
	fprintf(stdout, "{");
	for (vp=start; vp < (const guchar*)end; ++vp) {
		fprintf(stdout, "%s0x%02x"
		,	vp == start ? "" : ", "
		,	(unsigned)(*vp));
		
	}
	fprintf(stdout, "}");
}
