
import random
import socket
import struct
import sys
import time
import threading
from enum import Enum, unique
import multiprocessing

RESYNC_RATE = 3
DEFAULT_TIMEOUT = 5
MAX_CLOCK_DRIFT = 10
MY_CLOCK_DRIFT = random.randrange(-MAX_CLOCK_DRIFT, MAX_CLOCK_DRIFT)

# There are a finite number of states, so can just use ENUM to reduce errors
@unique
class State(Enum):
    START = 1
    NOLEADER = 2
    LEADER = 3
    FOLLOWER = 4
    CONSISTENCY = 5
    CONFLICT = 6
    ACCEPT = 7
    CANDIDATE = 8
    RESOLVE = 9

# There are a finite number of signals, so can just use ENUM to reduce errors
@unique
class Signal(Enum):
    ACK = 1
    LEADERREQ = 2
    LEADERACK = 3
    LEADERUP = 4
    FOLLOWERUP = 5
    ELECTION = 6
    REFUSE = 7
    ACCEPT = 8
    SYNCREQ = 9
    SYNCRESP = 10
    CONFLICT = 11
    RESOLVE = 12
    QUIT = 13
    CLOCKREQ = 14


class SignalDetector():

    def __init__(self, multicaster):
        self.__multicaster = multicaster


