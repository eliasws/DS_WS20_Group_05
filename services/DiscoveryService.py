import time

from config import BROADCAST_INTERVAL
from dynamic_discovery.broadcast_converter import from_broadcast_message
from dynamic_discovery.BroadcastMessage import BroadcastMessage
from threading import Thread

from models.Host import Host, HostType


class DiscoveryService(Thread):
    def __init__(self, own_host: Host, socket_service, discovery_counter):
        Thread.__init__(self)
        self.is_broadcasting = False
        self.discovery_counter = discovery_counter
        self.socket_service = socket_service
        self.counter = 0
        self.own_host = own_host

    def run(self):
        broadcast_message = BroadcastMessage(self.own_host.unicast_port)
        time.sleep(BROADCAST_INTERVAL)
        while True:
            if self.is_broadcasting:
                data = from_broadcast_message(broadcast_message)
                print("Send broadcast")
                self.socket_service.send_broadcast("BC", data)
                self.counter = self.counter + 1
                if self.discovery_counter:
                    self.discovery_counter(self.counter)
            time.sleep(BROADCAST_INTERVAL)

    def start_broadcasting(self):
        self.counter = 0
        self.is_broadcasting = True

    def stop_broadcasting(self):
        self.counter = 0
        self.is_broadcasting = False
