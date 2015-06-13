__author__ = 'bokuto'

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
import sys
#import argparse

class MulticastPingClient(DatagramProtocol):
    def __init__(self, _filename):
        self.filename = _filename

    def startProtocol(self):
        # Join the multicast address, so we can receive replies:
        self.transport.joinGroup("224.0.1.224")
        # Send to 228.0.0.5:8005 - all listeners on the multicast address
        # (including us) will receive this message.
        self.machines = dict()
        self.transport.write(b'00110011' + 'register'.encode(), ("224.0.1.224", 8005))
        with open("README.md", 'br') as f:
            read_data = f.read()
        sendstr = b'00110011' + 'loadload'.encode()
        sendstr += read_data
        self.transport.write(sendstr, ("224.0.1.224", 8005))

    def datagramReceived(self, datagram, address):
        print("Datagram %s received from %s" % (repr(datagram), repr(address)))
        # Parse the command
        commandParts = datagram.decode().split()
        if (commandParts[0] != "11001100"):
            print("Error: Command doesn't start from cmd sequence")
            return

        command = commandParts[1].lower()
        args = commandParts[2:]
        if (command == "answer"):
            self.machines[address] = args
        elif (command == "return"):
            print(repr(self.machines[address]) + ": " + args)


def main():
    #parser = argparse.ArgumentParser(description="Code or binary over LAN execution")
    #parser.add_argument('--filename', dest='binfile', )
    filename = "nb.tar.gz"
    reactor.listenMulticast(8005, MulticastPingClient(filename), listenMultiple=True)
    reactor.run()

if __name__ == "__main__":
    ret = main()
    sys.exit(ret)