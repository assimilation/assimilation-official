/**
 * @file
 * @brief Functions for server-side dumping of LLDP and CDP packets.
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#ifdef _MSC_VER
#define EXP_FUNC __declspec( dllexport )
#else
#define EXP_FUNC
#endif
typedef int bool_t;
EXP_FUNC void dump_cdp_packet(const void* packet, const void* packend);
EXP_FUNC void dump_lldp_packet(const void* packet, const void* packend);
EXP_FUNC bool_t is_all_ascii(const void* mem, const void* end);
EXP_FUNC void dump_mem(const void * start, const void * end);
