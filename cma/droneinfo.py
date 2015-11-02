#!/usr/bin/env python
# vim: smartindent tabstop=4 shiftwidth=4 expandtab number colorcolumn=100
#
# This file is part of the Assimilation Project.
#
# Copyright (C) 2011, 2012 - Alan Robertson <alanr@unix.sh>
#
#  The Assimilation software is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  The Assimilation software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with the Assimilation Project software.  If not, see http://www.gnu.org/licenses/
#
#
'''
We implement the Drone class - which implements all the properties of
drones as a Python class.
'''
import time, sys
#import os, traceback
from cmadb import CMAdb
from consts import CMAconsts
from store import Store
from graphnodes import nodeconstructor, RegisterGraphClass, IPaddrNode, SystemNode, BPRules, \
    JSONMapNode
from frameinfo import FrameSetTypes, FrameTypes
from AssimCclasses import pyNetAddr, pyConfigContext, DEFAULT_FSP_QID, pyCryptFrame
from assimevent import AssimEvent
from cmaconfig import ConfigFile


@RegisterGraphClass
#droneinfo.py:39: [R0904:Drone] Too many public methods (21/20)
#droneinfo.py:39: [R0902:Drone] Too many instance attributes (11/10)
# pylint: disable=R0904,R0902
class Drone(SystemNode):
    '''Everything about Drones - endpoints that run our nanoprobes.

    There are two Cypher queries that get initialized later:
    Drone.IPownerquery_1: Given an IP address, return th SystemNode (probably Drone) 'owning' it.
    Drone.OwnedIPsQuery:  Given a Drone object, return all the IPaddrNodes that it 'owns'
    '''
    _JSONprocessors = None
    IPownerquery_1 = None
    OwnedIPsQuery = None
    IPownerquery_1_txt = '''START n=node:IPaddrNode({ipaddr})
                            MATCH n<-[:%s]-()<-[:%s]-drone
                            return drone LIMIT 1'''
    OwnedIPsQuery_txt = '''START d=node({droneid})
                           MATCH d-[:%s]->()-[:%s]->ip
                           return ip'''
    JSONattrnames =        '''START d=node({droneid})
                           MATCH d-[r:jsonattr]->()
                           return r.jsonname as key'''
    JSONsingleattr =      '''START d=node({droneid})
                           MATCH d-[r:jsonattr]->(json)
                           WHERE r.jsonname={jsonname}
                           return json'''

    HASH_PREFIX = 'JSON__hash__'


    # R0913: Too many arguments to __init__()
    # pylint: disable=R0913
    def __init__(self, designation, port=None, startaddr=None
    ,       primary_ip_addr=None, domain=CMAconsts.globaldomain
    ,       status= '(unknown)', reason='(initialization)', roles=None, key_id=''):
        '''Initialization function for the Drone class.
        We mainly initialize a few attributes from parameters as noted above...

        The first time around we also initialize a couple of class-wide query
        strings for a few queries we know we'll need later.

        We also behave as though we're a dict from the perspective of JSON attributes.
        These discovery strings are converted into pyConfigContext objects and are
        then searchable like dicts themselves - however updating these dicts has
        no direct impact on the underlying JSON strings stored in the database.

        The reason for treating these as a dict is so we can easily change
        the implementation to put JSON strings in separate nodes, or perhaps
        eventually in a separate data store.

        This is necessary because the performance of putting lots of really large
        strings in Neo4j is absolutely horrible. Putting large strings in is dumb
        and what Neo4j does with them is even dumber...
        The result is at least DUMB^2 -not 2*DUMB ;-)
        '''
        SystemNode.__init__(self, domain=domain, designation=designation)
        if roles is None:
            roles = ['host', 'drone']
        self.addrole(roles)
        self._io = CMAdb.io
        self.lastjoin = 'None'
        self.status = status
        self.reason = reason
        self.key_id = key_id
        self.startaddr = str(startaddr)
        self.primary_ip_addr = str(primary_ip_addr)
        self.time_status_ms = int(round(time.time() * 1000))
        self.time_status_iso8601 = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        if port is not None:
            self.port = int(port)
        else:
            self.port = None

        self.monitors_activated = False

        if Drone.IPownerquery_1 is None:
            Drone.IPownerquery_1 = (Drone.IPownerquery_1_txt
                                    % (CMAconsts.REL_ipowner, CMAconsts.REL_nicowner))
            Drone.OwnedIPsQuery_subtxt = (Drone.OwnedIPsQuery_txt    \
                                          % (CMAconsts.REL_nicowner, CMAconsts.REL_ipowner))
            Drone.OwnedIPsQuery =  Drone.OwnedIPsQuery_subtxt
        self.set_crypto_identity()
        if Store.is_abstract(self) and not CMAdb.store.readonly:
            #print 'Creating BP rules for', self.designation
            from bestpractices import BestPractices
            bprules = CMAdb.io.config['bprulesbydomain']
            rulesetname = bprules[domain] if domain in bprules else bprules[CMAconsts.globaldomain]
            for rule in BestPractices.gen_bp_rules_by_ruleset(CMAdb.store, rulesetname):
                #print >> sys.stderr, 'ADDING RELATED RULE SET for', \
                    #self.designation, rule.bp_class, rule
                CMAdb.store.relate(self, CMAconsts.REL_bprulefor, rule,
                                   properties={'bp_class': rule.bp_class})

    def gen_current_bp_rules(self):
        '''Return a generator producing all the best practice rules
        that apply to this Drone.
        '''
        return CMAdb.store.load_related(self, CMAconsts.REL_bprulefor, BPRules)

    def get_bp_head_rule_for(self, trigger_discovery_type):
        '''
        Return the head of the ruleset chain for the particular set of rules
        that go with this particular node
        '''
        rules = CMAdb.store.load_related(self, CMAconsts.REL_bprulefor, BPRules)
        for rule in rules:
            if rule.bp_class == trigger_discovery_type:
                return rule
        return None

    def get_merged_bp_rules(self, trigger_discovery_type):
        '''Return a merged version of the best practices rules for this
        particular discovery type.  This involves creating a hash table
        of rules, where the contents are merged together such that we return
        a single consolidated view of the rules to our viewer.
        We start out with the head of the ruleset chain and then merge in the
        ones its based on.

        We return a dict-like object reflecting this merger suitable
        for evaluating the rules. You just walk the set of rules
        and evaluate them.
        '''
        # Although we ought to hit the database once and get the PATH of the
        # rules in one fell swoop, we don't yet support PATHs, so we're going
        # at it the somewhat slower way -- incrementally.
        start = self.get_bp_head_rule_for(trigger_discovery_type)
        if start is None:
            return {}
        ret = start.jsonobj()
        this = start
        while True:
            nextrule = None
            for nextrule in CMAdb.store.load_related(this, CMAconsts.REL_basis, BPRules):
                break
            if nextrule is None:
                break
            nextobj = nextrule.jsonobj()
            for elem in nextobj:
                if elem not in ret:
                    ret[elem] = nextobj[elem]
            this = nextrule
        return ret


    def get_owned_ips(self):
        '''Return a list of all the IP addresses that this Drone owns'''
        params = {'droneid':Store.id(self)}
        if CMAdb.debug:
            print >> sys.stderr, ('IP owner query:\n%s\nparams %s'
            %   (Drone.OwnedIPsQuery_subtxt, str(params)))

        return [node for node in CMAdb.store.load_cypher_nodes(Drone.OwnedIPsQuery, IPaddrNode
        ,       params=params)]

    def crypto_identity(self):
        '''Return the Crypto Identity that should be associated with this Drone
        Note that this current algorithm isn't ideal for a multi-tenant environment.
        '''
        return self.designation

    def logjson(self, origaddr, jsontext):
        'Process and save away JSON discovery data.'
        assert CMAdb.store.has_node(self)
        jsonobj = pyConfigContext(jsontext)
        if not 'discovertype' in jsonobj or not 'data' in jsonobj:
            CMAdb.log.warning('Invalid JSON discovery packet: %s' % jsontext)
            return
        dtype = jsonobj['discovertype']
        if not self.json_eq(dtype, jsontext):
            CMAdb.log.debug("Saved discovery type %s for endpoint %s."
            %       (dtype, self.designation))
            self[dtype] = jsontext # This is stored in separate nodes for performance
        else:
            if not self.monitors_activated and dtype == 'tcpdiscovery':
                # This is because we need to start the monitors anyway...
                if CMAdb.debug:
                    CMAdb.log.debug('Discovery type %s for endpoint %s is unchanged'
                    '. PROCESSING ANYWAY.'
                    %       (dtype, self.designation))
            else:
                if CMAdb.debug:
                    CMAdb.log.debug('Discovery type %s for endpoint %s is unchanged. ignoring'
                    %       (dtype, self.designation))
                return
        self._process_json(origaddr, jsonobj)


    def __iter__(self):
        'Iterate over our child JSON attribute names'
        for tup in CMAdb.store.load_cypher_query(self.JSONattrnames, None,
                                     params={'droneid': Store.id(self)}):
            yield tup.key

    def keys(self):
        'Return the names of all our JSON discovery attributes.'
        return [attr for attr in self]

    def __contains__(self, key):
        'Return True if our object contains the given key (JSON name).'
        return hasattr(self, self.HASH_PREFIX + key)

    def __len__(self):
        'Return the number of JSON items in this Drone.'
        return len(self.keys())

    def jsonval(self, jsontype):
        'Construct a python object associated with a particular JSON discovery value.'
        if not hasattr(self, self.HASH_PREFIX + jsontype):
            return None
        return CMAdb.store.load_cypher_node(self.JSONsingleattr, JSONMapNode,
                                            params={'droneid': Store.id(self),
                                            'jsonname': jsontype}
                                            ).map()
    def get(self, key, alternative=None):
        '''Return JSON object if the given key exists - 'alternative' if not.'''
        ret = self.jsonval(key)
        return ret if ret is not None else alternative

    def __getitem__(self, key):
        'Return the given JSON value or raise IndexError.'
        ret = self.jsonval(key)
        if ret is None:
            raise IndexError('No such JSON attribute [%s].' % key)
        return ret

    def deepget(self, key, alternative=None):
        '''Return value if object contains the given *structured* key - 'alternative' if not.'''
        keyparts = key.split('.', 1)
        if len(keyparts) == 1:
            return self.get(key, alternative)
        jsonmap = self.jsonval(keyparts[0])
        if jsonmap is None:
            return alternative
        return jsonmap.deepget(keyparts[1], alternative)

    def __setitem__(self, name, value):
        'Set the given JSON value to the given object/string.'
        if name in self:
            if self.json_eq(name, value):
                return
            else:
                # FIXME: ADD ATTRIBUTE HISTORY (enhancement)
                # This will likely involve *not* doing a 'del' here
                del self[name]
        jsonnode = CMAdb.store.load_or_create(JSONMapNode, json=value)
        setattr(self, self.HASH_PREFIX + name, jsonnode.jhash)
        CMAdb.store.relate(self, CMAconsts.REL_jsonattr, jsonnode,
                           properties={'jsonname':  name,
                                       'time':   long(round(time.time()))
                                       })

    def __delitem__(self, name):
        'Delete the given JSON value from the Drone.'
        try:
            delattr(self, self.HASH_PREFIX + name)
        except AttributeError:
            raise IndexError('No such JSON attribute [%s].' % name)
        jsonnode=self[name]
        should_delnode = True
        # See if it has any remaining references...
        for node in CMAdb.store.load_in_related(jsonnode,
                                                CMAconsts.REL_jsonattr,
                                                nodeconstructor):
            if node is not self:
                should_delnode = False
                break
        CMAdb.store.separate(self, CMAconsts.REL_jsonattr, jsonnode)
        if should_delnode:
            # Avoid dangling properties...
            CMAdb.store.delete(jsonnode)

    def json_eq(self, key, newvalue):
        '''Return True if this new value is equal to the current value for
        the given key (JSON attribute name).

        We do this by comparing hash values. This keeps us from having to
        fetch potentially very large strings (read VERY SLOW) if we can
        compare hash values instead.

        Our hash values are representable in fewer than 60 bytes to maximize Neo4j performance.
        '''
        if key not in self:
            return False
        hashname = self.HASH_PREFIX + key
        newhash = JSONMapNode.strhash(newvalue)
        return getattr(self, hashname) == newhash


    def _process_json(self, origaddr, jsonobj):
        'Pass the JSON data along to interested discovery plugins (if any)'
        dtype = jsonobj['discovertype']
        foundone = False
        if CMAdb.debug:
            CMAdb.log.debug('Processing JSON for discovery type [%s]' % dtype)
        for prio in range(0, len(Drone._JSONprocessors)):
            if dtype in Drone._JSONprocessors[prio]:
                foundone = True
                classes = Drone._JSONprocessors[prio][dtype]
                #print >> sys.stderr, 'PROC[%s][%s] = %s' % (prio, dtype, str(classes))
                for cls in classes:
                    proc = cls(CMAdb.io.config, CMAdb.transaction, CMAdb.store
                    ,   CMAdb.log, CMAdb.debug)
                    proc.processpkt(self, origaddr, jsonobj)
        if foundone:
            CMAdb.log.info('Processed %s JSON data from %s into graph.'
            %   (dtype, self.designation))
        else:
            CMAdb.log.info('Stored %s JSON data from %s without processing.'
            %   (dtype, self.designation))


    def destaddr(self, ring=None):
        '''Return the "primary" IP for this host as a pyNetAddr with port'''
        return pyNetAddr(self.select_ip(ring=ring), port=self.port)

    def select_ip(self, ring=None):
        '''Select an appropriate IP address for talking to a partner on this ring
        or our primary IP if ring is None'''
        # Current code is not really good enough for the long term,
        # but is good enough for now...
        # In particular, when talking on a particular switch ring, or
        # subnet ring, we want to choose an IP that's on that subnet,
        # and preferably on that particular switch for a switch-level ring.
        # For TheOneRing, we want their primary IP address.
        ring = ring
        return self.primary_ip_addr


    #Current implementation does not use 'self'
    #pylint: disable=R0201
    def send_hbmsg(self, dest, fstype, addrlist):
        '''Send a message with an attached pyNetAddr list - each including port numbers'
           This is intended primarily for start or stop heartbeating messages.'''

        # Now we create a collection of frames that looks like this:
        #
        #   One FrameTypes.RSCJSON frame containing JSON Heartbeat parameters
        #   one frame per dest, type FrameTypes.IPPORT
        #
        params = ConfigFile.agent_params(CMAdb.io.config
        ,       'heartbeats', None, self.designation)
        framelist = [{'frametype': FrameTypes.RSCJSON, 'framevalue': str(params)},]
        for addr in addrlist:
            if addr is None:
                continue
            framelist.append({'frametype': FrameTypes.IPPORT, 'framevalue': addr})

        CMAdb.transaction.add_packet(dest, fstype, framelist)

    def death_report(self, status, reason, fromaddr, frameset):
        'Process a death/shutdown report for us.  RIP us.'
        from hbring import HbRing
        frameset = frameset # We don't use the frameset at this point in time
        if reason != 'HBSHUTDOWN':
            if self.status != status or self.reason != reason:
                CMAdb.log.info('Node %s has been reported as %s by address %s. Reason: %s'
                %   (self.designation, status, str(fromaddr), reason))
        oldstatus = self.status
        self.status = status
        self.reason = reason
        self.monitors_activated = False
        self.time_status_ms = int(round(time.time() * 1000))
        self.time_status_iso8601 = time.strftime('%Y-%m-%d %H:%M:%S')
        if status == oldstatus:
            # He was already dead, Jim.
            return
        # There is a need for us to be a little more sophisticated
        # in terms of the number of peers this particular drone had
        # It's here in this place that we will eventually add the ability
        # to distinguish death of a switch or subnet or site from death of a single drone
        for mightbering in CMAdb.store.load_in_related(self, None, nodeconstructor):
            if isinstance(mightbering, HbRing):
                mightbering.leave(self)
        deadip = pyNetAddr(self.select_ip(), port=self.port)
        if CMAdb.debug:
            CMAdb.log.debug('Closing connection to %s/%d' % (deadip, DEFAULT_FSP_QID))
        #
        # So, if this is a death report from another system we could shut down ungracefully
        # and it would be OK.
        #
        # But if it's a graceful shutdown, we need to not screw up the comm shutdown in progress
        # If it's broken, our tests and the real world will eventually show that up :-D.
        #
        if reason != 'HBSHUTDOWN':
            self._io.closeconn(DEFAULT_FSP_QID, deadip)
        AssimEvent(self, AssimEvent.OBJDOWN)

    def start_heartbeat(self, ring, partner1, partner2=None):
        '''Start heartbeating to the given partners.
        We insert ourselves between partner1 and partner2.
        We only use forward links - because we can follow them in both directions in Neo4J.
        So, we need to create a forward link from partner1 to us and from us to partner2 (if any)
        '''
        ouraddr = pyNetAddr(self.select_ip(), port=self.port)
        partner1addr = pyNetAddr(partner1.select_ip(ring), port=partner1.port)
        if partner2 is not None:
            partner2addr = pyNetAddr(partner2.select_ip(ring), port=partner2.port)
        else:
            partner2addr = None
        if CMAdb.debug:
            CMAdb.log.debug('STARTING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]' %
                (self, ouraddr, partner1, partner1addr, partner2, partner2addr))
        self.send_hbmsg(ouraddr, FrameSetTypes.SENDEXPECTHB, (partner1addr, partner2addr))

    def stop_heartbeat(self, ring, partner1, partner2=None):
        '''Stop heartbeating to the given partners.'
        We don't know which node is our forward link and which our back link,
        but we need to remove them either way ;-).
        '''
        ouraddr = pyNetAddr(self.select_ip(), port=self.port)
        partner1addr = pyNetAddr(partner1.select_ip(ring), port=partner1.port)
        if partner2 is not None:
            partner2addr = pyNetAddr(partner2.select_ip(ring), port=partner2.port)
        else:
            partner2addr = None
        # Stop sending the heartbeat messages between these (former) peers
        if CMAdb.debug:
            CMAdb.log.debug('STOPPING heartbeat(s) from %s [%s] to %s [%s] and %s [%s]' %
                (self, ouraddr, partner1, partner1addr, partner2, partner2addr))
        self.send_hbmsg(ouraddr, FrameSetTypes.STOPSENDEXPECTHB, (partner1addr, partner2addr))

    def request_discovery(self, args): ##< A vector of arguments containing
        '''Send our drone a request to perform discovery
        We send a           DISCNAME frame with the instance name
        then an optional    DISCINTERVAL frame with the repeat interval
        then a              DISCJSON frame with the JSON data for the discovery operation.

        Our argument is a vector of pyConfigContext objects with values for
            'instance'  Name of this discovery instance
            'interval'  How often to repeat this discovery action
            'timeout'   How long to wait before considering this discovery failed...
        '''
        #fs = pyFrameSet(FrameSetTypes.DODISCOVER)
        frames = []
        for arg in args:
            instance = arg['instance']
            frames.append({'frametype': FrameTypes.DISCNAME, 'framevalue': instance})
            if 'repeat' in arg:
                interval = int(arg['repeat'])
            else:
                interval = None
            if interval is not None:
                frames.append({'frametype': FrameTypes.DISCINTERVAL, 'framevalue': int(interval)})
            frames.append({'frametype': FrameTypes.DISCJSON, 'framevalue': str(arg)})
        # This doesn't work if the client has bound to a VIP
        ourip = self.select_ip()    # meaning select our primary IP
        ourip = pyNetAddr(ourip)
        if ourip.port() == 0:
            ourip.setport(self.port)
        #print >> sys.stderr, ('ADDING PACKET TO TRANSACTION: %s', str(frames))
        if CMAdb.debug:
            CMAdb.log.debug('Sending Discovery request(%s, %s) to %s Frames: %s'
            %	(instance, str(interval), str(ourip), str(frames)))
        CMAdb.transaction.add_packet(ourip,  FrameSetTypes.DODISCOVER, frames)
        #print >> sys.stderr, ('Sent Discovery request(%s, %s) to %s Frames: %s'
        #%	(instance, str(interval), str(ourip), str(frames)))

    def set_crypto_identity(self, keyid=None):
        'Associate our IP addresses with our key id'
        if CMAdb.store.readonly or not CMAdb.use_network:
            return
        if keyid is not None and keyid != '':
            if self.key_id != '' and keyid != self.key_id:
                raise ValueError('Cannot change key ids for % from %s to %s.'
                %   (str(self), self.key_id, keyid))
            self.key_id = keyid
        # Encryption is required elsewhere - we ignore this here...
        if self.key_id != '':
            pyCryptFrame.dest_set_key_id(self.destaddr(), self.key_id)
            pyCryptFrame.associate_identity(self.crypto_identity(), self.key_id)

    def __str__(self):
        'Give out our designation'
        return 'Drone(%s)' % self.designation

    @staticmethod
    def find(designation, port=None, domain=None):
        'Find a drone with the given designation or IP address, or Neo4J node.'
        desigstr = str(designation)
        if isinstance(designation, Drone):
            designation.set_crypto_identity()
            return designation
        elif isinstance(designation, str):
            if domain is None:
                domain = CMAconsts.globaldomain
            designation = designation.lower()
            drone = CMAdb.store.load_or_create(Drone, port=port, domain=domain
            ,       designation=designation)
            assert drone.designation == designation
            assert CMAdb.store.has_node(drone)
            drone.set_crypto_identity()
            return drone
        elif isinstance(designation, pyNetAddr):
            desig = designation.toIPv6()
            desig.setport(0)
            desigstr = str(desig)
            if domain is None:
                dstr = '*'
            else:
                dstr = domain
            query = '%s:%s' % (str(Store.lucene_escape(desigstr)), dstr)
            #We now do everything by IPv6 addresses...
            drone = CMAdb.store.load_cypher_node(Drone.IPownerquery_1, Drone, {'ipaddr':query})
            if drone is not None:
                assert CMAdb.store.has_node(drone)
                drone.set_crypto_identity()
                return drone
            if CMAdb.debug:
                CMAdb.log.warn('Could not find IP NetAddr address in Drone.find... %s [%s] [%s]'
                %   (designation, desigstr, type(designation)))

        if CMAdb.debug:
            CMAdb.log.debug("DESIGNATION2 (%s) = %s" % (designation, desigstr))
            CMAdb.log.debug("QUERY (%s) = %s" % (designation, query))
            print >> sys.stderr, ("DESIGNATION2 (%s) = %s" % (designation, desigstr))
            print >> sys.stderr, ("QUERY (%s) = %s" % (designation, query))
        if CMAdb.debug:
            raise RuntimeError('drone.find(%s) (%s) (%s) => returning None' % (
                str(designation), desigstr, type(designation)))
                #str(designation), desigstr, type(designation)))
            #tblist = traceback.extract_stack()
            ##tblist = traceback.extract_tb(trace, 20)
            #CMAdb.log.info('======== Begin missing IP Traceback ========')
            #for tbelem in tblist:
                #(filename, line, funcname, text) = tbelem
                #filename = os.path.basename(filename)
                #CMAdb.log.info('%s.%s:%s: %s'% (filename, line, funcname, text))
            #CMAdb.log.info('======== End missing IP Traceback ========')
            #CMAdb.log.warn('drone.find(%s) (%s) (%s) => returning None' % (
        return None

    @staticmethod
    def add(designation, reason, status='up', port=None, domain=CMAconsts.globaldomain
    ,       primary_ip_addr=None):
        'Add a drone to our set unless it is already there.'
        drone = CMAdb.store.load_or_create(Drone, domain=domain, designation=designation
        ,   primary_ip_addr=primary_ip_addr, port=port, status=status, reason=reason)
        assert CMAdb.store.has_node(drone)
        drone.reason = reason
        drone.status = status
        drone.statustime = int(round(time.time() * 1000))
        drone.iso8601 = time.strftime('%Y-%m-%d %H:%M:%S')
        if port is not None:
            drone.port = port
        return drone

    @staticmethod
    def add_json_processor(clstoadd):
        "Register (add) all the json processors we've been given as arguments"

        if Drone._JSONprocessors is None:
            Drone._JSONprocessors = []
            for prio in range(0, clstoadd.PRI_LIMIT):
                prio = prio # Make pylint happy
                Drone._JSONprocessors.append({})

        priority = clstoadd.priority()
        msgtypes = clstoadd.desiredpackets()

        for msgtype in msgtypes:
            if msgtype not in Drone._JSONprocessors[priority]:
                Drone._JSONprocessors[priority][msgtype] = []
            if clstoadd not in Drone._JSONprocessors[priority][msgtype]:
                Drone._JSONprocessors[priority][msgtype].append(clstoadd)

        return clstoadd
