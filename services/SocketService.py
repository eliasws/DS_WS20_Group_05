import datetime
import json
import uuid

import select
import traceback
from threading import Thread

from config import BROADCAST_ADDRESS, BUFFER_SIZE, SERVER_GROUP_BASE_MULTICAST_ADDRESS, BROADCAST_PORT, \
    HEADER_DELIMITER, SERVER_GROUP_MULTICAST_PORT, DEBUG, HEARTBEAT
from models.Host import Host
from sockets.BroadcastSocket import BroadcastSocket
from sockets.MulticastSocket import MulticastSocket
from sockets.UnicastSocket import UnicastSocket


class DeliveryState:
    DELIVERABLE = "deliverable"
    UNDELIVERABLE = "undeliverable"


class SocketService(Thread):
    def __init__(self, own_host: Host, on_host_failed):
        Thread.__init__(self)
        self.groups = []
        self.own_host = own_host
        self.broadcast_socket = BroadcastSocket(BROADCAST_ADDRESS, BROADCAST_PORT)
        self.unicast_socket = UnicastSocket(own_host.address, own_host.unicast_port)
        self.multicast_socket = MulticastSocket(SERVER_GROUP_BASE_MULTICAST_ADDRESS, SERVER_GROUP_MULTICAST_PORT)

        self.on_multicast_delivered = None
        self.on_unicast_delivered = None
        self.on_broadcast_delivered = None
        self.on_host_failed = on_host_failed

        self.sockets = [self.unicast_socket, self.broadcast_socket, self.multicast_socket]

    def set_on_broadcast_delivered(self, on_broadcast_received):
        self.on_broadcast_delivered = on_broadcast_received

    def set_on_unicast_delivered(self, on_unicast_received):
        self.on_unicast_delivered = on_unicast_received

    def set_on_multicast_delivered(self, on_multicast_received):
        self.on_multicast_delivered = on_multicast_received

    def add_group(self, group):
        if group not in self.groups:
            self.groups.append(group)

    def _get_base_header(self, method):
        return {
            'id': self.own_host.id,
            't': self.own_host.host_type,
            'p': self.own_host.unicast_port,
            'm': method
        }

    def _to_message(self, header: dict, payload):
        json_header = json.dumps(header)
        return HEADER_DELIMITER.join([json_header, str(payload)]).encode()

    def _from_message(self, message):
        decoded_message = message.decode('utf-8')
        message_chunks = decoded_message.split(HEADER_DELIMITER)
        header = json.loads(message_chunks[0])
        payload = ''
        if len(message_chunks) > 1:
            payload = message_chunks[1]
        return header, payload

    def send_broadcast(self, method: str, message: str = ''):

        header = self._get_base_header(method)
        encoded_message = self._to_message(header, message)

        if DEBUG:
            print(
                f"[BROADCAST:SENT:{method}] {header} {message} to {self.broadcast_socket.address}:{self.broadcast_socket.port}")

        self.broadcast_socket.sendto(
            encoded_message,
            (self.broadcast_socket.address, self.broadcast_socket.port)
        )

    def _on_broadcast_received(self, header, host: Host, method: str, message: str):
        # Note: Broadcast is not dynamic
        if host.id != self.own_host.id:
            host.unicast_port = message
            if DEBUG:
                print(f"[BROADCAST:REC:{method}] {message} from {host.address}:{host.unicast_port} ({host.id})")
            self.on_broadcast_delivered(host, method, message)

    def send_unicast(self, host: Host, method: str, message):
        if not host:
            return

        header = self._get_base_header(method)

        if method != "ACK":
            host.message_seq = host.message_seq + 1
            header['seq'] = host.message_seq

        encoded_message = self._to_message(header, message)

        if method != "ACK":
            if host.open_ack:
                print("Resent Message Unicast")
                self.unicast_socket.sendto(
                    host.last_message_sent,
                    (host.address, int(host.unicast_port))
                )

        if DEBUG and not method == 'ACK':
            if method != "HB" or HEARTBEAT:
                print(
                    f"[UNICAST:SENT:{method}] {header} {message} to {host.address}:{host.unicast_port} ({host.id})")

        host.last_message_sent = encoded_message
        self.unicast_socket.sendto(
            encoded_message,
            (host.address, int(host.unicast_port))
        )

    def _on_unicast_received(self, header, host: Host, method: str, message: str):
        if method == 'ACK':
            host.open_ack = False
        elif method == "SEQ/PROP":
            if DEBUG:
                print(
                    f"[UNICAST:REC:{method}] {message} from {host.address}:{host.unicast_port} ({host.id})")

            message_payload = json.loads(message)
            message_id = message_payload.get("m_id")
            group_id = message_payload.get("g_id")
            suggested_sequence_number = message_payload.get("s_seq")
            group = self._find_group(group_id)

            hold_back_message = self._find_hold_back_message_by_id(group, message_id)

            if not hold_back_message:
                print("Multicast could not get message for proposal", message_id)
                return
            if 'suggested_numbers' not in hold_back_message:
                hold_back_message['suggested_numbers'] = {}

            hold_back_message['suggested_numbers'][header.get('id')] = suggested_sequence_number

            if DEBUG:
                print(f"Proposal {message_id} with {group.participants} participants")

            if len(hold_back_message['suggested_numbers'].keys()) >= len(group.participants) and self.own_host.id in \
                    hold_back_message['suggested_numbers'].keys():
                # choose smallest possible value for identity if there are multiple suggesting this sequence
                if DEBUG:
                    print(f"Number of participants {hold_back_message['suggested_numbers']}")
                max_value = 0
                max_key = None
                for [k, v] in hold_back_message['suggested_numbers'].items():
                    if v > max_value:
                        max_value = v
                        if not max_key or max_key < k:
                            max_key = k

                self.send_group_multicast(group, "SEQ/ANNOUNCEMENT", json.dumps({
                    "m_id": message_id,
                    "max_suggested_seq": max_value,
                    "max_suggested_process_id": max_key
                }))
        else:
            self.send_unicast(host, "ACK", header.get('seq'))
            host.last_message_seq = header.get('seq')
            if DEBUG and not method == 'ACK':
                if method != "HB" or HEARTBEAT:
                    print(f"[UNICAST:REC:{method}] {message} from {host.address}:{host.unicast_port} ({host.id})")
            self.on_unicast_delivered(host, method, message)

    def resend_group_multicast(self, group, seq, header, method: str, message):
        if DEBUG:
            print(
                f"[MULTICAST:RESENT:{method}] {header} {message if not method == 'GS/OV' else ''} "
                f"to {self.multicast_socket.address}:{self.multicast_socket.port}")
        header["resent"] = seq
        encoded_message = self._to_message(header, message)

        self.multicast_socket.sendto(
            encoded_message,
            (self.multicast_socket.address, self.multicast_socket.port)
        )

    def _find_group(self, group_identifier):
        return next((group for group in self.groups if group.identifier == group_identifier), None)

    def _find_hold_back_message_by_id(self, group, message_id):
        if not group:
            return
        return next((item for item in group.hold_back_queue if item.get('header', {}).get('m_id') == message_id), None)

    def _find_hold_back_message_by_sender(self, group, sender_id):
        return next((item for item in group.hold_back_queue if item.get('header', {}).get('id') == sender_id), None)

    def _find_hold_back_message_by_deliverable(self, group, seq):
        return next(
            (item for item in group.hold_back_queue if item.get('max_suggested_seq') == seq
             and item.get('state') == DeliveryState.DELIVERABLE),
            None)

    def send_group_multicast(self, group, method: str, message: str = ''):

        header = self._get_base_header(method)
        header["g_ident"] = group.identifier

        header['m_id'] = str(uuid.uuid1())  # i
        if DEBUG:
            print(
                f"[MULTICAST:SENT:{method}] {header} {message if not method == 'GS/OV' else ''} to {self.multicast_socket.address}:{self.multicast_socket.port}")

        encoded_message = self._to_message(header, message)
        if not method == 'SEQ/ANNOUNCEMENT' and not method == 'NACK':
            self._add_message_to_hold_back(
                group=group,
                host=self.own_host,
                header=header,
                method=method,
                message=message,
                sequence=group.sequencer.get_sequence(),
                sequence_suggester=self.own_host.id,
                state=DeliveryState.UNDELIVERABLE
            )

        self.multicast_socket.sendto(
            encoded_message,
            (self.multicast_socket.address, self.multicast_socket.port)
        )

    def _add_message_to_hold_back(self, group, host, header, method, message, sequence, sequence_suggester, state,
                                  resent=False):
        hold_back_message = {
            "host": host,
            "header": header,
            "method": method,
            "message": message,
            'resent': resent,
            "max_suggested_seq": sequence,  # si
            "max_suggested_process_id": sequence_suggester,  # si
            "state": state
        }
        group.hold_back_queue.append(hold_back_message)
        return hold_back_message

    def _check_queue_for_max_number(self, group):

        group.hold_back_queue = sorted(group.hold_back_queue, key=lambda t: t.get("max_suggested_process_id"))
        group.hold_back_queue = sorted(group.hold_back_queue,
                                       key=lambda t: 0 if t.get("state") == DeliveryState.UNDELIVERABLE else 1)
        group.hold_back_queue = sorted(group.hold_back_queue, key=lambda t: t.get("max_suggested_seq"))

        list_copy = []
        for item in group.hold_back_queue:
            if DEBUG:
                print("Last", group.group_last_message_delivered_seq, item.get('max_suggested_seq'), item.get("state"))
                if item.get('state') == DeliveryState.UNDELIVERABLE:
                    print("MESSAGE", item.get('header'), item.get('header'), item.get('suggested_numbers'))
            if int(item.get('max_suggested_seq')) == group.group_last_message_delivered_seq + 1 and item.get(
                    "state") == DeliveryState.DELIVERABLE:
                group.group_last_message_delivered_seq = group.group_last_message_delivered_seq + 1
                if DEBUG:
                    print("DELIVER MESSAGE WITH SEQUENCE NUMBER", item.get('max_suggested_seq'),
                          item.get('header', {}))
                self.on_multicast_delivered(item.get("host"), item.get("method"), item.get("message"),
                                            item.get("header"))
                group.message_history[item.get('max_suggested_seq')] = item
            else:
                list_copy.append(item)
        group.hold_back_queue = list_copy

    def _on_multicast_received(self, header, host: Host, method, message: str):

        if 't' in header and header.get('t') == 'monitor':
            self.on_multicast_delivered(host, method, message, header)
            return

        if "g_ident" not in header:
            raise Exception("Could not find valid header", header)

        group_identifier = header["g_ident"]
        group = self._find_group(group_identifier)

        if not group:
            print(f"Not in group {group_identifier}, discard")
            return

        if method == "NACK":
            payload = json.loads(message)
            missing_sequences = json.loads(payload.get('seq'))
            for missing_seq in missing_sequences:
                if missing_seq in group.message_history:
                    missed_message = group.message_history[missing_seq]
                    if missed_message:
                        if DEBUG:
                            print("RESENT MESSAGE", missing_seq)
                        self.resend_group_multicast(
                            group,
                            missing_seq,
                            missed_message.get("header"),
                            missed_message.get("method"),
                            missed_message.get("message"),
                        )

        elif method == "SEQ/ANNOUNCEMENT":
            message_payload = json.loads(message)
            message_id = message_payload.get("m_id")
            max_suggested_seq = message_payload.get("max_suggested_seq")
            max_suggested_process_id = message_payload.get("max_suggested_process_id")
            group.sequencer.sequence = max(group.sequencer.get_sequence(), max_suggested_seq)
            hold_back_message = self._find_hold_back_message_by_id(group, message_id)

            if DEBUG:
                print("Received announcement for ", max_suggested_seq, message_id)

            if not hold_back_message:
                if DEBUG:
                    print("Multicast could not get message for announcement, probably already delivered", message_id)
                return

            hold_back_message['max_suggested_seq'] = max_suggested_seq
            hold_back_message['max_suggested_process_id'] = max_suggested_process_id
            hold_back_message['state'] = DeliveryState.DELIVERABLE

            if max_suggested_seq <= group.group_last_message_delivered_seq:
                if DEBUG:
                    print(
                        f"Got lower sequence number then expected: current: {group.group_last_message_delivered_seq}, "
                        f"got {max_suggested_seq}; discard message")
                group.hold_back_queue.remove(hold_back_message)
                return
            elif max_suggested_seq > group.group_last_message_delivered_seq + 1:
                # TODO: Dont request the messages we already have!
                sequences = list(range(group.group_last_message_delivered_seq + 1, max_suggested_seq))
                for sq in sequences:
                    if self._find_hold_back_message_by_deliverable(group, sq):
                        sequences.remove(sq)
                if DEBUG:
                    print(f"MISSING MESSAGE; GOT {max_suggested_seq},  SENDING NACK FOR ", sequences)
                self._send_group_multicast_nack(group, json.dumps(sequences))

            self._check_queue_for_max_number(group)

        else:
            # https://studylib.net/doc/7830646/isis-algorithm-for-total-ordering-of-messages
            if 'resent' in header:
                resent_number = int(header.get('resent'))
                if resent_number not in group.message_history:
                    if DEBUG:
                        print("RECEIVED RESENT MESSAGE!", resent_number, method)
                    hold_back_message = self._find_hold_back_message_by_id(group, header.get('m_id'))
                    if hold_back_message:
                        group.hold_back_queue.remove(hold_back_message)
                    self._add_message_to_hold_back(
                        group=group,
                        host=host,
                        header=header,
                        method=method,
                        message=message,
                        sequence=resent_number,
                        sequence_suggester=self.own_host.id,
                        resent=True,
                        state=DeliveryState.DELIVERABLE
                    )

                    self._check_queue_for_max_number(group)
            else:
                if DEBUG:  # host.id != self.own_host.id and
                    print(
                        f"[MULTICAST:REC:{method}] {header}  {message if not method == 'GS/OV' else ''}"
                        f" from {host.address}:{host.unicast_port} ({host.id})")

                group.sequencer.increment_sequence()
                sequence = group.sequencer.get_sequence()

                hold_back_message = self._find_hold_back_message_by_id(group, header.get('m_id'))
                if not hold_back_message:
                    self._add_message_to_hold_back(
                        group=group,
                        host=host,
                        header=header,
                        method=method,
                        message=message,
                        sequence=sequence,
                        sequence_suggester=self.own_host.id,
                        state=DeliveryState.UNDELIVERABLE
                    )

                self.send_unicast(
                    host,
                    "SEQ/PROP",
                    json.dumps({
                        'm_id': header.get('m_id'),
                        's_seq': sequence,
                        'g_id': group_identifier,
                    }),
                )

    def _send_group_multicast_nack(self, group, seq):
        method = 'NACK'
        payload = {"seq": str(seq)}
        self.send_group_multicast(
            group,
            method,
            json.dumps(payload),
        )

    def run(self):
        print(f"[BROADCAST] Start listening {self.broadcast_socket.address}:{self.broadcast_socket.port}")
        print(f"[UNICAST] Start listening {self.unicast_socket.address}:{self.unicast_socket.port}")
        print(f"[MULTICAST] Start listening {self.multicast_socket.address}:{self.multicast_socket.port}")
        while True:
            # Await an event on a readable socket descriptor
            (read, write, exception) = select.select(self.sockets, [], [])
            # Iterate through the tagged read descriptors
            for error in exception:
                print("GOT ERROR IN ", error)
            for wr in write:
                print("GOT WRITE IN ", wr)
            for receiver in read:
                try:
                    data, address = receiver.recvfrom(BUFFER_SIZE)

                    hostname = address[0]
                    port = address[1]

                    header, payload = self._from_message(data)

                    host = Host(header.get('id'), hostname, header.get('p'), header.get('t'))

                    method = header.get('m')

                    if receiver == self.broadcast_socket:
                        self._on_broadcast_received(header, host, method, payload)
                    elif receiver == self.unicast_socket:
                        self._on_unicast_received(header, host, method, payload)
                    elif receiver == self.multicast_socket:
                        self._on_multicast_received(header, host, method, payload)
                except Exception as e:
                    if e and hasattr(e, 'errno') and e.errno == 10054:
                        self.on_host_failed()
                        print("Host failed! We dont know which one :(")
                    else:
                        print("Exception", e)
                        traceback.print_exc()
                    continue
