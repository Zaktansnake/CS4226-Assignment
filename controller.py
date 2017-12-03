'''
Please add your name: David Chong Yong Ming
Please add your matric number: A0116633L
'''

import sys
import os
from sets import Set

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_tree

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.macmap = {}
        # For Premium Service Class
        self.psc = {}
        return
        
    # You can write other functions as you need.
    def _handle_PacketIn (self, event):    
        # install entries to the route table
        packet = event.parsed
        dpid = event.dpid
        port = event.port
        source = packet.src
        destination = packet.dst

        def install_enqueue(event, packet, outport, q_id):
            log.info("Installing flow for %s:%i -> %s:%i", source, port, destination, outport)
            message = of.ofp_flow_mod()
            message.match = of.ofp_match.from_packet(packet, port)
            message.actions.append(of.ofp_action_enqueue(port = outport, queue_id = q_id))
            message.data = event.ofp
            message.priority = 1000
            event.connection.send(message)
            log.info("Packet with queue ID %i sent via port %i\n", q_id, outport)
            return

        # Check the packet and decide how to route the packet
        def forward(message = None):
            log.info("Receiving packet %s from port %i", packet, port)

            # Store the port from where the packet comes from
            if self.macmap[dpid].get(source) == None:
                self.macmap[dpid][source] = port

            # Get source and destination IP address
            sourceip = None
            destinationip = None

            if packet.type == packet.IP_TYPE:
                log.info("Packet is IP type %s", packet.type)
                ippacket = packet.payload
                sourceip = ippacket.srcip
                destinationip = ippacket.dstip
            elif packet.type == packet.ARP_TYPE:
                log.info("Packet is ARP type %s", packet.type)
                arppacket = packet.payload
                sourceip = arppacket.protosrc
                destinationip = arppacket.protodst
            else:
                log.info("Packet is Unknown type %s", packet.type)
                sourceip = None
                destinationip = None

            # Check if source and destination ip is in same premium service class
            qid = 0

            if sourceip == None or destinationip == None:
                qid = 0
            elif isSameClass(sourceip, destinationip):
                qid = 1
            else:
                qid = 2

            # If multicast, flood
            if destination.is_multicast:
                flood("Multicast to Port %s -- flooding" % (destination))
                return

            # If destination port is not found, flood
            if destination not in self.macmap[dpid]:
                flood("Destination Port %s unknown -- flooding" % (destination))
                return

            outport = self.macmap[dpid][destination]
            install_enqueue(event, packet, outport, qid)
            return

        # Check if IPs belong to same premium service class
        def isSameClass(sourceip, destinationip):
            for i in self.psc[dpid]:
                if sourceip in i and destination in i:
                    log.info("Source IP %s and Destination IP %s are in the same Premium Service Class", sourceip, destinationip)
                    return True
            log.info("Source IP %s and Destination IP %s are not in the same Premium Service Class", sourceip, destinationip)
            return False

        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            log.info(message)
            floodmsg = of.ofp_packet_out()
            floodmsg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            floodmsg.data = event.ofp
            floodmsg.in_port = port
            event.connection.send(floodmsg)
            log.info("Flood Message sent via port %i\n", of.OFPP_FLOOD)
            return

        forward()
        return


    def _handle_ConnectionUp(self, event):
        dpid = event.dpid
        log.debug("Switch %s has come up.", dpid)

        self.macmap[dpid] = {}
        self.psc[dpid] = []

        filename = "policy.in"
        filereader = open(filename, "r")
        firstline = filereader.readline().split(' ')

        numofpolicies = int(firstline[0])
        numofpsc = int(firstline[1])
        fpolicies = []

        for i in xrange(numofpolicies):
            line = filereader.readline().strip().split(',')
            source = line[0]
            destination = line[1]
            port = line[2]
            fpolicies.append((source, destination, port))

        for j in xrange(numofpsc):
            line = filereader.readline().strip().split(',')
            self.psc[dpid].append(line)

        log.info("Premium Service Class List: %s", self.psc[dpid])

        # Send the firewall policies to the switch
        def sendFirewallPolicy(connection, policy):

            # From first host to second host
            source = policy[0]
            destination = policy[1]
            port = policy[2]

            messageone = of.ofp_flow_mod()
            messageone.priority = 2000
            messageone.actions.append(of.ofp_action_output(port = of.OFPP_NONE))
            messageone.match.dl_type = 0x800
            messageone.match.nw_proto = 6
            messageone.match.nw_src = IPAddr(source)
            messageone.match.nw_dst = IPAddr(destination)
            messageone.match.tp_dst = int(port)
            connection.send(messageone)
            log.info("Firewall Policy: source = %s, destination = %s, port = %s", source, destination, port)

            # From second host to first host
            source = policy[1]
            destination = policy[0]
            port = policy[2]

            messagetwo = of.ofp_flow_mod()
            messagetwo.priority = 2000
            messagetwo.actions.append(of.ofp_action_output(port = of.OFPP_NONE))
            messagetwo.match.dl_type = 0x800
            messagetwo.match.nw_proto = 6
            messagetwo.match.nw_src = IPAddr(source)
            messagetwo.match.nw_dst = IPAddr(destination)
            messagetwo.match.tp_dst = int(port)
            connection.send(messagetwo)
            log.info("Firewall Policy: source = %s, destination = %s, port = %s", source, destination, port)
            return

        for i in fpolicies:
            sendFirewallPolicy(event.connection, i)

        for j in self.psc:
            pass

        return
            

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    # Starting the controller module
    core.registerNew(Controller)
