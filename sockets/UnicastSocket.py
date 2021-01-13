import os
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR

class UnicastSocket(socket):
    # TODO: can have own id?
    def __init__(self, address, port):
        super().__init__(AF_INET, SOCK_DGRAM)
        self.address = address
        self.port = port
        self.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if os.name != 'nt':
            from socket import SO_REUSEPORT
            self.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        self.bind((address, port))

    def __del__(self):
        self.close()
