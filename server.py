__author__ = 'bokuto'

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from subprocess import PIPE, TimeoutExpired
import psutil
import platform
import operator


class MulticastPingPong(DatagramProtocol):
    def __init__(self):
        self.state = 'WAIT'
        self.filename = 'default_loaded_filename'
        self.filedict = dict()
        self.last_file_size = 0
        pass

    def startProtocol(self):
        """
        Called after protocol has started listening.
        """
        # Set the TTL>1 so multicast will cross router hops:
        self.transport.setTTL(5)
        # Join a specific multicast group:
        self.transport.joinGroup("224.0.1.224")
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
            self.transport.write(info, ("224.0.1.224", 8005))
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
            self.state == 'WORK'
            data = data.decode().split('/')
            args = data[0].split()
            ins = data[1].split()
            execstr = [self.filename].append(*args)
            proc = psutil.Popen(execstr, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            try:
                outs, errs = proc.communicate(input=ins, timeout=300)
            except TimeoutExpired:
                proc.kill()
                outs, errs = proc.communicate()
            ret = bytearray((outs, errs, proc.returncode))

            self.transport.write(b'11001100return__' + ret, ("224.0.1.224", 8005))
            return

        return

# We use listenMultiple=True so that we can run MulticastServer.py and
# MulticastClient.py on same machine:
reactor.listenMulticast(8005, MulticastPingPong(),
                        listenMultiple=True)
reactor.run()