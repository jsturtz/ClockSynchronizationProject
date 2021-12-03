
import socket
import struct
import sys
import threading

from enums import Signal, State

# We can create our own custom event classes like this
class MessageEvent(threading.Event):
    def __init__(self):
        super().__init__()
        self.__message = None
 
    def set_message(self, message):
        self.__message = message
 
    def get_message(self):
        return self.__message

# specific class only for stopping execution
class StopExecution(Exception):
    pass

# Override the standard run method to that when stop is called, doesn't 
class StoppableThread(threading.Thread):
    def run(self):
        try:
            super().run()
        except StopExecution:
            print("Thread stopped!")

    def stop(self):
        raise StopExecution

# Create a new thread class that can kill itself when another thread ends
class CustomThread(StoppableThread):

    def stop_when_thread_ends(self, thread: StoppableThread):
        while True:
            if not thread.is_alive():
                if self.is_alive():
                    print("Thread 1 is no longer alive, but I am so killing self")
                    self.stop()
                else:
                    print("Thread 1 is no longer alive, and I am also no longer alive, so nothing to do")
                sys.exit()

            print("Thread 1 is still alive...")
            sleep(2)

class Multicaster():
    def __init__():
        self.multicast_group = ('224.3.29.71', 10000)
        self.server_address = ('', 10000)
        self.my_ip_address = 0 # how do I get this programatically?

        # Create the datagram socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
        self.sock.bind(self.server_address)

        # Tell the operating system to add the socket to the multicast group
        # on all interfaces.
        group = socket.inet_aton(self.multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # This is done on the sender. Which of these is right? Do we need two sockets for this shared object?
        # Can just one socket work? My brain hurts
        ttl = struct.pack('b', 1)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        # FIXME: Don't think we need this since I'm handling blocking calls with threads
        # Set a timeout so the socket does not block indefinitely when trying
        # to receive data.
        # self.sock.settimeout(0.2)

    def broadcast(self, message):
        formatted_message = format_message(message)
        self.sock.sendto(formatted_message, multicast_group)

    def format_message(self, data: dict) -> str:
        # How do we want to format messsages for transport? Come up with some easy protocol. 
        # For now, assume data has "signal" key and just send that as bytes
        message = bytes("{signal}".format(**data), encoding='utf-8')
        return message

    def parse_message(self, data):
        # How do we want to parse messsages? Come up with some easy protocol
        # How do we handle badly formatted data? We probably dont' want an exception to propagate
        # FIXME: Once we figure out what we need to pass, change the parsing here
        message = {
            "signal": data,
        } 
        return message

    def parse_message(self, data):
        # How do we want to parse messsages? Come up with some easy protocol
        # How do we handle badly formatted data? We probably dont' want an exception to propagate
        # FIXME: Once we figure out what we need to pass, change the parsing here
        message = {
            "signal": data,
        } 
        return message

    def listen_for_message(self):
        # FIXME: What's a good size for recvfrom? Would depend on protocol if I implemented one
        data, address = sock.recvfrom(1024)
        if address != self.my_ip_address:
            # For now, parsing just returns {"signal": data}
            return self.parse_message(str(data))

    def trigger_event_if_signal(signal, handler_event: threading.Event):

        while True:
            message = listen_for_message()
            if message["signal"] == signal:
                handler_event.set()
                break
        sys.exit()

    # Then, we can define a task we want a thread to perform while waiting for the event to be triggered
    # def handle_timout_event(event, timeout, event_handler, event_handler_kwargs, timeout_handler, timeout_handler_kwargs):
        # event_set = event.wait(timeout)
        # if event_set:
        #     event_handler(**event_handler_kwargs)
        # else:
        #     timeout_handler(**timeout_handler_kwargs)
        # sys.exit()

    # Simple listener. Will indicate whether the given signal was detected within the timeout
    def signal_detected(signal, timeout):

        signal_event = MyCustomEvent()
        event_listener_thread = MyThread(
            name="Event-Listener", 
            target=trigger_event_if_signal, 
            kwargs={
            "signal": signal, 
            "signal_event": signal_event,
        })

        # Simplest way to handle timing out a blocking thread
        event_listener_thread.start()
        time.sleep(timeout)
        event_listener_thread.stop()
        return signal_event.is_set()

    # # Simple listener. Will 
    # def signal_detected(signal, timeout, signal_handler, signal_handler_kwargs, timeout_handler, timeout_handler_kwargs):

    #     signal_event = MyCustomEvent()
    #     handler_kwargs = {
    #         "event": e,
    #         "timeout": timeout,
    #         "signal_handler": signal_handler,
    #         "signal_handler_kwargs": signal_handler_kwargs,
    #         "timeout_handler": timeout_handler,
    #         "timeout_handler_kwargs": timeout_handler_kwargs,
    #     }
    #     event_listener_thread = MyThread(name="Event-Listener", target=trigger_event_if_signal, kwargs=listener_kwargs)
    #     event_listener_thread.start()
    #     time.sleep(timeout)
    #     return signal_event.is_set()

    #     event_handler_thread = MyThread(name="Event-Handler", target=handle_timout_event, kwargs=handler_kwargs)

    #     # listen for signals while thread1 is alive. If right signal shows up before thread1 terminates, call e.set()
    #     listener_kwargs = {
    #         "signal": signal, 
    #         "handler_event": e,
    #     }

    #     event_handler_thread.start()
    #     event_listener_thread.start()
    #     thread2.stop_when_thread_ends(thread1)

    # def sender():
    #     # Set the time-to-live for messages to 1 so they do not go past the
    #     # local network segment.

    #     try:
    #         while True:
    #             # Send data to the multicast group
    #             message = input("--> ")
    #             print("Message: %s" % message)
    #             sent = sock.sendto(bytes(message, encoding='utf-8'), multicast_group)
    #             if message == "q":
    #                 break

    #     finally:
    #         print("Closing sender socket")
    #         sock.close()

    # def receiver():
    #     # Receiver Logic

    #     multicast_group = '224.3.29.71'
    #     server_address = ('', 10000)

    #     # Create the socket
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #     # Bind to the server address
    #     sock.bind(server_address)

    #     # Tell the operating system to add the socket to the multicast group
    #     # on all interfaces.
    #     group = socket.inet_aton(multicast_group)
    #     mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    #     sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    #     # Receive/respond loop
    #     try:
    #         while True:
    #             data, address = sock.recvfrom(1024)
    #             if str(data) == "q":
    #                 break
    #             print(f"{address}: {data}")
    #     finally:
    #         print("Closing receiver socket")
    #         sock.close()

# from threading import Thread
# import sys

# def sender():
#     # Sender logic
#     import socket
#     import struct
#     import sys

#     multicast_group = ('224.3.29.71', 10000)

#     # Create the datagram socket
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#     # Set a timeout so the socket does not block indefinitely when trying
#     # to receive data.
#     sock.settimeout(0.2)

#     # Set the time-to-live for messages to 1 so they do not go past the
#     # local network segment.
#     ttl = struct.pack('b', 1)
#     sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

#     try:
#         while True:
#             # Send data to the multicast group
#             message = input("--> ")
#             print("Message: %s" % message)
#             sent = sock.sendto(bytes(message, encoding='utf-8'), multicast_group)
#             if message == "q":
#                 break

#     finally:
#         print("Closing sender socket")
#         sock.close()

# def receiver():
#     # Receiver Logic

#     import socket
#     import struct
#     import sys

#     multicast_group = '224.3.29.71'
#     server_address = ('', 10000)

#     # Create the socket
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#     # Bind to the server address
#     sock.bind(server_address)

#     # Tell the operating system to add the socket to the multicast group
#     # on all interfaces.
#     group = socket.inet_aton(multicast_group)
#     mreq = struct.pack('4sL', group, socket.INADDR_ANY)
#     sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

#     # Receive/respond loop
#     try:
#         while True:
#             data, address = sock.recvfrom(1024)
#             if str(data) == "q":
#                 break
#             print(f"{address}: {data}")
#     finally:
#         print("Closing receiver socket")
#         sock.close()

# def main():
#     sender_thread = Thread(group=None, target=sender, name="sender_thread")
#     sender_thread.daemon = True

#     receiver_thread = Thread(group=None, target=receiver, name="receiver_thread")
#     receiver_thread.daemon = True

#     sender_thread.start()
#     receiver_thread.start()

#     # Wait until the sender thread exits, then exit the process altogether
#     # Probably a better way to handle
#     sender_thread.join()

#     # By setting these threads as daemon threads, they will exit when the main program exists
#     sys.exit()

# if __name__ == "__main__":
#     main()


