
class TSPMessage():
    def __init__(self, type=None, version_no=None, sequence_no=None, secs=None, microsecs=None, machine_name=None) -> None:
        self.initialize_variables(type, version_no, sequence_no, secs, microsecs, machine_name)

    def initialize_variables(self, type, version_no, sequence_no, secs, microsecs, machine_name):
        self.type = type
        self.version_no = version_no
        self.sequence_no = sequence_no
        self.secs = secs
        self.microsecs = microsecs
        self.machine_name = machine_name

    def validate(self):
        # Do any validation to guarantee messages are valid
        raise Exception ("Not valid!")

    def create_message(self, type, version_no, sequence_no, secs, microsecs, machine_name) -> bytes:
        # Make sure we have the variables we need to create a message
        self.validate()

        # Do the work to create the bytes message corresponding to the TSP protocol
        # https://apps.dtic.mil/sti/pdfs/ADA611038.pdf
        return b""

    def parse_message(self, message: bytes) -> None:
        # Do the work of converting the bytes message to our member variables
        pass

import socket
import struct
import sys

multicast_group = ('224.3.29.71', 10000)

# Create the datagram socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set a timeout so the socket does not block indefinitely when trying
# to receive data.
sock.settimeout(0.2)

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

try:

    # Send data to the multicast group
    print >>sys.stderr, 'sending "%s"' % message
    sent = sock.sendto(message, multicast_group)

    # Look for responses from all recipients
    while True:
        print >>sys.stderr, 'waiting to receive'
        try:
            data, server = sock.recvfrom(16)
        except socket.timeout:
            print >>sys.stderr, 'timed out, no more responses'
            break
        else:
            print >>sys.stderr, 'received "%s" from %s' % (data, server)

finally:
    print >>sys.stderr, 'closing socket'
    sock.close()