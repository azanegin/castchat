#!/usr/bin/python

__author__ = 'bokuto'

from subprocess import PIPE, TimeoutExpired, Popen
from os import chmod
from functools import partial
import argparse
import platform
import operator
import stat
import sys
import tarfile

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor, defer


def sleep(secs):
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, None)
    return d


class MulticastDevopsClientProtocol(DatagramProtocol):
    def __init__(self, port_number, args_list):
        self.args_list = args_list
        self.machines = dict()
        self.multicast_address = ("224.0.1.224", port_number)

    def startProtocol(self):
        self.transport.joinGroup(self.multicast_address[0])
        self.transport.write(b'00110011' + 'register'.encode(), self.multicast_address)
        if self.args_list.localfile is not None:
            self.transport.write(b'00110011filename' + self.args_list.localfile.encode(), self.multicast_address)
            with open(self.args_list.localfile, 'br') as f:
                i = 0
                for chunk in iter(partial(f.read, 4 * 1024), b''):
                    sendstr = b'00110011' + b'loadload' + i.to_bytes(2, byteorder='big') + chunk
                    self.transport.write(sendstr, self.multicast_address)
                    i += 1
            self.transport.write(b'00110011endoload', self.multicast_address)
            pass

        if self.args_list.archive is False:
            for x in range(self.args_list.tries):
                self.transport.write(b'00110011startbin' + self.args_list.execstr.encode(), self.multicast_address)
                sleep(3)
        else:
            self.transport.write(b'00110011makearch', self.multicast_address)
        return

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
    def __init__(self, portnum, _whitelist):
        self.state = 'WAIT'
        self.filename = "defaultfile"
        self.file_dict = dict()
        self.last_file_size = 0
        self.whitelist = None
        if _whitelist is not None:
            with open(_whitelist, 'r') as wlfile:
                self.whitelist = [line.rstrip('\n') for line in wlfile]
        self.multicast_address = ("224.0.1.224", portnum)
        return

    def startProtocol(self):
        """
        Called after protocol has started listening.
        """
        # Set the TTL>1 so multicast will cross router hops:
        self.transport.setTTL(5)
        # Join a specific multicast group:
        self.transport.joinGroup(self.multicast_address[0])
        return

    def datagramReceived(self, datagram, address):
        print("Datagram %s received from %s" % (repr(datagram), repr(address)))
        # Parse the command
        preambula = datagram[0:8]
        command = datagram[8:16]
        data = datagram[16:]

        print(self.whitelist)
        print(address[0])
        print(address[0] not in self.whitelist)
        if self.whitelist is not None and address[0] not in self.whitelist:
            print("IP Address not in whitelist, ignored")
            return

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
            self.transport.write(info, self.multicast_address)
            return


        if self.state == 'WAIT' and command == b'loadload':
            self.state = 'LOAD'
            num = int.from_bytes(data[0:2], byteorder='big')
            data = data[2:]
            self.last_file_size = len(data)
            self.file_dict[num] = data
            return

        if self.state == 'LOAD' and command == b'loadload':
            num = int.from_bytes(data[0:2], byteorder='big')
            data = data[2:]
            self.file_dict[num] = data
            self.last_file_size += len(data)
            return

        if self.state == 'LOAD' and command == b'endoload':
            with open(self.filename, 'wb') as f:
                file_binary_list = sorted(self.file_dict.items(), key=operator.itemgetter(0))
                for number, chunk in file_binary_list:
                    f.write(chunk)
            self.state = 'WAIT'
            print("File %s loaded, size %d" % (self.filename, self.last_file_size))
            return

        if self.state == 'WAIT' and command == b'startbin':
            self.state = 'WORK'
            data = data.decode()
            args = data.split()
            print(self.filename)
            chmod('./' + self.filename, stat.S_IXUSR | stat.S_IRUSR)
            execstr = ['./' + self.filename] + args
            print(execstr)
            proc = Popen(execstr, stdout=PIPE, stderr=PIPE)
            try:
                outs, errs = proc.communicate(timeout=3)
            except TimeoutExpired:
                proc.kill()
                outs, errs = proc.communicate()
            print(outs, errs, proc.returncode)
            ret = bytes(outs)
            ret += bytes(errs)
            ret += int(proc.returncode).to_bytes(2, byteorder='big')

            self.transport.write(b'11001100return__' + ret, self.multicast_address)
            self.state = 'WAIT'
            return

        if self.state == 'WAIT' and command == b'makearch':
            self.state = 'WORK'

            tfile = tarfile.open(self.filename)
            extractPath = self.filename.split("/")[-1].split(".")[0] + "/"
            tfile.extractall(path=extractPath)

            execstr = ["make", "-f", "./" + extractPath + "Makefile"]
            proc = Popen(execstr, stdout=PIPE, stderr=PIPE)

            try:
                proc.wait(timeout=3)
            except TimeoutExpired:
                proc.kill()
            print(proc.returncode)
            # ret = bytes(outs)
            # ret += bytes(errs)
            ret = int(proc.returncode).to_bytes(2, byteorder='big')
            return

        return

def main():
    init_parser = argparse.ArgumentParser(description="Code or binary over LAN execution", add_help=False)
    init_parser.add_argument('--port', action="store", type=int, default=8005, help="Network port to use, default 8005")
    group_client_server = init_parser.add_mutually_exclusive_group(required=True)
    group_client_server.add_argument('--client', action="store_false", help="Start client with some query")
    group_client_server.add_argument('--server', action="store_true", help="Start as server, waiting for connections")
    init_parser.add_argument('--version', action='version', version='%(prog)s 0.1')
    init_args, other_args = init_parser.parse_known_args()
    if init_args.server is False:
        parser = argparse.ArgumentParser(parents=[init_parser])
        parser.add_argument('--localfile', action="store", type=str, help="Local file to load on servers")
        parser.add_argument('--tries', action="store", type=int, default=1, help="How many times to exec")
        group_arch_bin_script = parser.add_mutually_exclusive_group()
        group_arch_bin_script.add_argument('--archive', action="store_true", help="If localfile is archive")
        group_arch_bin_script.add_argument('--executable', action="store_false",
                                           help="If localfile is binary or script")
        parser.add_argument('--execstr', action="store", type=str, required=True,
                            help="Your regular shell exec: filename and args, to be launched on remote machine")
        args, other_args = parser.parse_known_args()
    elif init_args.server is True:
        parser = argparse.ArgumentParser(parents=[init_parser])
        parser.add_argument('--whitelist', action="store", type=str, help="File with allowed IP's, in A.B.C.D format")
        args, other_args = parser.parse_known_args()

    if init_args.server:
        reactor.listenMulticast(init_args.port, MulticastDevopsServerProtocol(init_args.port, args.whitelist),
                                listenMultiple=True)
    else:
        reactor.listenMulticast(init_args.port, MulticastDevopsClientProtocol(init_args.port, args),
                                listenMultiple=True)
    return reactor.run()


if __name__ == "__main__":
    ret = main()
    sys.exit(ret)
