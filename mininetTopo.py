'''
Please add your name: David Chong Yong Ming
Please add your matric number: A0116633L
'''

import os
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

        # Gets the names and number of hosts, switches and links from topology.in (Task 1)
        filename = "topology.in"
        filereader = open(filename, "r")
        firstline = filereader.readline().split(' ')

        # Number of hosts, switches and links are stored in the first line of topology.in (Task 1)
        numofhosts = int(firstline[0])
        numofswitches = int(firstline[1])
        numoflinks = int(firstline[2])

        # You can write other functions as you need.

        # Add hosts to the mininet
        # > self.addHost('h%d' % [HOST NUMBER])
        hosts = []

        for i in xrange(numofhosts):
            host = self.addHost('H%d' % (i+1))
            hosts.append(host)

        # Print the added hosts for user to see (Task 1)
        print hosts

        # Add switches to the mininet
        # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
        # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)
        switches = []

        for j in xrange(numofswitches):
            sconfig = {'dpid': "%016x" % (j+1)}
            switch = self.addSwitch('S%d' % (j+1), **sconfig)
            switches.append(switch)

        # Print the added switches for user to see (Task 1)
        print switches
        print self.switches()

        # Add links to the mininet
        # > self.addLink([HOST1], [HOST2])
        self.linkconfigs = []

        for k in xrange(numoflinks):
            link = filereader.readline().strip().split(',')
            self.linkconfigs.append(link)
            firstnode = link[0]
            secondnode = link[1]
            # Links are added without bandwidth as bandwidth is added in the queue
            self.addLink(firstnode, secondnode)
            print link

        # Print the added links for user to see (Task 1)
        print self.links(True, False, True)

def startNetwork():
    info('** Creating the tree network\n')
    topo = TreeTopo()

    # Changed server IP to 127.0.0.1 for the host-only adaptor (Implementation)
    global net
    net = Mininet(topo=topo, link = Link,
                  controller=lambda name: RemoteController(name, ip='127.0.0.1'),
                  listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    # Used to calculate the link speed between nodes in bits per second (Task 1)
    def getLinkSpeed(firstnode, secondnode):
        for i in topo.linkconfigs:
            if firstnode == i[0] and secondnode == i[1]:
                return int(i[2]) * 1000000

        return 0

    # Local variable used to increment for number of links and switches added
    networkints = 0

    # Create QoS Queues
    # > os.system('sudo ovs-vsctl -- set Port [INTERFACE] qos=@newqos \
    #            -- --id=@newqos create QoS type=linux-htb other-config:max-rate=[LINK SPEED] queues=0=@q0,1=@q1,2=@q2 \
    #            -- --id=@q0 create queue other-config:max-rate=[LINK SPEED] other-config:min-rate=[LINK SPEED] \
    #            -- --id=@q1 create queue other-config:min-rate=[X] \
    #            -- --id=@q2 create queue other-config:max-rate=[Y]')
    for j in topo.links(True, False, True):
        for k in topo.switches():
            linkinfo = j[2]
            for l in [1, 2]:
                if linkinfo["node%i" % (l)] == k:
                    port = linkinfo["port%i" % (l)]
                    interface = "%s-eth%s" % (k, port)
                    firstnode = linkinfo["node1"]
                    secondnode = linkinfo["node2"]
                    linkspeed = getLinkSpeed(firstnode, secondnode)
                    xspeed = linkspeed * 8/10 # bandwith * 0.8 for normal queues (Task 3)
                    yspeed = linkspeed * 5/10 # bandwidth * 0.5 for Premium Service Class (Task 4)

                    # OS System Call
                    os.system("sudo ovs-vsctl -- set Port %s qos=@newqos \
                            -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%i queues=0=@q0,1=@q1,2=@q2 \
                            -- --id=@q0 create queue other-config:max-rate=%i other-config:min-rate=%i \
                            -- --id=@q1 create queue other-config:min-rate=%i \
                            -- --id=@q2 create queue other-config:max-rate=%i" % (interface, linkspeed, linkspeed, linkspeed, xspeed, yspeed))

                    # When a interface is added, the value will increment
                    networkints += 1

    # Print out the number of interfaces that has been created (Task 1)
    print "QoS has been set up on %i interfaces" % (networkints)

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
