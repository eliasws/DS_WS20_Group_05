import random
import socket

from config import SERVER_GROUP_BASE_MULTICAST_ADDRESS


def get_local_address():
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_address = s.getsockname()[0]
        return local_address
    finally:
        if s:
            s.close()


def get_random_unicast_port():
    return random.randint(49152, 55000)
