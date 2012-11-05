/**
 * @file
 * @brief Implements basic stupid-level dumping capabilities for the server side of things
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
WINEXPORT gboolean
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
