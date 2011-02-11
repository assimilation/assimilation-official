/**
 * @file
 * @brief Implements minimal client-oriented LLDP capabilities
 * @details This file contains the minimal LLDP capability for a client - enough for it to be able to
 * understand and validate a CDP packet's structure, return any particular TLV
 * and specifically to be able to locate the chassis id and port id (which the client needs).
 *
 * @author &copy; 2011 - Alan Robertson <alanr@unix.sh>
 * @n
 * Licensed under the GNU Lesser General Public License (LGPL) version 3 or any later version at your option,
 * excluding the provision allowing for relicensing under the GPL at your option.
 */
#include <stdio.h>
#include <string.h>
#include <lldp.h>
#include <lldp.h>
#include <server_dump.h>
#define	DIMOF(a)	(sizeof(a)/sizeof(a[0]))

#define		NETTLV_INITPKTOFFSET	14
#define		NETTLV_HDRSZ	2
unsigned get_oui(const void* ouiptr);
const char * get_oui_string(unsigned oui);
const char * get_lldp_type_string(unsigned lldptype);
void dump_lldp_packet(const void*, const void*);

static const char *	lldptypenames[] =
{	"end"
,	"chassis_id"
,	"port_id"
,	"ttl"
,	"port description"
,	"system_name"
,	"system_description"
,	"capabilities"
,	"mgmt_address"
};

/// Convert the OUI given a pointer to the OUI field.
/// @return the OUI as an unsigned.
unsigned
get_oui(const void* ouiptr) ///<[in] Pointer to the first byte of an OUI field in a TLV entry
{
	const unsigned char* ucptr = ouiptr;
	unsigned	ret = 0;
	int		j;
	for (j=0; j < 3; j++) {
		ret <<= 8;
		ret |= *ucptr;
		++ucptr;
	}
	return ret;
}
static struct {
	unsigned	oui;
	const char*	string;
}ouimap[] =
{	{0x000FAC, "IEEE 802.11"}
,	{0x00120F, "IEEE 802.3"}
,	{0x00190D, "IEEE 1394c"}
,	{0x001B19, "IEEE I&M Society TC9"}
,	{0x001BC5, "IEEE Registration Authority"}
,	{0x0050C2, "IEEE REGISTRATION AUTHORITY"}
,	{0x0080C2, "IEEE 802.1"}
,	{0x1C129D, "IEEE PES PSRC/SUB"}
,	{0x58D08F, "IEEE 1904.1"}
,	{0x90E0F0, "IEEE P1722"}
};

/// Convert an Organizational-Unique-Identifier to a human-readable string.
/// @return pointer to a constant string containing the OUI name if known,
/// or a static buffer with an ASCII represention of the OUI if unknown.
/// Although there are lots of OUIs, we know about the ones most likely to
/// appear in an LLDP Org-Specific TLV. 
const char *
get_oui_string(unsigned oui)	///<[in] A (three-byte) OUI as an unsigned
{
	int	j;
	static char	ret[64];

	for (j=0; j < DIMOF(ouimap); ++j) {
		if (oui == ouimap[j].oui) {
			return ouimap[j].string;
		}
	}
	snprintf(ret, sizeof(ret), "OUI 0x%06x", oui);
	return ret;
}


/// Translate an LLDP TLV packet type into a string
/// @return a constant string representing the name of the LLDP TLV type.
/// This function always returns a constant string, never a malloced
/// or static buffer string.
const char *
get_lldp_type_string(unsigned lldptype)	///<[in] LLDP TLV type
{
	if (lldptype < DIMOF(lldptypenames)) {
		return lldptypenames[lldptype];
	}
	if (lldptype == LLDP_TLV_ORG_SPECIFIC) {
		return "org_specific";
	}
	return "UnknownLLDPtype";
}
/// Dump an LLDP packet to stdout
void
dump_lldp_packet(const void* tlv_vpv, 	///<[in] Pointer to the first byte of the packet
                 const void* tlv_vpendv)///<[in] Pointer to the first byte past the end of the packet
{
	const guchar* tlv_vp = tlv_vpv;
	const guchar* tlv_vpend = tlv_vpendv;
	if (tlv_vp == NULL || !is_valid_lldp_packet(tlv_vp, tlv_vpend)) {
		fprintf(stdout, "%ld byte lldptlv structure at address %p is not valid.\n"
		,	(long)(tlv_vpend-tlv_vp), tlv_vp);
		return;
	}
	for (tlv_vp = get_lldptlv_first(tlv_vp, tlv_vpend)
	;	NULL != tlv_vp
	;	tlv_vp = get_lldptlv_next(tlv_vp, tlv_vpend)) {
		unsigned		ttype	= get_lldptlv_type(tlv_vp, tlv_vpend);
		gsize			tlen	= get_lldptlv_len(tlv_vp, tlv_vpend);
		const unsigned char*	tbody	= get_lldptlv_body(tlv_vp, tlv_vpend);


		if (ttype == LLDP_TLV_ORG_SPECIFIC) {
			unsigned oui = get_oui(tbody);
			unsigned subtype = tbody[3];
			fprintf(stdout, "Org Specific TLV, %s subtype=%d sublength: %zd, values: "
			,	get_oui_string(oui),	subtype, tlen-4);
			dump_mem(tbody+4, tbody+tlen);
			fprintf(stdout, "\n");
			continue;
		}
			
		fprintf(stdout, "TLV type: %s, length: %d, values: "
		,	get_lldp_type_string(ttype), (int)tlen);
		dump_mem(tbody, tbody+tlen);
		fprintf(stdout, "\n");
	}
}
