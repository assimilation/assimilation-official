/**
 * @file
 * @brief Implements the Network Discovery action for Windows .net platfom
 * @details We discover all the local NICs and their IP address assignments, and report that back as JSON
 *          to standard output.  Inquiring CMAs want to know!
 *
 * @author  Roger Massey <sadsaddle(at)gmail(dot)(com)> - Copyright &copy; 2013 - Assimilation Systems Limited
 * @n
 *  This file is part of the Assimilation Project.
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
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Management;
using System.ComponentModel;
using System.Web.Script.Serialization;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using System.Net;
using System.Net.Sockets;
using System.Net.NetworkInformation;
using System.Diagnostics;

using netconfig;

namespace netconfig
{

    /// This class implements network discovery for the Assimilation Project
    public class NetDisc
    {
        public const Int32 MAX_ADAPTER_NAME = 128;
        public const Int32 MAX_ADAPTER_NAME_LENGTH = 256;
        public const Int32 MAX_ADAPTER_DESCRIPTION_LENGTH = 128;
        public const Int32 MAX_ADAPTER_ADDRESS_LENGTH = 8;
        public const UInt32 ERROR_BUFFER_OVERFLOW = (UInt32)111;
        public const Int32 ERROR_SUCCESS = 0;

        [Flags]
        public enum GAA_FLAGS
        {
            GAA_NONE = 0x0000,
            GAA_SKIP_UNICAST = 0x0001,
            GAA_SKIP_ANYCAST = 0x0002,
            GAA_SKIP_MULTICAST = 0x0004,
            GAA_SKIP_DNS_SERVER = 0x0008,
            GAA_INCLUDE_PREFIX = 0x0010,
            GAA_SKIP_FRIENDLY_NAME = 0x0020,
            GAA_INCLUDE_WINS_INFO = 0x0040,
            GAA_INCLUDE_GATEWAYS = 0x0080,
            GAA_INCLUDE_ALL_INTERFACES = 0x0100,
            GAA_INCLUDE_ALL_COMPARTMENTS = 0x0200,
            GAA_INCLUDE_TUNNEL_BINDINGORDER = 0x0400
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
        public struct SOCKET_ADDRESS
        {
            public IntPtr lpSockAddr;
            public Int32 iSockaddrLength;
        }
        public enum IP_PREFIX_ORIGIN
        {
            IpPrefixOriginOther = 0,
            IpPrefixOriginManual,
            IpPrefixOriginWellKnown,
            IpPrefixOriginDhcp,
            IpPrefixOriginRouterAdvertisement
        }
        public enum IP_SUFFIX_ORIGIN
        {
            IpSuffixOriginOther = 0,
            IpSuffixOriginManual,
            IpSuffixOriginWellKnown,
            IpSuffixOriginDhcp,
            IpSuffixOriginLinkLayerAddress,
            IpSuffixOriginRandom
        }
        public enum IP_DAD_STATE
        {
            IpDadStateInvalid = 0,
            IpDadStateTentative,
            IpDadStateDuplicate,
            IpDadStateDeprecated,
            IpDadStatePreferred
        }
        public enum SCOPE_LEVEL
        {
            ScopeLevelInterface = 1,
            ScopeLevelLink = 2,
            ScopeLevelSubnet = 3,
            ScopeLevelAdmin = 4,
            ScopeLevelSite = 5,
            ScopeLevelOrganization = 8,
            ScopeLevelGlobal = 14
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
        public struct IP_ADAPTER_UNICAST_ADDRESS
        {
            public UInt32 Length;
            public UInt32 Flags;

            public IntPtr Next;
            public SOCKET_ADDRESS Address;
            public IP_PREFIX_ORIGIN PrefixOrigin;
            public IP_SUFFIX_ORIGIN SuffixOrigin;
            public IP_DAD_STATE DadState;
            public UInt32 ValidLifetime;
            public UInt32 PreferredLifetime;
            public UInt32 LeaseLifetime;
            public Byte OnLinkPrefixLength;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct IP_ADAPTER_GATEWAY_ADDRESS {
            public UInt64 Alignment;
            public IntPtr Next;
            SOCKET_ADDRESS Address;
        } 
 
        [StructLayout(LayoutKind.Sequential)]
        public struct SOCKADDR
        {
            public Int32 sa_family;       /* address family */

            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4)]
            public byte[] sa_data;         /* up to 4 bytes of direct address */
        };
        [StructLayout(LayoutKind.Sequential)]
        public struct SOCKADDRIPV6
        {
            public Int64 sa_family;       /* address family */

            [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
            public byte[] sa_data;         /* up to 16 bytes of direct address */
        };

        private static TraceSource mySource =
            new TraceSource("netconfig");

        /// Main program for Assimilation Project network discovery for Windows
        static void Main(string[] args)
        {
            mySource.Switch = new SourceSwitch("netconfig", "Error");
            mySource.Listeners.Remove("Default");
            EventLogTraceListener evl = new EventLogTraceListener("netconfig");

            //Off, Critical, Error,	Warning, Information, Verbose, ActivityTracing,	All
            evl.Filter = new EventTypeFilter(SourceLevels.All);

            mySource.Listeners.Add(evl);

            Trace.WriteLine("start netconfig");

            // build the json output string
            String jout = NetworkExplorer();

            // add the final brace
            jout += "}";

            // send to our stdout
            System.Console.WriteLine(jout);

            Trace.WriteLine("end   netconfig");
            mySource.Close();
        }

        /// Does the real work of doing network discovery for Windows
        static private String NetworkExplorer()
        {
            List<IP_ADAPTER_ADDRESSES> aAL;  // a list of all adapters
            StringBuilder json_out = new StringBuilder();  // json string builder
            bool firstadapter = true;   // to comma or not to comma

            Trace.WriteLine("start NetworkExplorer");
            // build the boiler plate
            json_out.Append("{\n  \"discovertype\": \"netconfig\",\n  \"description\": \"IP Network Configuration\",\n");
            json_out.Append("  \"source\": \"netconfig\",\n");
            json_out.Append("  \"host\": ");

            json_out.Append("\"");
            json_out.Append(System.Environment.GetEnvironmentVariable("COMPUTERNAME"));
            json_out.Append("\",\n");

            json_out.Append("   \"data\": {\n");

            //get the list of all adapters
            Adapter.GetAdaptersAddresses(AddressFamily.Unspecified, GAA_FLAGS.GAA_NONE, out aAL);

            foreach (IP_ADAPTER_ADDRESSES A in aAL)
            {
                string tmps;
                string adapterName = Marshal.PtrToStringAnsi(A.AdapterName);
                string FriendlyName = Marshal.PtrToStringAuto(A.FriendlyName);
                string description = Marshal.PtrToStringAuto(A.Description);

                uint operationstatus = A.OperStatus;
                if (operationstatus != 1)
                {
                    continue;
                }
                /*
                if (A.IfType == 24)  // loopback
                {
                    continue;
                }
                */
                if (firstadapter)
                {
                    json_out.Append("    \"");
                    firstadapter = false;
                }
                else
                {
                    json_out.Append(",\n    \"");
                }
                json_out.Append(FriendlyName);
                json_out.Append("\": {\n");

                // build the mac address string
                tmps = "";
                for (int i = 0; i < 6; i++)
                {
                    tmps += string.Format("{0:X2}", A.PhysicalAddress[i]);
                    if (i < 5)
                    {
                        tmps += ":";
                    }
                }
                
                json_out.Append("      \"address\": \"");
                json_out.Append(tmps);
                json_out.Append("\",\n");

                json_out.Append("      \"mtu\": ");
                json_out.Append(A.Mtu);
                json_out.Append(",\n");
               
                // this doesn't work on my xp development machine, this field + others require vista or later
                //json_out.Append("      \"speed\": ");    //doesn't work
                //json_out.Append(A.TransmitLinkSpeed);
                //json_out.Append(",\n");

                json_out.Append("      \"operstate\": \"");
                json_out.Append((operationstatus == 1 ? "UP" : "DOWN"));
                json_out.Append("\",\n");

                // check for ip address
                IP_ADAPTER_UNICAST_ADDRESS ipua;
                IntPtr next = A.FirstUnicastAddress;
                bool firstipaddr = true;

                json_out.Append("      \"ipaddrs\": {\n");

                if (next != (IntPtr)0)
                {
                       /*TODO -- doesn't work on xp, it should on vista or later */
                       // IP_ADAPTER_GATEWAY_ADDRESS ipG;
                       // IntPtr gNext = A.FirstGatewayAddress;
                       // if (gNext != (IntPtr)0)
                       // {
                       //     ipG = (IP_ADAPTER_GATEWAY_ADDRESS)Marshal.PtrToStructure(gNext, typeof(IP_ADAPTER_GATEWAY_ADDRESS));
                       // }
                       /*TODO*/
                    do
                    {
                        ipua = (IP_ADAPTER_UNICAST_ADDRESS)Marshal.PtrToStructure(next, typeof(IP_ADAPTER_UNICAST_ADDRESS));
                        SOCKET_ADDRESS sock_addr;
                        sock_addr = (SOCKET_ADDRESS)ipua.Address;
                        next = ipua.Next;

                        SOCKADDR sockaddr;
                        SOCKADDRIPV6 sockaddripv6;
                        IPAddress ipaddr = null;

                        //Marshal memory pointer into a struct
                        sockaddr = (SOCKADDR)Marshal.PtrToStructure(sock_addr.lpSockAddr, typeof(SOCKADDR));

                        //Check if the address family is IPV4
                        if (sockaddr.sa_family == (Int32)System.Net.Sockets.AddressFamily.InterNetwork)
                        {
                            ipaddr = new IPAddress(sockaddr.sa_data);
                        }
                        else if (sockaddr.sa_family == (Int32)System.Net.Sockets.AddressFamily.InterNetworkV6)
                        {
                            //Marshal memory pointer into a struct
                            sockaddripv6 = (SOCKADDRIPV6)Marshal.PtrToStructure(sock_addr.lpSockAddr, typeof(SOCKADDRIPV6));
                            ipaddr = new IPAddress(sockaddripv6.sa_data);
                        }

                        if (ipaddr == null)
                        {
                            Trace.WriteLine("unable to create socket" + sockaddr.ToString());
                            throw new MemberAccessException("Could not parse the interface's IP Address.");
                        }

                        int bc = 128;
                        String ba = "";

                        // the mumbo jumbo in GetIPv4gateway gets netmask & broadcast address for ipv4 on xp
                        // it probably could be deleted if we required vista or later
                        if (sockaddr.sa_family == (Int32)System.Net.Sockets.AddressFamily.InterNetwork)
                        {
                            GetIPv4gateway(A, ipaddr, out bc, out ba);
                        }

                        if (firstipaddr)
                        {
                            json_out.Append("        \"");
                            firstipaddr = false;
                        }
                        else
                        {
                            json_out.Append(",\n        \"");
                        }
                        json_out.Append(ipaddr.ToString() + "/" + bc.ToString());

                        if (ipaddr.AddressFamily == AddressFamily.InterNetworkV6)
                        {
                            json_out.Append("\": {");
                            if (A.IfType == 24)
                            { // loopback
                                json_out.Append("\"scope\":\"host\"");
                            }
                            else if (ipaddr.IsIPv6LinkLocal)
                            {
                                json_out.Append("\"scope\":\"link\"");
                            }
                            else if (ipaddr.IsIPv6SiteLocal)
                            {
                                json_out.Append("\"scope\":\"host\"");
                            }
                            else if (ipaddr.IsIPv6Multicast)
                            {
                                json_out.Append("\"scope\":\"multicast\"");
                            }
                            else
                            {
                                json_out.Append("\"scope\":\"global\"");
                            }
                            json_out.Append("}");
                        }
                        else
                        {
                            if (ba.Length > 0)
                            {
                                json_out.Append("\": {\"brd\":\"");
                                json_out.Append(ba);
                                json_out.Append("\"}\n");
                            }
                            else
                            {
                                json_out.Append("\": {}");
                            }

                            
                        }

                    } while (next != (IntPtr)0);
                    json_out.Append("      }\n");
                }
                json_out.Append("    }\n");
            }
            json_out.Append("  }\n");

            Trace.WriteLine("end   NetworkExplorer");

            return (json_out.ToString());
        }

        public static void GetIPv4gateway(IP_ADAPTER_ADDRESSES A, IPAddress ipaddr, out int bc, out string ba)
        {
            bc = 32;
            ba = "";
            string first_multi = "";

            Trace.WriteLine("start GetIPv4gateway");

            NetworkInterface[] adapters = NetworkInterface.GetAllNetworkInterfaces();
            foreach (NetworkInterface adapter in adapters)
            {
                // match c# adapter to win32 adapter A passed in
                if (adapter.Name.CompareTo(Marshal.PtrToStringAuto(A.FriendlyName)) != 0)
                {
                    continue;
                }
                // get a c# view of adapter properties
                IPInterfaceProperties adapterProperties = adapter.GetIPProperties();

                // get the first multicast address
                MulticastIPAddressInformationCollection multiCast = adapterProperties.MulticastAddresses;
                if (multiCast != null)
                {
                    foreach (IPAddressInformation multi in multiCast)
                    {
                        if (first_multi.Length == 0)
                        {
                            multi.Address.ToString();
                        }
                        Trace.WriteLine("       multi " + multi.Address.ToString());
                        continue;
                    }
                 }
                
                UnicastIPAddressInformationCollection uniCast = adapterProperties.UnicastAddresses;
                if (uniCast != null)
                {
                    foreach (UnicastIPAddressInformation uni in uniCast)
                    {
                        // chop off any % char and what trails it
                        string s1 = uni.Address.ToString();
                        string s2 = ipaddr.ToString();
                        if (s1.IndexOf((char)'%') != -1)
                        {
                            s1 = s1.Substring(0, s1.IndexOf((char)'%'));
                        }
                        if (s2.IndexOf((char)'%') != -1)
                        {
                            s2 = s2.Substring(0, s2.IndexOf((char)'%'));
                        }
                        if (s1.Equals(s2))
                        {
                            Trace.WriteLine("unicast addr " + s1);
                            if (uni.IPv4Mask != null)
                            {
                                byte[] bcast_add = uni.Address.GetAddressBytes();

                                // check for ipv4
                                if (uni.IPv4Mask.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork)
                                {
                                    ba = uni.IPv4Mask.ToString();
                                    
                                    byte[] ipAdressBytes = uni.Address.GetAddressBytes();
                                    byte[] subnetMaskBytes = uni.IPv4Mask.GetAddressBytes();

                                    if (ipAdressBytes.Length != subnetMaskBytes.Length)
                                    {
                                        if (ipAdressBytes.Length > 4)
                                        {
                                            Trace.WriteLine("    ipAdressBytes.Length = " + ipAdressBytes.Length.ToString());
                                            Trace.WriteLine("    different addr length " + uni.Address.ToString() + " " + uni.IPv4Mask.ToString());
                                            ba = first_multi;
                                            bc = 64;
                                        }
                                        break;
                                    }
                                    bc = 0;
                                    int totbits = subnetMaskBytes.Length * 8;
                                    for (int i = 0; i < subnetMaskBytes.Length; i++)
                                    {
                                        for (int j = 0; j < totbits; j++)
                                        {
                                            byte maskbit = (byte)(1 << j);
                                            if ((maskbit & subnetMaskBytes[i]) != 0)
                                            {
                                                bc++;
                                            }
                                            else
                                            {
                                                bcast_add[i] |= maskbit;
                                            }
                                        }
                                    }
                                
                                    StringBuilder sb = new StringBuilder(bcast_add.Length * 4);
                                    foreach (byte b in bcast_add)
                                    {
                                        sb.AppendFormat("{0}", b);
                                        sb.Append(".");
                                    }
                                    sb.Remove(sb.Length - 1, 1);
                                    ba = sb.ToString();
                                }
                            }
                            else
                            {
                                ba = first_multi;
                                if (A.IfType == 24)
                                {  // loopback
                                    bc = 8;
                                }
                                else
                                {
                                    bc = 32;
                                }
                                break;
                            }
                        }
                    }
                }
                /* the code below doesn't display any gateways on win7, seems like it should
                if (System.Environment.OSVersion.Version.Major >= 6)   //vista or later
                {  
                    Trace.WriteLine("Gateways");
                    GatewayIPAddressInformationCollection addresses = adapterProperties.GatewayAddresses;
                    if (addresses.Count > 0)
                    {
                        Trace.WriteLine(adapter.Description);
                        foreach (GatewayIPAddressInformation address in addresses)
                        {
                            Trace.WriteLine("  Gateway Address : {0}",
                                address.Address.ToString());
                        }
                    }
                }
                */
                break;
            }
            Trace.WriteLine("end   GetIPv4gateway");
        }
    }

    /// Class to discover all our adapters
    public class Adapter
    {
        [DllImport("Iphlpapi.dll", CharSet = CharSet.Auto)]
        private static extern uint GetAdaptersAddresses(uint Family,
                                                        uint flags,
                                                        IntPtr Reserved,
                                                        IntPtr PAdaptersAddresses,
                                                        ref uint pOutBufLen);

        public static void GetAdaptersAddresses(System.Net.Sockets.AddressFamily addressFamily,
            NetDisc.GAA_FLAGS gaaFlags,
            out List<IP_ADAPTER_ADDRESSES> adaptAddrList)
        {

            adaptAddrList = new List<IP_ADAPTER_ADDRESSES>();
            UInt32 size = (UInt32)Marshal.SizeOf(typeof(IP_ADAPTER_ADDRESSES));
            IntPtr pAdaptAddrBuffer = Marshal.AllocHGlobal((Int32)size);

            uint result = GetAdaptersAddresses((UInt32)addressFamily, (UInt32)gaaFlags, (IntPtr)0, pAdaptAddrBuffer, ref size);

            if (result == NetDisc.ERROR_BUFFER_OVERFLOW)
            {
                Marshal.FreeHGlobal(pAdaptAddrBuffer);
                pAdaptAddrBuffer = Marshal.AllocHGlobal((Int32)size);
                result = GetAdaptersAddresses((UInt32)addressFamily, (UInt32)gaaFlags, (IntPtr)0, pAdaptAddrBuffer, ref size);
            }

            if (result != NetDisc.ERROR_SUCCESS)
            {
                throw new Win32Exception((Int32)result, "GetAdaptersAddresses FAILED.");
            }

            if ((result == NetDisc.ERROR_SUCCESS) && (pAdaptAddrBuffer != IntPtr.Zero))
            {
                IntPtr pTemp = pAdaptAddrBuffer;

                do
                {
                    IP_ADAPTER_ADDRESSES aAB = new IP_ADAPTER_ADDRESSES();
                    aAB = (IP_ADAPTER_ADDRESSES)Marshal.PtrToStructure((IntPtr)pTemp, typeof(IP_ADAPTER_ADDRESSES));
                    adaptAddrList.Add(aAB);

                    pTemp = (IntPtr)aAB.Next;
                }
                while (pTemp != IntPtr.Zero);
            }
        }
    }
    /* the win32 struct definition, ZoneIndices is the last valid field on xp
     typedef struct _IP_ADAPTER_ADDRESSES {
    union {
      ULONGLONG Alignment;
      struct {
        ULONG Length;
        DWORD IfIndex;
      };
    };
    struct _IP_ADAPTER_ADDRESSES  *Next;
    PCHAR                              AdapterName;
    PIP_ADAPTER_UNICAST_ADDRESS        FirstUnicastAddress;
    PIP_ADAPTER_ANYCAST_ADDRESS        FirstAnycastAddress;
    PIP_ADAPTER_MULTICAST_ADDRESS      FirstMulticastAddress;
    PIP_ADAPTER_DNS_SERVER_ADDRESS     FirstDnsServerAddress;
    PWCHAR                             DnsSuffix;
    PWCHAR                             Description;
    PWCHAR                             FriendlyName;
    BYTE                               PhysicalAddress[MAX_ADAPTER_ADDRESS_LENGTH];
    DWORD                              PhysicalAddressLength;
    DWORD                              Flags;
    DWORD                              Mtu;
    DWORD                              IfType;
    IF_OPER_STATUS                     OperStatus;
    DWORD                              Ipv6IfIndex;
    DWORD                              ZoneIndices[16];
    PIP_ADAPTER_PREFIX                 FirstPrefix;
    ULONG64                            TransmitLinkSpeed;
    ULONG64                            ReceiveLinkSpeed;
    PIP_ADAPTER_WINS_SERVER_ADDRESS_LH FirstWinsServerAddress;
    PIP_ADAPTER_GATEWAY_ADDRESS_LH     FirstGatewayAddress;
    ULONG                              Ipv4Metric;
    ULONG                              Ipv6Metric;
    IF_LUID                            Luid;
    SOCKET_ADDRESS                     Dhcpv4Server;
    NET_IF_COMPARTMENT_ID              CompartmentId;
    NET_IF_NETWORK_GUID                NetworkGuid;
    NET_IF_CONNECTION_TYPE             ConnectionType;
    TUNNEL_TYPE                        TunnelType;
    SOCKET_ADDRESS                     Dhcpv6Server;
    BYTE                               Dhcpv6ClientDuid[MAX_DHCPV6_DUID_LENGTH];
    ULONG                              Dhcpv6ClientDuidLength;
    ULONG                              Dhcpv6Iaid;
    PIP_ADAPTER_DNS_SUFFIX             FirstDnsSuffix;
  } IP_ADAPTER_ADDRESSES, *PIP_ADAPTER_ADDRESSES;

       */
    /*typedef struct _IP_ADAPTER_GATEWAY_ADDRESS_LH {
    union {
        ULONGLONG Alignment;
        struct {
            ULONG Length;
            DWORD Reserved;
        };
    };
    struct _IP_ADAPTER_GATEWAY_ADDRESS_LH *Next;
    SOCKET_ADDRESS Address;
} IP_ADAPTER_GATEWAY_ADDRESS_LH, *PIP_ADAPTER_GATEWAY_ADDRESS_LH;
     * */

    /// IP_ADAPTER_ADDRESSES defines the layout of information we know about an adapter Address
    // the c# layout of the above struct _IP_ADAPTER_ADDRESSES
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Auto)]
    public class IP_ADAPTER_ADDRESSES
    {
        public uint Length;
        public uint IfIndex;


        public IntPtr Next;
        public IntPtr AdapterName;
        public IntPtr FirstUnicastAddress;
        public IntPtr FirstAnycastAddress;
        public IntPtr FirstMulticastAddress;
        public IntPtr FirstDnsServerAddress;

        public IntPtr DnsSuffix;
        public IntPtr Description;

        public IntPtr FriendlyName;

        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 8)]
        public Byte[] PhysicalAddress;

        public uint PhysicalAddressLength;
        public uint flags;
        public uint Mtu;
        public uint IfType;
        
        public uint OperStatus;

        public uint Ipv6IfIndex;

        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 16)]
        public uint[] ZoneIndices;

        public IntPtr FirstPrefix;
        
        public UInt64 TransmitLinkSpeed;
        public UInt64 ReceiveLinkSpeed;
        public IntPtr FirstWinsServerAddress;
        public IntPtr  FirstGatewayAddress;
        
    }

}
