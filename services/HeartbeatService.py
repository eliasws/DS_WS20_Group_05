import time

from services.SocketService import SocketService
from config import HEARTBEAT_INTERVAL, PAYLOAD_DELIMITER, HEARTBEAT_MAX, DEBUG, HEARTBEAT
from threading import Thread

from models.Host import Host
from models.Ring import Ring


class HeartbeatService(Thread):
    def __init__(self, own_host: Host, ring: Ring, socket_service: SocketService):
        Thread.__init__(self)
        self.is_sending = False
        self.last_messages = {}
        self.socket_service = socket_service
        self.own_host = own_host
        self.on_heartbeat_missing = None
        self.ring = ring

    def __del__(self):
        self.is_sending = False

    def run(self):
        while True:
            if self.is_sending and len(self.ring.nodes) > 1:
                left_neighbour = self.ring.get_left_neighbour()
                right_neighbour = self.ring.get_right_neighbour()
                if left_neighbour and left_neighbour.id != self.own_host.id:
                    current_time = time.time()
                    self.socket_service.send_unicast(left_neighbour, "HB", current_time)
                if right_neighbour and right_neighbour.id != self.own_host.id:
                    if right_neighbour.id in self.last_messages \
                            and time.time() - float(self.last_messages[right_neighbour.id]):
                        if DEBUG and HEARTBEAT:
                            print("TIME", right_neighbour.id, time.time() - float(self.last_messages[right_neighbour.id]))
                    if right_neighbour.id in self.last_messages \
                            and time.time() - float(self.last_messages[right_neighbour.id]) > HEARTBEAT_MAX:

                        self.on_heartbeat_missing(right_neighbour)
            time.sleep(HEARTBEAT_INTERVAL)

    def set_on_heartbeat_missing(self, func):
        self.on_heartbeat_missing = func

    def on_heartbeat_received(self, host, payload):
        self.last_messages[host.id] = payload

    def start_heartbeat(self):
        if not self.is_sending:
            self.is_sending = True
            self.start()

    def stop_heartbeat(self):
        if self.is_sending:
            self.is_sending = False
            self.join()
