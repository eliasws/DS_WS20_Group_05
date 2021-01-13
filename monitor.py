import json
import pickle
import traceback
import uuid
from types import SimpleNamespace

import select
import os

from config import SERVER_GROUP_BASE_MULTICAST_ADDRESS, SERVER_GROUP_MULTICAST_PORT, BUFFER_SIZE, PAYLOAD_DELIMITER, \
    HEADER_DELIMITER
from models.Host import Host
from sockets.MulticastSocket import MulticastSocket
from util.terminal_helper import cls


def render():
    cls()

    print(f"Last update: \n"
          f"{encoded_data} \n")

    print("{:<8} {:<12} {:<14} {:<16} {:<32}".format('index', 'is leader', 'address', 'host type', 'id'))
    for num, host in enumerate(hosts):
        print("{:<8} {:<12} {:<14} {:<16} {:<32}".format(num, str(host.id == leader_id), host.address,
                                                         host.host_type, host.id))


if __name__ == "__main__":
    hosts = []

    leader_id = None
    multicast_socket = MulticastSocket(SERVER_GROUP_BASE_MULTICAST_ADDRESS, SERVER_GROUP_MULTICAST_PORT)
    print("Start monitor")
    header = json.dumps({
        'id': str(uuid.uuid1()),
        't': "monitor",
        'g_ident': "MAIN_GROUP",
        'm': "MAIN_GROUP/GET_HOSTS"
    })
    multicast_socket.sendto(
        header.encode()
        , (SERVER_GROUP_BASE_MULTICAST_ADDRESS, SERVER_GROUP_MULTICAST_PORT))
    while True:
        (read, write, exception) = select.select([multicast_socket], [], [])
        # Iterate through the tagged read descriptors
        for receiver in read:
            try:
                data, address = receiver.recvfrom(BUFFER_SIZE)

                encoded_data = data.decode('utf-8')
                hostname = address[0]
                port = address[1]
                chunks = encoded_data.split(HEADER_DELIMITER)
                header = json.loads(chunks[0])
                method = header.get('m')
                message = ''
                if len(chunks) > 1:
                    message = chunks[1]
                message_chunks = message.split(PAYLOAD_DELIMITER)
                if method == "LCR/LEADER_CHANGED":
                    leader_id = message_chunks[0]
                    render()
                elif method == "MAIN_GROUP/HOSTS":
                    print("GOT HOST UPDATE")
                    if 'resent' not in header:
                        hosts = json.loads(message)
                        hosts = [Host.from_json(h) for h in hosts]
                        render()
            except Exception as e:
                print("Exception", e)
                traceback.print_exc()
                continue