class Multicaster():
    # FIXME: Get rid of this after testing
    def __init__(self, temp_port):
        self.temp_port = temp_port
        self.multicast_group = ('224.3.29.71', 10000)
        # self.server_address = ('', 10000)
        self.server_address = ('', self.temp_port)
        self.my_ip_address = socket.gethostbyname("localhost")

        # Create the datagram socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
        self.sock.bind(self.server_address)

        # Tell the operating system to add the socket to the multicast group
        # on all interfaces.
        group = socket.inet_aton(self.multicast_group[0])
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # This is done on the sender. Which of these is right? Do we need two sockets for this shared object?
        # Can just one socket work? My brain hurts
        # ttl = struct.pack('b', 1)
        # self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        # FIXME: Don't think we need this since I'm handling blocking calls with threads
        # Set a timeout so the socket does not block indefinitely when trying
        # to receive data.
        # self.sock.settimeout(0.2)

    def multicast_signal(self, signal: Signal) -> None:
        message_dict = {"signal": signal.value, "sender_ip": self.my_ip_address}
        self.multicast_message(message_dict)

    def multicast_message(self, message_dict: dict) -> None:
        formatted_message = self.format_message(message_dict)
        self.sock.sendto(formatted_message, self.multicast_group)

    def format_message(self, data: dict) -> str:
        message = bytes("{signal}-{sender_ip}".format(**data), encoding='utf-8')
        return message

    def parse_message(self, data: bytes, ip_address: str):
        data = data.decode("utf-8")

        # FIXME: Decide what else we want to send along delimited by "-"
        # For now, assume we are only sending "<signal>-"
        signal = int(data.split("-")[0])
        message = {
            "signal": signal,
            "ip_address": ip_address,
        } 
        return message

    def get_multicast_message(self):
        print("In get multicast message...")
        # FIXME: What's a good size for recvfrom? Would depend on protocol if I implemented one
        data, ip_address = self.sock.recvfrom(1024)

        # FIXME: DO we need to worry about pickign up messages multicast by ourselves? Might depend on 
        # overall logic. If so, add some kind of check here that says "If message didnt' come from me..."
        # print("address: %s" % str(ip_address))
        # print("self.my_ip_address: %s" % self.my_ip_address)

        return self.parse_message(data, ip_address[0])

    # FIXME: Need to create the TCP socket logic for specific situations where we know the ip_address
    def send_message(self, ip_address, message):
        return {}

    # def get_signal_messages(self, signal, event_queue, reply=None):
    #     while True:
    #         message = self.handle_signal(signal, reply)
    #         event_queue.append(message)

    def handle_signal(self, signal, reply=None):
        while True:
            # FIXME: This should be handled with a queue so that we don't drop messages
            message = self.get_multicast_message()
            print("Handle signal got a message!")
            print("Message: %s" % message)
            print("Message[signal]: %s" % message["signal"])
            print("Message[signal] type: %s" % type(message["signal"]))
            print("Signal: %s" % signal.value)
            print("Signal type: %s" % type(signal.value))
            print("Are they the same?: %s" % message["signal"] == signal.value)
            if message["signal"] == signal.value:
                print("Message detected, returning...")
                if reply:
                    print("Seeing reply in handle_signal...")
                    self.send_message(self.format_message(reply), message["ip_address"])
                return message

    # Detects whether ANY signal in signals detected within timeout
    def signals_detected(self, signals, timeout):

        signal_values = [signal.value for signal in signals]
        print("signal_values we are listening for...")
        print(signal_values)

        # Create separate process to listen for multicasts and add them to the queue
        multicast_queue = multiprocessing.Queue()
        listener = multiprocessing.Process(target=self.queue_multicasts, args=(multicast_queue,))
        listener.start()

        # Then, check the multicast queue to see if the signal is among them
        start_time = time.time()
        detected = False
        while int(time.time() - start_time) < timeout:
            # Pop off queued multicasts, then check if they have the right signal
            if not multicast_queue.empty():
                message = multicast_queue.get()
                print("Message[signal] in multicast queue: %s" % message["signal"])
                if message["signal"] in signal_values:
                    detected = True
                    break

        # If detected or if timed out, kill our child process and return
        listener.terminate()
        return detected

    # Detects whether a single signal detected within timeout
    def signal_detected(self, signal, timeout):
        return self.signals_detected([signal], timeout)

    def queue_multicasts(self, multicast_queue: list) -> None:
        while True:
            message = self.get_multicast_message()
            multicast_queue.put(message)

    def start_multicast_listener(self):

        # Create separate process to listen for multicasts and add them to the queue
        self.multicast_queue = multiprocessing.Queue()
        self.listener = multiprocessing.Process(target=self.queue_multicasts, args=(self.multicast_queue,))
        self.listener.start()

    def stop_multicast_listener(self):
        self.listener.terminate()

    def check_queued_multicasts_for_signals(self, signals, signal_event):
        signal_values = [signal.value for signal in signals]
        print("signal_values: %s" % signal_values)
        while True:
            if not self.multicast_queue.empty():
                message = self.multicast_queue.get()
                print("There's a message in the multicast queue!")
                print("message: %s" % message)
                if message["signal"] in signal_values:
                    signal_event.set()
                    return

    def check_queued_multicasts_for_signal(self, signal, signal_event):
        self.check_queued_multicasts_for_signals([signal], signal_event)

    def wait_for_signals(self, signals, signal_event, timeout):
        signal_checker = multiprocessing.Process(
            target=self.check_queued_multicasts_for_signals, 
            kwargs={"signals": signals, "signal_event": signal_event})
        signal_checker.start()

        # Prematurely return if event is set
        start_time = time.time()
        while time.time() - start_time < timeout:
            if signal_event.is_set():
                break

        signal_checker.terminate()

    def wait_for_signal(self, signal, signal_event, timeout):
        self.wait_for_signals([signal], signal_event, timeout)

    def has_queued_messages(self):
        return not self.multicast_queue.empty()

    def get_queued_message(self):
        return self.multicast_queue.get()

    # # Detects whether any signal detected using a process (not easy to use threads)
    # def signals_detected(self, signals, timeout):

    #     processes = []
    #     signal_events = {signal: multiprocessing.Event() for signal in signals}
    #     for signal, event in signal_events.items():

    #         event_listener_process = multiprocessing.Process(
    #             target=self.trigger_event_if_signal_detected, 
    #             kwargs={"signal": signal, "event": event})

    #         event_listener_process.start()
    #         processes.append(event_listener_process)

    #     # Then wait for the timeout
    #     time.sleep(timeout)

    #     # Stop all the threads
    #     print("Killing processes...")
    #     for process in processes:
    #         process.terminate()

    #     returned_signals = {signal: event.is_set() for signal, event in signal_events.items()}
    #     print(returned_signals)
    #     return returned_signals

    # # Simple listener. Will indicate whether the given signal was detected within the timeout
    # def signal_detected(self, signal: Signal, reply, timeout: int) -> None:
    #     return self.signals_detected({signal: reply}, timeout)[signal]

