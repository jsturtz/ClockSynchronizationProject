from threading import Thread
import sys

def sender():
    # Sender logic
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
        while True:
            # Send data to the multicast group
            message = input("--> ")
            print("Message: %s" % message)
            sent = sock.sendto(bytes(message, encoding='utf-8'), multicast_group)
            if message == "q":
                break

    finally:
        print("Closing sender socket")
        sock.close()

def receiver():
    # Receiver Logic

    import socket
    import struct
    import sys

    multicast_group = '224.3.29.71'
    server_address = ('', 10000)

    # Create the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to the server address
    sock.bind(server_address)

    # Tell the operating system to add the socket to the multicast group
    # on all interfaces.
    group = socket.inet_aton(multicast_group)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    # Receive/respond loop
    try:
        while True:
            data, address = sock.recvfrom(1024)
            if str(data) == "q":
                break
            print(f"{address}: {data}")
    finally:
        print("Closing receiver socket")
        sock.close()

def main():
    sender_thread = Thread(group=None, target=sender, name="sender_thread")
    sender_thread.daemon = True

    receiver_thread = Thread(group=None, target=receiver, name="receiver_thread")
    receiver_thread.daemon = True

    sender_thread.start()
    receiver_thread.start()

    # Wait until the sender thread exits, then exit the process altogether
    # Probably a better way to handle
    sender_thread.join()

    # By setting these threads as daemon threads, they will exit when the main program exists
    sys.exit()

if __name__ == "__main__":
    main()


