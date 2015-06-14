__author__ = 'bokuto'
from functools import partial
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
import sys
# import argparse

class MulticastPingClient(DatagramProtocol):
    def __init__(self, _filename):
        self.filename = _filename
        self.machines = dict()
        self.multicast_addr = ("224.0.1.224", 8005)

    def startProtocol(self):
        self.transport.joinGroup(self.multicast_addr[0])
        self.transport.write(b'00110011' + 'register'.encode(), self.multicast_addr)


        with open(self.filename, 'br') as f:
            i = 0
            for chunk in iter(partial(f.read, 4 * 1024), b''):
                sendstr = b'00110011' + b'loadload' + i.to_bytes(2, byteorder='big') + chunk
                self.transport.write(sendstr, self.multicast_addr)
                i += 1
                pass

        sendstr = b'00110011' + b'endoload'
        self.transport.write(sendstr, self.multicast_addr)
        self.transport.write(b'00110011startbinkhoooy pesda/ya ebu sobak', self.multicast_addr)

    def datagramReceived(self, datagram, address):
        print("Datagram %s received from %s" % (repr(datagram), repr(address)))
        # Parse the command
        preambula = datagram[0:8]
        command = datagram[8:16]
        data = datagram[16:]
        if preambula != b'11001100':
            print("Ignored")
            return
        command = command.lower()
        if command == b"answer__":
            self.machines[address] = data
            print(str(address) + ": \n" + data.decode())
        if command == b'return__':
            print(data[:-2].decode())
            print(int().from_bytes(data[-2:], byteorder='big'))


def main():
    # parser = argparse.ArgumentParser(description="Code or binary over LAN execution")
    # parser.add_argument('--filename', dest='binfile', )
    filename = "test.py"
    reactor.listenMulticast(8005, MulticastPingClient(filename), listenMultiple=True)
    reactor.run()

if __name__ == "__main__":
    ret = main()
    sys.exit(ret)