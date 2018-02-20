# -*- coding: utf-8 -*-
import random
import socket
import sys
import pickle

DATA_DIVIDE_LENGTH = 1024


class TCPPacket(object):
    """
    Add Documentation here
    """
    SMALLEST_STARTING_SEQ = 0
    HIGHEST_STARTING_SEQ = 9000  # 4294967295

    def __init__(self):
        # self.src_port = src_port  # 16bit
        # self.dst_port = dst_port  # 16bit
        self.seq = TCPPacket.gen_starting_seq_num()  # 32bit
        self.ack = 0  # 32bit
        self.data_offset = 0  # 4 bits
        self.reserved_field = 0  # 3bits saved for future use must be zero assert self.reserved_field = 0
        #FLAGS
        self.flag_ns = 0  # 1bit
        self.flag_cwr = 0  # 1bit
        self.flag_ece = 0  # 1bit
        self.flag_urg = 0  # 1bit
        self.flag_ack = 0  # 1bit
        self.flag_psh = 0  # 1bit
        self.flag_rst = 0  # 1bit
        self.flag_seq = 0  # 1bit
        self.flag_fin = 0  # 1bit
        #window size
        self.window_size = 0  # 16bit
        #checksum
        self.checksum = 0  # 16bit
        #urgent pointer
        self.urgent_pointer = 0  # 16bit
        #options
        self.options = 0  # 0-320bits, divisible by 32
        #padding - TCP packet must be on a 32bit boundary this ensures that it is the padding is filled with 0's
        self.padding = 0  # as much as needed
        self.data = ""

    def __repr__(self):
        return "TCPpacket()"

    def __str__(self):
        return "SEQ Number: %d, ACK Number: %d" \
               % (self.seq, self.ack)

    @staticmethod
    def gen_starting_seq_num():
        return random.randint(TCPPacket.SMALLEST_STARTING_SEQ, TCPPacket.HIGHEST_STARTING_SEQ)


class TCP(object):

    def __init__(self, server_address=('localhost', 10000)):
        self.own_packet = TCPPacket()  # last packet of communication.
        self.own_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket used for communication.
        # self.server_address = server_address  # Server's address
        self.receiver_address = ""
        self.own_address = ""  # maybe change listen to listen to own address and to send to receiver

# Every change of the sequence and acknowledgment numbers needs to be changed to add the length of the packet itself too
    def send(self, data):
        data_parts = TCP.data_divider(data)
        for data_part in data_parts:
            self.own_packet.seq += len(data_part)
            checksum_of_data = TCP.checksum(data_part)
            self.own_packet.checksum = checksum_of_data
            self.own_packet.data = data_part
            packet_to_send = pickle.dumps(self.own_packet)
            self.own_socket.sendto(packet_to_send, self.receiver_address)
            answer, address = self.own_socket.recvfrom(1024)
            self.own_packet.ack += 1
            answer = pickle.loads(answer)
            while (answer.ack - 1) != self.own_packet.seq:
                packet_to_send = pickle.dumps(self.own_packet)
                self.own_socket.sendto(packet_to_send, self.receiver_address)
                answer, address = self.own_socket.recvfrom(1024)
                answer = pickle.loads(answer)
                self.own_packet.ack += 1

    def recv(self):
        data = ""

        while True:

            data_part, address = self.own_socket.recvfrom(1024)
            data_part = pickle.loads(data_part)
            checksum_value = TCP.checksum(data_part.data)

            while checksum_value != data_part.checksum:

                self.own_packet.seq += 1
                self.own_socket.sendto(self.own_packet, address)
                data_part, address = self.own_socket.recvfrom(1024)
                data_part = pickle.loads(data_part)
                checksum_value = TCP.checksum(data_part.data)
            data += data_part.data
            self.own_packet.ack += (len(data_part.data) + 1)
            self.own_packet.seq += 1
            packet_to_send = pickle.dumps(self.own_packet)
            self.own_socket.sendto(packet_to_send, address)

            if len(data_part.data) == 0:
                break

        return data

        # while len(data_part) == 1024


    def listen(self, server_address=('localhost', 10000)):
        """ Server-side Handshake """
        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # Bind the socket to the port
            print >>sys.stderr, 'starting up on %s port %s' % server_address
            sock.bind(server_address)

            print >> sys.stderr, '\nwaiting to receive message'
            client_first_packet, address = sock.recvfrom(4096)
            client_first_packet = pickle.loads(client_first_packet)
            print "from client first: " + str(client_first_packet)
            print address
            server_first_packet = TCPPacket()
            server_first_packet.ack = client_first_packet.seq + 1
            print "server: " + str(server_first_packet)
            server_first_packet = pickle.dumps(server_first_packet)
            sock.sendto(server_first_packet, address)
            client_second_packet, addr = sock.recvfrom(1024)
            client_second_packet = pickle.loads(client_second_packet)

            print "from client last: ",
            print client_second_packet

            self.own_socket = sock
            temp = client_second_packet.seq
            client_second_packet.seq = client_second_packet.ack
            client_second_packet.ack = temp
            self.own_packet = client_second_packet
            # -------------------- CHECK MAYBE NOT NEEDED --------
            self.receiver_address = addr
            self.own_address = server_address

        except Exception as error:
            print "Something went wrong: " + str(error)
            sock.close()

    def connect(self, server_address=('localhost', 10000)):  # -------------------------------------------server address
        """ Client-side Handshake """
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:

            client_first_packet = TCPPacket()
            print "client: " + str(client_first_packet)
            client_first_packet = pickle.dumps(client_first_packet)

            # Send data
            print >> sys.stderr, 'sending "%s"' % client_first_packet
            sock.sendto(client_first_packet, server_address)

            # Receive response
            print >> sys.stderr, 'waiting to receive'
            server_first_packet, server = sock.recvfrom(4096)
            server_first_packet = pickle.loads(server_first_packet)
            print "From server Second: " + str(server_first_packet)
            temp = server_first_packet.seq + 1  # continue handshake
            server_first_packet.seq = server_first_packet.ack
            server_first_packet.ack = temp
            print "client: " + str(server_first_packet)
            server_first_packet = pickle.dumps(server_first_packet)
            sock.sendto(server_first_packet, server)

            self.own_socket = sock
            server_first_packet = pickle.loads(server_first_packet)
            self.own_packet = server_first_packet
            # -------------------- CHECK MAYBE NOT NEEDED --------
            self.receiver_address = server_address
            # self.own_address = ? not really needed for client

        except Exception as error:
            print "Something went wrong: " + str(error)
            sock.close()

    @staticmethod
    def data_divider(data):
        """Divides the data into a list where each element's length is 1024"""
        data = [data[i:i + DATA_DIVIDE_LENGTH] for i in range(0, len(data), DATA_DIVIDE_LENGTH)]
        data.append("")
        return data

    @staticmethod
    def checksum(source_string):
        sum = 0
        count_to = (len(source_string) / 2) * 2
        count = 0
        while count < count_to:
            this_val = ord(source_string[count + 1])*256+ord(source_string[count])
            sum = sum + this_val
            count = count + 2
        if count_to < len(source_string):
            sum = sum + ord(source_string[len(source_string) - 1])
        sum = (sum >> 16) + (sum & 0xffff)
        sum = sum + (sum >> 16)
        answer = ~sum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)
        return answer