class TimeDaemon():
    def __init__(self, temp_port) -> None:
        self.temp_port = temp_port
        self.__state = State.START
        self.__multicaster = Multicaster(temp_port)
    
    def print_my_state(self):
        print("State: %s" % self.__state)

    # =============================================================================
    def run(self) -> None:
        while True:
            self.print_my_state()
            if self.__state == State.START:
                self.start()
            elif self.__state == State.NOLEADER:
                self.no_leader()
            elif self.__state == State.LEADER:
                self.leader()
            elif self.__state == State.FOLLOWER:
                self.follower()
            elif self.__state == State.CONSISTENCY:
                self.consistency()
            elif self.__state == State.CONFLICT:
                self.conflict()
            elif self.__state == State.ACCEPT:
                self.accept()
            elif self.__state == State.CANDIDATE:
                self.candidate()

    # =============================================================================
    def fix_my_clock(self, clock_offset):
        # Implement fixing the local clock
        pass

    def get_my_clock(self):
        # Get the local clock time
        pass

    # =============================================================================
    def reply_to_sender(self, received_message, sending_message):
        # FIXME: Implement this
        print("Replying back to sender the following message: %s" % sending_message)

    # =============================================================================
    def start(self) -> None:

        # Randomly assign R, where RESYNC_RATE < R < 2 * RESYNC_RATE
        # timeout = random.randrange(RESYNC_RATE, RESYNC_RATE * 2)

        # FIXME: Temporary for testing.
        if self.temp_port == 10000:
            timeout = 10
        else:
            timeout = 5

        print("My start timeout is {}".format(timeout))

        # Start adding messages to queue before we multicast our LEADERREQ
        self.__multicaster.start_multicast_listener()

        # Then, send out a request for a leader to respond
        self.__multicaster.multicast_signal(Signal.LEADERREQ)

        # Wait here until up to timeout for the response
        signal_event = multiprocessing.Event()
        self.__multicaster.wait_for_signal(Signal.LEADERACK, signal_event, timeout)

        # Kill our listener since we don't need to store these messages anymore
        self.__multicaster.stop_multicast_listener()

        # If the signal was detected, there's a Leader so go to Consistency state to confirm
        if signal_event.is_set():
            self.__state = State.CONSISTENCY
        else:
            self.__state = State.NOLEADER

    # =============================================================================
    def no_leader(self) -> None:
        # FIXME: Use default timeout until I figure out how long to wait in each state
        timeout = DEFAULT_TIMEOUT

        self.__multicaster.start_multicast_listener()
        event = multiprocessing.Event()
        self.__multicaster.wait_for_signals([Signal.ELECTION, Signal.LEADERREQ, Signal.LEADERUP], event, timeout)

        if event.is_set():
            self.__state = State.FOLLOWER
        else:
            self.__state = State.LEADER

    # =============================================================================
    def candidate(self) -> None:
        pass
        # timeout = DEFAULT_TIMEOUT
        # refuse_event = MessageEvent()
        # accept_event = MessageEvent()

        # refuse_kwargs = {
        #     "signal": Signal.REFUSE, 
        #     "handler_event": refuse_event,
        #     "reply": {"signal": Signal.ACK},
        #     "number_of_signals": 1,
        # }
        # refuse_thread = StoppableThread(target=self.__multicaster.handle_signal, kwargs=refuse_kwargs)

        # accept_kwargs = {
        #     "signal": Signal.ACCEPT, 
        #     "handler_event": accept_event,
        #     "reply": {"signal": Signal.ACK},
        # }
        # accept_thread = StoppableThread(target=self.__multicaster.handle_signal, kwargs=accept_kwargs)

        # refuse_thread.start()
        # accept_thread.start()

        # start_time = time.time()
        # while True:
        #     # If our timer expires, time to become the Leader
        #     if int(time.time() - start_time) > timeout:
        #         accept_thread.stop()
        #         refuse_thread.stop()
        #         break

        #     # If we get any Refuse signals, stop everything and become a Follower
        #     if refuse_event.is_set():
        #         accept_thread.stop()
        #         refuse_thread.stop()
        #         self.__state = State.FOLLOWER
        #         return

        #     # Keep resetting the timer everytime we get an Accept until our timer expires
        #     if accept_event.is_set():
        #         start_time = time.time()
        #         accept_event.clear()

        # # Leader time
        # self.__state = State.LEADER

    # =============================================================================
    def leader(self) -> None:
        print("I am the leader now! Extra cool")
        self.__multicaster.multicast_signal(Signal.LEADERUP)
        while True:
            pass
        # self.followers = set()

        # def add_followers(self, response_queue, quit_event):
        #     kwargs = {
        #         "signal": Signal.LEADERREQ,
        #         "event_queue": response_queue,
        #     }
        #     # Start a thread to push all the messages onto the response_queue
        #     StoppableThread(target=self.__multicaster.get_signal_messages, kwargs=kwargs)
            
        #     # Then, until we get a CONFLICT message, keep iterating over those messages and process them
        #     while True:
        #         # FIXME: Necessary to do this constantly? Add a time.sleep()?
        #         if quit_event.is_set():
        #             break
        #         while response_queue:
        #             response1 = response_queue[0]
        #             message = {"signal": Signal.LEADERACK}
        #             response2 = self.send_message(response1["ip_address"], message)
        #             if response2["signal"] == Signal.CONFLICT:
        #                 quit_event.set()
        #                 break

        #             # Always add the followers from each response
        #             self.followers.add(response1["ip_address"])
        #             response_queue.remove(0)

        # def sync_clocks():
        #     def get_follower_clock_time(ip_address, clock_times):
        #         # FIXME: Implement this when I actually add the TCP connection stuff
        #         pass
        #         # clock_times.append(self.request_clock_time(ip_address))

        #     clock_times = []
        #     threads = []
        #     for follower in self.followers:
        #         thread = threading.Thread(target=get_follower_clock_time, kwargs={"ip_address": follower, "clock_times": clock_times})
        #         thread.start()
        #         threads.append(thread)

        #     # Wait until all threads have responded
        #     # FIXME: What happens if there's a failure? Do we need a timeout to ignore nodes that dont' reply?
        #     for thread in threads:
        #         thread.join() 

        #     # At this point, clock_times will have the clock times retreived from followers 
        #     # FIXME: Figure out what this is actually supposed to be
        #     average = sum(clock_times) / len(clock_times)

        #     # FIXME: Need to figure out what protocol to use for these messages
        #     message = {
        #         "signal": Signal.SYNCREQ,
        #         "time": average,
        #     }
        #     self.__multicaster.multicast(message)

        # conflict_event = threading.Event()
        # add_followers_thread = StoppableThread(target=add_followers, kwargs={"conflict_event": conflict_event})
        # add_followers_thread.start()

        # # FIXME: We need a listener to listen for RESOLVE and reply automatically with LEADERACK
        # resolve_event = threading.Event()
        # resolve_reply = {"signal": Signal.ACK}
        # resolve_kwargs = {
        #     "signal": Signal.RESOLVE,
        #     "handler_event": resolve_event,
        #     "reply": resolve_reply,
        # }
        # resolve_thread = StoppableThread(target=self.__multicaster.handle_signal, kwargs=resolve_kwargs)
        # resolve_thread.start()

        # # FIXME: If receive Quit message from a node, move to Follower state and respond with Ack message
        # quit_event = threading.Event()
        # resolve_kwargs = {
        #     "signal": Signal.QUIT,
        #     "handler_event": quit_event,
        #     "reply": {"signal": Signal.ACK},
        # }
        # quit_thread = StoppableThread(target=self.__multicaster.handle_signal, kwargs=resolve_kwargs)
        # quit_thread.start()

        # sync_clocks_thread = threading.Timer(interval=RESYNC_RATE, function=sync_clocks)
        # sync_clocks_thread.start()

        # # Now that we've started all the threads, check for whether they have set the events that will trigger a state change
        # while True:
        #     if conflict_event.is_set():
        #         self.__state = State.CONFLICT
        #         break
        #     if resolve_event.is_set():
        #         self.__state = State.RESOLVE
        #         break
        #     if quit_event.is_set():
        #         self.__state = State.FOLLOWER
        #         break

        # # Now, clean up the started threads
        # add_followers_thread.stop()
        # resolve_thread.stop()
        # quit_thread.stop()
        # sync_clocks_thread.cancel()

    # =============================================================================
    def consistency(self) -> None:
        print("In consistency state!")
        pass

        # Consistency:
        # Starts consistency_timer
        # If constency_timer expires, moves to Slave state
        # If receives Masterack from another node, it sends a Conflict message to the first leader node and immediately moves to Slave state of the second leader. 
        # This is a way of allowing a follower to fix a situation where two machines have decided they are leaders

    # =============================================================================
    def conflict(self) -> None:
        print("In conflict state!")
        while True:
            pass

        # Conflict:
        # Broadcast “Resolve” message
        # Starts conflict_timer
        # If conflict_timer expires, multicast Masterup message and move to Master state
        # If receives Masterack from a node in response to Resolve message, send back a Quit message

    # =============================================================================
    def follower(self) -> None:
        
        # FIXME: Test all this stuff

        # Start listening for messages
        self.__multicaster.start_multicast_listener()

        # FIXME: What about network latency? Should add small buffer to RESYNC_RATE probably
        election_timeout = RESYNC_RATE
        last_leader_message = time.time()

        # Process messages until election timeout
        while time.time() - last_leader_message < election_timeout or self.__multicaster.has_queued_messages():
            if self.__multicaster.has_queued_messages():
                message = self.__multicaster.get_queued_message()

                # Give the leader your current clock time
                if message["signal"] == Signal.CLOCKREQ.value:
                    sending_message = {
                        "signal": Signal.CLOCKRESP.value,
                        "clock_time": self.get_my_clock(),
                    }
                    self.reply_to_sender(message["ip_address"], sending_message)

                    # This message came from the leader, so restart the timer
                    last_leader_message = time.time()

                # Fix your current clock time if leader requests
                elif message["signal"] == Signal.SYNCREQ.value:
                    self.fix_my_clock(message["seconds"], message["microseconds"])
                    self.reply_to_sender(message["ip_address"], {"signal": Signal.SYNCRESP})

                    # This message came from the leader, so restart the timer
                    last_leader_message = time.time()

                elif message["signal"] == Signal.LEADERUP.value:
                    self.reply_to_sender(message["ip_address"], {"signal": Signal.FOLLOWERUP})

                elif message["signal"] == Signal.ELECTION.value:
                    self.reply_to_sender(message["ip_address"], {"signal": Signal.ACCEPT})
                    self.__state = State.ACCEPT
                    break

        self.__multicaster.stop_multicast_listener()

        # if we get to this point and we aren't in the ACCEPT state, then we should be in ELECTION state
        # Since the election timer must have gone off
        if self.__state != State.ACCEPT:
            self.__state = State.ELECTION

    # =============================================================================
    def accept(self) -> None:
        print("We are in the accept state. Cool!")
        while True:
            pass

        # Accept:
        # Start accept_timer
        # If accept_timer expires, move back to Follower state
        # If receive Masterup message, reply with Followerup message
        # If receive Election message, reply with Refuse message

# ============================================================================
def main():
    TimeDaemon(int(sys.argv[1])).run()

    # Testing Multicaster

    # multicaster = Multicaster(int(sys.argv[1]))
    # if int(sys.argv[1]) == 10000:
    #     print("Listening for ten seconds for Leaderack...")
    #     if multicaster.signal_detected(Signal.LEADERACK, 10):
    #         print("We detected the signal!")
    #     else:
    #         print("We did not detect the signal!")
    # elif int(sys.argv[1]) == 10001:
    #     # Have this guy wait for five seconds, then multicast
    #     print("Waiting for five seconds...")
    #     time.sleep(5)
    #     print("Broadcasting Leaderack...")
    #     multicaster.multicast_signal(Signal.LEADERACK)
    # else:
    #     raise Exception("Only testing two ports right now")

if __name__ == "__main__":
    main()
