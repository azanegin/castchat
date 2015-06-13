__author__ = 'bokuto'

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
import psutil
import platform


class MulticastPingPong(DatagramProtocol):
    def startProtocol(self):
        """
        Called after protocol has started listening.
        """
        # Set the TTL>1 so multicast will cross router hops:
        self.transport.setTTL(5)
        # Join a specific multicast group:
        self.transport.joinGroup("224.0.1.224")

    def datagramReceived(self, datagram, address):
        print("Datagram %s received from %s" % (repr(datagram), repr(address)))
        # Parse the command
        preambula   = datagram[0:8]
        command     = datagram[8:16]
        data        = datagram[16:]

        if preambula != b'00110011':
            print("Error: Command doesn't start from cmd sequence")
            return
        command = command.lower().decode()
        # Dispatch the command to the appropriate method.  Note that all you
        # need to do to implement a new command is add another do_* method.
        method = getattr(self, 'do_' + command)
        method(address, data)

    def do_test_binary(self, address, data):
        pass

    def do_register(self, address, data):
        preambula = "11001100"
        command = "answer"
        info = "Platform: %s \n Arch: %s \n Machine: %s" % (platform.platform(),
                                                            platform.architecture(),
                                                            platform.machine())
        info = preambula + ' ' + command + ' ' + info
        self.transport.write(info.encode(), ("224.0.1.224", 8005))

    def do_loadload(self, address, data):
        filename = 'loaded'
        file_content = data
        with open(filename, 'wb') as f:
            f.write(file_content)
        pass

# We use listenMultiple=True so that we can run MulticastServer.py and
# MulticastClient.py on same machine:
reactor.listenMulticast(8005, MulticastPingPong(),
                        listenMultiple=True)
reactor.run()