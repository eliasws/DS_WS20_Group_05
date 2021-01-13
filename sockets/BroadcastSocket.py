import os
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, SO_REUSEADDR


class BroadcastSocket(socket):

    def __init__(self, address, port):
        super().__init__(AF_INET, SOCK_DGRAM)
        self.port = port
        self.address = address
        self.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        self.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if os.name != 'nt':
            from socket import SO_REUSEPORT
            self.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        self.bind(('', port))

    def __del__(self):
        self.close()
