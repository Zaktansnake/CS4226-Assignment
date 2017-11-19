'''
Please add your name: David Chong Yong Ming
Please add your matric number: A0116633L
'''

import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import Link
from mininet.node import RemoteController

net = None

class TreeTopo(Topo):

    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        filename = "topology.in"
        filereader = open(filename, "r")
        firstline = filereader.readline().split(' ')

        numofhosts = int(firstline[0])
        numofswitches = int(firstline[1])
        numoflinks = int(firstline[2])

        # Add Hosts
        hosts = []

        for i in xrange(numofhosts):
            host = self.addHost('H%d' % (i+1))
            hosts.append(host)

        print hosts

        # Add Switches
        switches = []

        for j in xrange(numofswitches):
            sconfig = {'dpid': "%016x" % (j+1)}
            switch = self.addSwitch('S%d' % (j+1), **sconfig)
            switches.append(switch)

        print switches
        print self.switches()

        # Add Links
        self.linkConfigs = []

        for k in xrange(numoflinks):
            link = filereader.readline().strip().split(',')
            print link
            self.linkConfigs.append(link)
            firstnode = link[0]
            secondnode = link[1]
            # Links are added without bandwidth as bandwidth is added in the queue
            self.addLink(firstnode, secondnode)

        print self.links(True, False, True)


    # You can write other functions as you need.

    # Add hosts
    # > self.addHost('h%d' % [HOST NUMBER])

    # Add switches
    # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
    # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)

    # Add links
    # > self.addLink([HOST1], [HOST2])

def startNetwork():
    info('** Creating the tree network\n')
    topo = TreeTopo()

    global net
    net = Mininet(topo=topo, link = Link,
                  controller=lambda name: RemoteController(name, ip='SERVER IP'),
                  listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    def getLinkSpeed(firstnode, secondnode):
        for i in topo.linkConfigs:
            if firstnode == i[0] and secondnode == i[1]:
                return int(i[2]) * 1000000

        return 0

    networkints = 0

    # Create QoS Queues
    # > os.system('sudo ovs-vsctl -- set Port [INTERFACE] qos=@newqos \
    #            -- --id=@newqos create QoS type=linux-htb other-config:max-rate=[LINK SPEED] queues=0=@q0,1=@q1,2=@q2 \
    #            -- --id=@q0 create queue other-config:max-rate=[LINK SPEED] other-config:min-rate=[LINK SPEED] \
    #            -- --id=@q1 create queue other-config:min-rate=[X] \
    #            -- --id=@q2 create queue other-config:max-rate=[Y]')

    # Get Switch interfaces
    for j in topo.links(True, False, True):
        for k in topo.switches():
            linkinfo = j[2]
            for l in [1, 2]:
                if linkinfo["node%i" % (l)] == k:
                    networkints += 1
                    port = linkinfo["port%i" % (l)]
                    firstnode = linkinfo["node1"]
                    secondnode = linkinfo["node2"]
                    linkspeed = getLinkSpeed(firstnode, secondnode)
                    xspeed = 100000000 # 100 mbps
                    yspeed = 50000000 # 50 mbps
                    interface = "%s-eth%s" % (k, port)

                    # OS System Call
                    os.system("sudo ovs-vsctl -- set Port %s qos=@newqos \
                            -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%i queues=0=@q0,1=@q1,2=@q2 \
                            -- --id=@q0 create queue other-config:max-rate=%i other-config:min-rate=%i \
                            -- --id=@q1 create queue other-config:min-rate=%i \
                            -- --id=@q2 create queue other-config:max-rate=%i" % (interface, linkspeed, linkspeed, linkspeed, xspeed, yspeed))

    print "QoS set up on %i interfaces" % (networkints)

    info('** Running CLI\n')
    CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()
        # Remove QoS and Queues
        os.system('sudo ovs-vsctl --all destroy Qos')
        os.system('sudo ovs-vsctl --all destroy Queue')


if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)

    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
