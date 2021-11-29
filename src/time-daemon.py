
from datetime import datetime
import multiprocessing
import os
import queue
import random
import socket
import struct
import sys
import time
import threading
from statistics import mean
from enum import Enum, unique
from multiprocessing import Event, Manager, Process, Queue
# import psutil
# from multiprocessing import log_to_stderr, SUBDEBUG
# import logging
# logger = log_to_stderr(SUBDEBUG)
from typing import Any, Dict, Optional, List, Set, Tuple

RESYNC_RATE = 30
DEFAULT_TIMEOUT = 10
SEC_DECIMAL_ROUND = 2
MAX_CLOCK_DRIFT = 0.1
MY_CLOCK_DRIFT = round(random.uniform(1-MAX_CLOCK_DRIFT, 1+MAX_CLOCK_DRIFT), SEC_DECIMAL_ROUND)
UDP_SOCKET_TIMEOUT = 5
DEFAULT_CHECK_QUEUE_INTERVAL=0.1


# There are a finite number of states, so can just use ENUM to reduce errors
@unique
class State(Enum):
    START = 1
    CONSISTENCY = 2
    NOLEADER = 3
    FOLLOWER = 4
    ACCEPT = 5
    CANDIDATE = 6
    LEADER = 7
    CONFLICT = 8

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
    CLOCKRESP = 15

# Typehint types
GroupType = Tuple[str, int]

class Messenger():
    def __init__(self, my_ip_address: str):
        self.my_ip_address = my_ip_address
        self.valid_keys_to_send = ["signal", "ip_address", "port", "timestamp", "adj_seconds"]

    def __format_message(self, data: dict) -> bytes:

        # Convert Signal to int before sending
        data["signal"] = data["signal"].value

        # Create the message string delimited by "|", using the valid_keys_to_send to order them, adding empty string for missing data items
        message = bytes("|".join([str(data.get(key) or "") for key in self.valid_keys_to_send]), encoding='utf-8')
        return message

    def __parse_message(self, data: bytes) -> Dict[str, Any]:
        message: Dict[str, Any]

        # Build the message dict back from the bytes message using the valid_keys_to_send to determine the keys
        message = {key: val for (key, val) in zip(self.valid_keys_to_send, data.decode("utf-8").split("|"))}

        # Turn back into Signal from int
        message["signal"] = Signal(int(message["signal"]))
        return message

    def recv_message(self, sock: socket.socket) -> Dict[str, Any]:
        data, _ = sock.recvfrom(1024)
        message_dict = self.__parse_message(data)
        # If we are multicasting to the same port we are listening on, we have to ignore messages from ourselves
        # print("Message dict: %s" % message_dict["ip_address"])
        # print("My ip_addres: %s" % self.my_ip_address)
        # print("Are they the same?: %s" % message_dict["ip_address"] == self.my_ip_address)
        # print("types")
        # print(type(self.my_ip_address))
        # print(type(message_dict["ip_address"]))
        return message_dict if message_dict["ip_address"] != self.my_ip_address else {}

    def create_listener_process(self, sock: socket.socket, message_queue: Queue) -> Process:

        def queue_messages(sock: socket.socket, message_queue: Queue) -> None:
            while True:
                message_dict = self.recv_message(sock)
                if message_dict:
                    # print("Adding message to message queue..")
                    message_queue.put(message_dict)

        return Process(target=queue_messages, args=(sock, message_queue), daemon=True)

    def send_signal(self, signal: Signal, sock: socket.socket, group: GroupType) -> None:
        message_dict = {"signal": signal}
        self.send_message(message_dict, sock, group)

    def send_message(self, message_dict: dict, sock: socket.socket, group: GroupType) -> None:
        message_dict["ip_address"] = self.my_ip_address
        formatted_message = self.__format_message(message_dict)
        # print("Sending this message: %s to group: %s" % (message_dict, group))
        sock.sendto(formatted_message, group)


