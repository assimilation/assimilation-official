/**
 * @file
 * @brief Functions for server-side dumping of LLDP and CDP packets.
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
#ifndef _SERVER_DUMP_H
#	define _SERVER_DUMP_H
#	include <projectcommon.h>
WINEXPORT void dump_cdp_packet(const void* packet, const void* packend);
WINEXPORT void dump_lldp_packet(const void* packet, const void* packend);
WINEXPORT gboolean is_all_ascii(const void* mem, const void* end);
WINEXPORT void dump_mem(const void * start, const void * end);
#endif/*_SERVER_DUMP_H*/
