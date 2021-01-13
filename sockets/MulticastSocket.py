import os
import struct

from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, IPPROTO_IP, IP_MULTICAST_TTL, inet_aton, INADDR_ANY, IP_ADD_MEMBERSHIP


class MulticastSocket(socket):
    # TODO: can have own id?
    def __init__(self, address, port):
        super().__init__(AF_INET, SOCK_DGRAM)
        self.address = address
        self.port = port
        ttl = struct.pack('b', 12)
        self.setsockopt(IPPROTO_IP, IP_MULTICAST_TTL, ttl)
        self.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if os.name != 'nt':
            from socket import SO_REUSEPORT
            self.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        group = inet_aton(address)
        mreq = struct.pack('4sL', group, INADDR_ANY)
        self.setsockopt(IPPROTO_IP, IP_ADD_MEMBERSHIP, mreq)
        self.bind(('', port))

    def __del__(self):
        self.close()
