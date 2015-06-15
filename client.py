#!/usr/bin/python

__author__ = 'bokuto'

from subprocess import PIPE, TimeoutExpired, Popen
from os import chmod
from functools import partial
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor

import argparse
import platform
import operator
import stat
import sys
# import psutil



class MulticastDevopsClientProtocol(DatagramProtocol):
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


class MulticastDevopsServerProtocol(DatagramProtocol):
    def __init__(self):
        self.state = 'WAIT'
        self.filename = 'default_loaded_filename'
        self.filedict = dict()
        self.last_file_size = 0
        self.multicast_addr = ("224.0.1.224", 8005)
        pass

    def startProtocol(self):
        """
        Called after protocol has started listening.
        """
        # Set the TTL>1 so multicast will cross router hops:
        self.transport.setTTL(5)
        # Join a specific multicast group:
        self.transport.joinGroup(self.multicast_addr[0])
        pass

    def datagramReceived(self, datagram, address):
        print("Datagram %s received from %s" % (repr(datagram), repr(address)))
        # Parse the command
        preambula = datagram[0:8]
        command = datagram[8:16]
        data = datagram[16:]

        if preambula != b'00110011':
            print("Ignored")
            return

        if self.state == 'WAIT' and command == b'filename':
            self.filename = data.decode()
            return

        if self.state == 'WAIT' and command == b'register':
            preambula = b"11001100"
            command = b"answer__"
            info = "Platform: %s \n Arch: %s \n Machine: %s" % (platform.platform(),
                                                                platform.architecture(),
                                                                platform.machine())
            info = preambula + command + info.encode()
            self.transport.write(info, self.multicast_addr)
            return


        if self.state == 'WAIT' and command == b'loadload':
            self.state = 'LOAD'
            num = int.from_bytes(data[0:2], byteorder='big')
            data = data[2:]
            self.last_file_size = len(data)
            self.filedict[num] = data
            return

        if self.state == 'LOAD' and command == b'loadload':
            num = int.from_bytes(data[0:2], byteorder='big')
            data = data[2:]
            self.filedict[num] = data
            self.last_file_size += len(data)
            return

        if self.state == 'LOAD' and command == b'endoload':
            with open(self.filename, 'wb') as f:
                file_binary_list = sorted(self.filedict.items(), key=operator.itemgetter(0))
                for number, chunk in file_binary_list:
                    f.write(chunk)
            self.state = 'WAIT'
            print("File %s loaded, size %d" % (self.filename, self.last_file_size))
            return

        if self.state == 'WAIT' and command == b'startbin':
            self.state = 'WORK'
            data = data.decode()
            args = data.split()
            chmod('./' + self.filename, stat.S_IRWXU)
            execstr = ['./' + self.filename] + args
            proc = Popen(execstr, stdout=PIPE, stderr=PIPE)
            try:
                outs, errs = proc.communicate(timeout=3)
            except TimeoutExpired:
                proc.kill()
                outs, errs = proc.communicate()
            print(outs, errs, proc.returncode)
            ret = bytearray(outs)
            ret += bytearray(errs)
            ret += int(proc.returncode).to_bytes(2, byteorder='big')

            self.transport.write(b'11001100return__' + ret, self.multicast_addr)
            self.state = 'WAIT'
            return


        return

def main():
    parser = argparse.ArgumentParser(description="Code or binary over LAN execution")
    parser.add_argument('--filename', dest='binfile', )
    reactor.listenMulticast(8005, MulticastDevopsClientProtocol(filename), listenMultiple=True)
    reactor.run()

if __name__ == "__main__":
    ret = main()
    sys.exit(ret)