class TimeDaemon():
    # FIXME: Don't pass the port in production. Just hardcode since all will be running on each machine
    # def __init__(self, singlecast_port, clock_sync_port, multicast_port) -> None:
    def __init__(self) -> None:

        # Once we've gotten a random drift, update the faketime to have that drift
        os.environ["FAKETIME"] = f"+0.00s x{MY_CLOCK_DRIFT}"


        # Get rid of log file each time for now
        f = open("logfile", "w+")
        f.truncate()
        f.close()

        self.my_ip_address = socket.gethostbyname(socket.gethostname())
        self.__state = State.START

        # FIXME: REmove for production
        if self.my_ip_address == '172.21.0.6':
            # FIXME: Just for testing extremes at the moment
            os.environ["FAKETIME"] = "+0.00s x1.1"
            self.__state = State.LEADER
        else:
            os.environ["FAKETIME"] = "+0.00s x0.9"
            self.__state = State.FOLLOWER

        self.__messenger = Messenger(self.my_ip_address)

        self.multiprocessing_manager = Manager()

        # Create a singlecaset socket for listening from / sending to messages to single receiver
        # self.singlecast_port = int(singlecast_port)
        self.singlecast_port = 1000
        self.singlecast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.singlecast_sock.bind((self.my_ip_address, self.singlecast_port))

        # Create a singlecaset socket for listening from / sending to messages to leader
        # self.clock_sync_port = int(clock_sync_port)
        self.clock_sync_port = 1001
        self.clock_sync_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.clock_sync_sock.bind((self.my_ip_address, self.clock_sync_port))

        # Create a multicast socket for listening for / sending to multiple receivers
        # self.multicast_port = int(multicast_port)
        self.multicast_port = 10000
        self.multicast_group = ('224.3.29.71', 10000)

        # Create the datagram socket for multicasting
        self.multicast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
        self.multicast_sock.bind(('', self.multicast_port))

        # Tell the operating system to add the multicast socket to the multicast group on all interfaces.
        group = socket.inet_aton(self.multicast_group[0])
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        self.multicast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # We will direct traffic from the general singlecast sock and the multicast sock to the same queue
        self.__message_queue: Queue = Queue()

        # FIXME: Make sure these processes get cleaned up. I think I just need the daemon mode arg to make it so they don't become
        # zombies
        self.singlecast_listener = self.__messenger.create_listener_process(self.singlecast_sock, self.__message_queue)
        self.singlecast_listener.start()

        self.multicast_listener = self.__messenger.create_listener_process(self.multicast_sock, self.__message_queue)
        self.multicast_listener.start()

        # We will also use a separate queue for messages from the followers about their times to simplify processing messages
        self.__clock_sync_queue: Queue = Queue()

        self.clock_sync_listener = self.__messenger.create_listener_process(self.clock_sync_sock, self.__clock_sync_queue)
        self.clock_sync_listener.start()

    # =============================================================================
    def clear_queue(self, q) -> None:
        while not q.empty():
            q.get()

    # =============================================================================
    def run(self) -> None:
        while True:
            # FIXME: Remove this for production
            print(self.__state)

            if self.__state == State.START:
                self.start()
            elif self.__state == State.CONSISTENCY:
                self.consistency()
            elif self.__state == State.NOLEADER:
                self.no_leader()
            elif self.__state == State.FOLLOWER:
                self.follower()
            elif self.__state == State.ACCEPT:
                self.accept()
            elif self.__state == State.CANDIDATE:
                self.candidate()
            elif self.__state == State.LEADER:
                self.leader()
            elif self.__state == State.CONFLICT:
                self.conflict()

    # =============================================================================
    def fix_my_clock(self, adj_seconds: float) -> None:
        # Implement fixing the local clock
        print("Adjusting clock by: %s" % adj_seconds)
        print("Current FAKETIME: %s" % os.environ["FAKETIME"])

        current_offset_as_str, current_drift = os.environ["FAKETIME"].split(" ")

        # Ignore sign and second symbol, convert to float
        current_offset = float(current_offset_as_str[:-1])

        # Add the adjustment
        current_offset += adj_seconds

        # Reassign back to env variable
        os.environ["FAKETIME"] = "{:+.{precision}f}s {}".format(current_offset, current_drift, precision=SEC_DECIMAL_ROUND)
        print("Adjusted FAKETIME: %s" % os.environ["FAKETIME"])

    # =============================================================================
    def get_my_clock(self) -> float:
        return datetime.now().timestamp()

    # =============================================================================
    def send_multicast_message(self, message_dict: Dict[str, Any]) -> None:
        self.__messenger.send_message(message_dict, self.multicast_sock, self.multicast_group)

    # =============================================================================
    def send_multicast_signal(self, signal: Signal) -> None:
        self.send_multicast_message({"signal": signal})

    # =============================================================================
    def send_message_to_ip_address(self, message_dict: Dict[str, Any], ip_address: str, port: Optional[int] = None, sock: Optional[socket.socket] = None) -> None:
        # If no port or sock provided, assume we are sending to the same singlecast port used by all machines
        group = (ip_address, port or self.singlecast_port)
        self.__messenger.send_message(message_dict, sock or self.singlecast_sock, group)

    # =============================================================================
    def send_signal_to_ip_address(self, signal: Signal, ip_address: str, port: Optional[int]=None, sock: Optional[socket.socket]=None) -> None:
        # If no port or sock provided, assume we are sending to the same singlecast port used by all machines
        group = (ip_address, port or self.singlecast_port)
        self.__messenger.send_signal(signal, sock or self.singlecast_sock, group)

    # =============================================================================
    def get_first_message_from_queue_by_signal(self, message_queue: Queue, signals: List[Signal], shared_dict: Dict[str, Any], terminate_event) -> None:

        # FIXME: Hate this, but we can't terminate a process that invokes .get() because then it will create a semaphore lock
        # That causes a deadlock on future attempts to get from the queue. Seems dumb.
        while True:
            try:
                message = message_queue.get_nowait()
            except queue.Empty:
                time.sleep(DEFAULT_CHECK_QUEUE_INTERVAL)
                continue

            # print("Message['signal']: %s" % message["signal"])
            # print("signals: %s" % signals)
            if message["signal"] in signals:
                shared_dict["message"] = message
                terminate_event.set()
                return

    # =============================================================================
    def wait_for_first_of_signals_from_multiple_queues(self, queues_to_signals: Dict[Queue, List[Signal]], timeout: int) -> Optional[Dict[str, Any]]:

        # FIXME: Probably not the right typehint, but whatever
        shared_dict: Dict[str, Any] = self.multiprocessing_manager.dict()
        queue_checkers = []
        terminate_event = Event()

        # Create a process for each queue to wait for the signal and append the message if we get one
        for queue, signals in queues_to_signals.items():
            queue_checker = Process(target=self.get_first_message_from_queue_by_signal,
                args=(queue, signals, shared_dict, terminate_event), daemon=True)

            queue_checker.start()
            queue_checkers.append(queue_checker)

        # Quit early if any started process detected the message
        time.sleep(timeout)
        # terminate_event.wait(timeout)

        # Then, wait for those processes to finish (They will all end if the message was heard or if all timeout)
        for queue_checker in queue_checkers:
            queue_checker.kill()
            queue_checker.join()

        # Once all processes end, return the message if any
        return dict(shared_dict).get("message")

    # =============================================================================
    def wait_for_signal_from_queue(self, queue, signal, timeout):
        return self.wait_for_first_of_signals_from_multiple_queues({queue: [signal]}, timeout)

    # =============================================================================
    def wait_for_signals_from_queue(self, queue, signals, timeout):
        return self.wait_for_first_of_signals_from_multiple_queues({queue: signals}, timeout)

    # =============================================================================
    # STATE FUNCTIONS START HERE
    # =============================================================================
    def start(self) -> None:

        # Randomly assign a timeout so that followers are less likely to elect themselves simultaneously
        timeout = random.randrange(RESYNC_RATE, RESYNC_RATE * 2)

        # Start adding messages to queue before we multicast our LEADERREQ
        # Then, send out a request for a leader to respond
        self.send_multicast_signal(Signal.LEADERREQ)

        # Wait here until up to timeout for the response
        message = self.wait_for_signal_from_queue(self.__message_queue, Signal.LEADERACK, timeout)

        # If the signal was detected, there's a Leader so go to Consistency state to send QUIT signals to competing leaders
        if message:
            self.__first_leader_ip: str = message["ip_address"]
            self.__state = State.CONSISTENCY
        else:
            self.__state = State.NOLEADER

        # self.__state = State.FOLLOWER

    # =============================================================================
    def consistency(self) -> None:
        timeout = DEFAULT_TIMEOUT

        message = self.wait_for_signal_from_queue(self.__message_queue, Signal.LEADERACK, timeout)

        # We kill the first leader if we get a subsequent leaderack
        # This state helps solve the problem of dueling leaders
        if message and self.__first_leader_ip:
            self.send_signal_to_ip_address(Signal.QUIT, self.__first_leader_ip)

        # Regardless of what happens, become a follower
        self.__state = State.FOLLOWER

    # =============================================================================
    def no_leader(self) -> None:
        timeout = DEFAULT_TIMEOUT

        # In this state, we become a follower if we detect any of these three signals from the general queue
        message = self.wait_for_signals_from_queue(self.__message_queue, [Signal.LEADERREQ, Signal.LEADERUP, Signal.ELECTION], timeout)

        if message:
            self.__state = State.FOLLOWER
        else:
            self.__state = State.LEADER

    # =============================================================================
    def follower(self) -> None:

        # -----------------------------------------------------------------------------
        # FIXME: Would be cool to figure out how to use typehints correctly for the class returned by multiprocessing.Event
        def handle_general_queue(safe_to_terminate, election_event):
            while True:
                safe_to_terminate.set()
                try:
                    message = self.__message_queue.get_nowait()
                except queue.Empty:
                    time.sleep(DEFAULT_CHECK_QUEUE_INTERVAL)
                    continue
                safe_to_terminate.clear()

                # Let the leader know you exist
                if message["signal"] == Signal.LEADERUP:
                    # print("We heard leaderup from leader, sending followerup in response")
                    self.send_signal_to_ip_address(Signal.FOLLOWERUP, message["ip_address"])

                # Accept the election of another follower, change state so we can refuse subsequent elections
                elif message["signal"] == Signal.ELECTION:
                    self.send_signal_to_ip_address(Signal.ACCEPT, message["ip_address"])
                    safe_to_terminate.set()
                    election_event.set()
                    return

        # -----------------------------------------------------------------------------
        # FIXME: Would be cool to figure out how to use typehints correctly for the class returned by multiprocessing.Event
        def handle_clock_sync_queue(safe_to_terminate, shared_dict: Dict[str, Any]):
            # Let the parent know the time we last heard from the leader
            shared_dict["last_leader_timestamp"] = time.time()
            while True:
                # Let the parent know its safe to terminate when we are just waiting for a message
                safe_to_terminate.set()
                try:
                    # print("Size of clock_sync_queue: %s" % self.__clock_sync_queue.qsize())
                    message = self.__clock_sync_queue.get_nowait()
                except queue.Empty:
                    time.sleep(DEFAULT_CHECK_QUEUE_INTERVAL)
                    continue
                safe_to_terminate.clear()
                # print("Received message from leader!")
                # print(message)
                shared_dict["last_leader_timestamp"] = time.time()

                # Give the leader your current clock time
                if message["signal"] == Signal.CLOCKREQ:
                    sending_message = {
                        "signal": Signal.CLOCKRESP,
                        "timestamp": time.time(),
                    }
                    print("Sending timestamp {} to leader".format(sending_message["timestamp"]))
                    self.send_message_to_ip_address(sending_message, message["ip_address"], self.clock_sync_port, self.clock_sync_sock)

                # Fix your current clock time if leader requests
                elif message["signal"] == Signal.SYNCREQ:
                    print(message)
                    self.fix_my_clock(round(float(message["adj_seconds"]), SEC_DECIMAL_ROUND))

                    # Return your current time to the leader so leader can log diffs between their clock and yours
                    # Best way to do this I guess
                    sending_message = {
                        "signal": Signal.SYNCRESP,
                        "timestamp": time.time(),
                    }
                    self.send_message_to_ip_address(sending_message, message["ip_address"])

        # The general message handler is responsible for informing the parent if the election event has happened
        election_event = Event()
        safe_to_terminate_general_queue = Event()

        general_queue_process = Process(
            target=handle_general_queue,
            args = (safe_to_terminate_general_queue, election_event), daemon=True)

        # The clock sync handler is responsible for informing the parent about the last time we heard from the leader node
        safe_to_terminate_clock_sync_queue = Event()
        shared_dict: Dict[str, Any] = self.multiprocessing_manager.dict()
        shared_dict["last_leader_timestamp"] = time.time()

        clock_sync_process = Process(
            target=handle_clock_sync_queue,
            args = (safe_to_terminate_clock_sync_queue, shared_dict), daemon=True)

        self.clear_queue(self.__clock_sync_queue)

        # Let the leader know we are following and ready for messages
        self.send_multicast_signal(Signal.FOLLOWERUP)

        general_queue_process.start()
        clock_sync_process.start()

        # FIXME: What about network latency? Should add small buffer to RESYNC_RATE probably
        # FIXME: Just added 5 seconds for now
        candidate_timeout = RESYNC_RATE + 5

        while True:
            # We wait for RESYNC_RATE amount of time for the election_event to be triggered
            election_event.wait(candidate_timeout)

            # Then, if either the election event is triggered or we didn't hear from the leader fast enough, we are done
            if election_event.is_set() or time.time() > (shared_dict["last_leader_timestamp"] + candidate_timeout):
                break

        # IF either process is still alive, then wait until its safe to terminate and do so
        if general_queue_process.is_alive():
            safe_to_terminate_general_queue.wait()
            general_queue_process.terminate()
            general_queue_process.join()

        if clock_sync_process.is_alive():
            safe_to_terminate_clock_sync_queue.wait()
            clock_sync_process.terminate()
            clock_sync_process.join()

        # This means we heard an ELECTION signal, so we are going into the ACCEPT state
        if election_event.is_set():
            self.__state = State.ACCEPT

        # Otherwise, we timed out so we are going to elect ourselves
        else:
            self.send_multicast_signal(Signal.ELECTION)
            self.__state = State.CANDIDATE

    # =============================================================================
    def accept(self) -> None:

        # -----------------------------------------------------------------------------
        # FIXME: Would be cool to figure out how to use typehints correctly for the class returned by multiprocessing.Event
        def handle_general_queue(safe_to_terminate):
            while True:
                safe_to_terminate.set()
                try:
                    message = self.__message_queue.get_nowait()
                except queue.Empty:
                    time.sleep(DEFAULT_CHECK_QUEUE_INTERVAL)
                    continue
                safe_to_terminate.clear()

                # Send REFUSE signal to any subsequent ELECTION signals
                if message["signal"] == Signal.ELECTION:
                    self.send_signal_to_ip_address(Signal.REFUSE, message["ip_address"])

                # Keep replying to LEADERUPs with FOLLOWERUPs
                elif message["signal"] == Signal.LEADERUP:
                    self.send_signal_to_ip_address(Signal.FOLLOWERUP, message["ip_address"])

        # Start a process capable of informing the parent process when its safe to terminate
        safe_to_terminate = Event()
        general_queue_process = Process(target=handle_general_queue, args=(safe_to_terminate,), daemon=True)
        general_queue_process.start()

        # Sleep for designated amount of time
        accept_timeout = DEFAULT_TIMEOUT
        time.sleep(accept_timeout)

        # Then kill the process when its safe to do so
        safe_to_terminate.wait()
        general_queue_process.terminate()
        general_queue_process.join()

        # Once we've finished the ACCEPT state, we go back to follower
        self.__state = State.FOLLOWER

    # =============================================================================
    def candidate(self) -> None:
        election_timeout = DEFAULT_TIMEOUT
        start_time = time.time()

        # -----------------------------------------------------------------------------
        # FIXME: Would be cool to figure out how to use typehints correctly for the class returned by multiprocessing.Event
        def handle_messages(safe_to_terminate, become_follower_event):

            while True:
                safe_to_terminate.set()
                try:
                    message = self.__message_queue.get_nowait()
                except queue.Empty:
                    time.sleep(DEFAULT_CHECK_QUEUE_INTERVAL)
                    continue
                safe_to_terminate.clear()

                # send ACK to any ACCEPT signals
                if message["signal"] == Signal.ACCEPT:
                    self.send_signal_to_ip_address(Signal.ACK, message["ip_address"])

                # Send REFUSE signal to any subsequent ELECTION signals
                elif message["signal"] == Signal.ELECTION:
                    self.send_signal_to_ip_address(Signal.REFUSE, message["ip_address"])

                # If another leader orders us to QUIT or a follower sends a REFUSE signal, become a FOLLOWER
                elif message["signal"] in (Signal.QUIT, Signal.REFUSE):
                    self.send_signal_to_ip_address(Signal.ACK, message["ip_address"])
                    become_follower_event.set()

        safe_to_terminate = Event()
        become_follower_event = Event()
        message_handler_process = Process(target=handle_messages, args=(safe_to_terminate, become_follower_event), daemon=True)
        message_handler_process.start()

        # Wait for this event to be set or for the timer to expire
        become_follower_event.wait(election_timeout)

        # Then kill the process when its safe to do so
        safe_to_terminate.wait()
        message_handler_process.terminate()
        message_handler_process.join()

        if become_follower_event.is_set():
            self.__state = State.FOLLOWER
        else:
            # FIXME: Decide whether to send this signal at the end of a state or at the beginning
            self.__state = State.LEADER

    # =============================================================================
    def leader(self) -> None:

        # FIXME: Would be cool to figure out how to use typehints correctly for the class returned by multiprocessing.Event

        # -----------------------------------------------------------------------------
        def fix_follower_clocks(safe_to_terminate, timeout: int, followers: List[str]) -> None:

            # -----------------------------------------------------------------------------
            def get_follower_diffs(followers: List[str]) -> Dict[str, float]:
                # Create a copy from the multiprocessing.List so we don't do anything crazy
                followers_timestamps: Dict[str, Dict[str, float]] = {f: {} for f in followers}
                for follower_ip in followers_timestamps.keys():
                    followers_timestamps[follower_ip]["t1"] = time.time()
                    print("Requesting time from follower at time {}".format(followers_timestamps[follower_ip]["t1"]))
                    self.send_signal_to_ip_address(Signal.CLOCKREQ, follower_ip, self.clock_sync_port, self.clock_sync_sock)

                followers_responded = set(followers_timestamps.keys())
                time_to_wait = DEFAULT_TIMEOUT
                time_to_wait_start = time.time()
                while followers_responded and time.time() < time_to_wait_start + time_to_wait:
                    try:
                        message = self.__clock_sync_queue.get_nowait()
                    except queue.Empty:
                        time.sleep(DEFAULT_CHECK_QUEUE_INTERVAL)
                        continue
                    ip_address = message["ip_address"]
                    if ip_address in followers_timestamps:
                        print("T1: %s " % followers_timestamps[ip_address]["t1"])
                        print("timestamp2: %s " % message["timestamp"])
                        print("T2: %s " % float(message["timestamp"]))
                        followers_timestamps[ip_address]["t2"] = float(message["timestamp"])
                        followers_timestamps[ip_address]["t3"] = time.time()
                        print("Timestamping for t3 {}".format(followers_timestamps[follower_ip]["t3"]))
                        followers_responded.remove(ip_address)

                follower_diffs: Dict[str, float] = {}
                for follower, timestamps in followers_timestamps.items():

                    if "t1" in timestamps and "t2" in timestamps and "t3" in timestamps:
                        print("Diff between t1 and t2: %s" % (timestamps["t2"] - timestamps["t1"]))
                        print("Diff between t2 and t3: %s" % (timestamps["t3"] - timestamps["t2"]))
                        clock_diff = timestamps["t2"] - ((timestamps["t1"] + timestamps["t3"]) / 2)
                        follower_diffs[follower] = clock_diff

                return follower_diffs

            # -----------------------------------------------------------------------------
            def log_follower_diffs(follower_diffs, follower_order):
                if follower_diffs and follower_order:
                    print("Gonna write to logfile...")
                    with open("logfile", "a+") as f:
                        row = ",".join(str(follower_diffs.get(follower) or "") for follower in follower_order)
                        print("Writing this row: %s" % row)
                        f.write(row + '\n')

            while True:
                print(f"Waiting for {timeout} in fix_follower_clocks...")
                safe_to_terminate.set()
                time.sleep(timeout)
                safe_to_terminate.clear()
                # Sort the followers for consistency, also make copy from multiprocessing.List to avoid craziness
                followers_as_list = list(sorted(f for f in followers))
                if not followers_as_list: continue

                follower_clock_diffs = get_follower_diffs(followers_as_list)
                log_follower_diffs(follower_clock_diffs, followers_as_list)

                # Add a 0 for the leader so average works properly
                print(follower_clock_diffs.values())
                avg_diff: float = mean(list(follower_clock_diffs.values()) + [0.0])

                # We adjust our own clock to the avg diff
                self.fix_my_clock(round(avg_diff, SEC_DECIMAL_ROUND))

                # We adjust the followers' clocks to the avg_diff - their estimated drift
                for follower, diff in follower_clock_diffs.items():
                    message_dict = {
                        "signal": Signal.SYNCREQ,
                        "adj_seconds": avg_diff - diff,
                    }
                    print(message_dict)
                    self.send_message_to_ip_address(message_dict, follower, self.clock_sync_port, self.clock_sync_sock)

                # When done fixing all clocks, log the diffs again so we can plot the pre-fixed time with the fixed time
                time.sleep(DEFAULT_TIMEOUT)
                log_follower_diffs(get_follower_diffs(followers_as_list), followers_as_list)

        def handle_messages(followers: List[str], state_change_dict: Dict[str, State]):

            while True:
                # Handle messages in the message queue while sync process running
                try:
                    message = self.__message_queue.get_nowait()
                except queue.Empty:
                    time.sleep(DEFAULT_CHECK_QUEUE_INTERVAL)
                    continue

                print("We got a message!")
                print(message)
                # We broadcasted LEADERUP to all followers, so they should have replied with FOLLOWERUP so we can
                # record their ip addresses to contact them
                if message["signal"] == Signal.FOLLOWERUP and message["ip_address"] not in followers:
                    print("Adding follower...")
                    followers.append(message["ip_address"])

                if message["signal"] == Signal.LEADERREQ:
                    self.send_signal_to_ip_address(Signal.LEADERACK, message["ip_address"])

                elif message["signal"] == Signal.RESOLVE:
                    self.send_signal_to_ip_address(Signal.LEADERACK, message["ip_address"])

                # Tell those nodes that multicast ELECTION to go back to follower
                elif message["signal"] == Signal.ELECTION:
                    self.send_signal_to_ip_address(Signal.QUIT, message["ip_address"])

                # Leader nodes will tell us their current time right after they fix their clocks, so log the diffs
                elif message["signal"] == Signal.SYNCRESP:
                    leader_time = time.time()
                    follower_time = round(float(message["timestamp"]), SEC_DECIMAL_ROUND)

                # If another leader tells this node to quit, node acknowledges and goes to FOLLOWER state
                elif message["signal"] == Signal.QUIT:
                    # FIXME: It's on the state diagram, but doesn't seem like ACK is handled by anything
                    # Is this for some retransmission purpose that I'm not implementing?
                    self.send_signal_to_ip_address(Signal.ACK, message["ip_address"])
                    state_change_dict["state"] = State.FOLLOWER
                    break

                # If we hear a conflict message, we go to CONFLICT state
                elif message["signal"] == Signal.CONFLICT:
                    self.send_multicast_signal(Signal.RESOLVE)
                    state_change_dict["state"] = State.CONFLICT
                    break

        safe_to_terminate = Event()
        followers: List[str] = self.multiprocessing_manager.list()
        state_change_dict: Dict[str, State] = self.multiprocessing_manager.dict()

        handle_messages_process = Process(target=handle_messages, args=(followers, state_change_dict), daemon=True)
        handle_messages_process.start()

        self.send_multicast_signal(Signal.LEADERUP)
        fix_follower_clocks_process = Process(target=fix_follower_clocks, args=(safe_to_terminate, RESYNC_RATE, followers), daemon=True)
        fix_follower_clocks_process.start()

        handle_messages_process.join()

        safe_to_terminate.wait()
        fix_follower_clocks_process.terminate()
        fix_follower_clocks_process.join()

        # FIXME: Maybe this is a tad paranoid? I could just reassign state only if a state is present
        if not isinstance(state_change_dict.get("state"), State):
            raise Exception("Something went wrong! We exited the leader state without entering a new one!")

        self.__state = state_change_dict["state"]

    # =============================================================================
    def conflict(self) -> None:

        # When we enter the conflict state, broadcast RESOLVE so that other leaders reply with LEADERACK
        timeout = DEFAULT_TIMEOUT

        # We wait here for a signal from a leader
        message = self.wait_for_signal_from_queue(self.__message_queue, Signal.LEADERACK, timeout)
        if message:
            # Kill the other leader, then go back to LEADER state
            self.send_signal_to_ip_address(Signal.QUIT, message["ip_address"])

        self.send_multicast_signal(Signal.LEADERUP)
        self.__state = State.LEADER

# ============================================================================
def main():
    # args = sys.argv[1:]
    # TimeDaemon(*args).run()
    TimeDaemon().run()

    # Testing Messenger

    # multicaster = Messenger(int(sys.argv[1]))
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
    #     multicaster.send_multicast_signal(Signal.LEADERACK)
    # else:
    #     raise Exception("Only testing two ports right now")

if __name__ == "__main__":
    main()
