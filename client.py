__author__ = 'bokuto'
from functools import partial
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
import sys
#import argparse

class MulticastPingClient(DatagramProtocol):
    def __init__(self, _filename):
        self.filename = _filename
        self.machines = dict()

    def startProtocol(self):
        self.transport.joinGroup("224.0.1.224")
        self.transport.write(b'00110011' + 'register'.encode(), ("224.0.1.224", 8005))


        with open(self.filename, 'br') as f:
            i = 0
            for chunk in iter(partial(f.read, 4 * 1024), b''):
                sendstr = b'00110011' + b'loadload' + i.to_bytes(2, byteorder='big') + chunk
                self.transport.write(sendstr, ("224.0.1.224", 8005))
                i += 1
                pass

        sendstr = b'00110011' + b'endoload'
        self.transport.write(sendstr, ("224.0.1.224", 8005))

    def datagramReceived(self, datagram, address):
        print("Datagram %s received from %s" % (repr(datagram), repr(address)))
        # Parse the command
        preambula   = datagram[0:8]
        command     = datagram[8:16]
        data        = datagram[16:]
        if preambula != b'11001100':
            print("Error: Command doesn't start from cmd sequence")
            return
        command = command.lower()
        if (command == b"answer__"):
            self.machines[address] = data
            print(str(address) + ": \n" + data.decode())


def main():
    #parser = argparse.ArgumentParser(description="Code or binary over LAN execution")
    #parser.add_argument('--filename', dest='binfile', )
    filename = "nb.tar.gz"
    reactor.listenMulticast(8005, MulticastPingClient(filename), listenMultiple=True)
    reactor.run()

if __name__ == "__main__":
    ret = main()
    sys.exit(ret)