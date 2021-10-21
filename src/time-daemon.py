
from enum import Enum



# What we need to implement

# We need to implement a way of manage being in different *states* and transitioning to those states
	# Each state transition happens because of events, of which there are two types: (1) the receipt of a message or (2) the expiration of a timer
# So, each daemon needs to have a thread listening for messages broadcasted from other nodes

RESYNC_RATE = 10

# There are a finite number of states, so can just use ENUM to reduce errors
class State(Enum):
	START = 1
	NOMASTER = 2
	MASTER = 3
	SLAVE = 4
	CONSISTENCY = 5
	CONFLICT = 6
	ACCEPT = 7
	CANDIDATE = 8

# Do we want to define an ENUM for all the valid messages as well?
class Signal(Enum):
	pass

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


class MulticastSender()

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

class MulticastReceiver():

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




class TimeDaemon():
	def __init__(self) -> None:
		self.__state = State.START

	# Create a thread listening for broadcasts
	# How will this thread interrupt execution of other threads?
	# figure this out. Each state needs to be able to respond to
	# messages this listener picks up
	def __listen_for_broadcasts(self):
		pass

	def run(self) -> None:
		self.__listen_for_broadcasts()
		self.__change_state(State.Start)

	def __change_state(self, state: State) -> None:
		self.__state = state
		if self.__state == State.START:
			self.start()
		elif self.__state == State.NOMASTER:
			self.no_master()
		elif self.__state == State.MASTER:
			self.master()
		elif self.__state == State.SLAVE:
			self.slave()
		elif self.__state == State.CONSISTENCY:
			self.consistency()
		elif self.__state == State.CONFLICT:
			self.conflict()
		elif self.__state == State.ACCEPT:
			self.accept()
		elif self.__state == State.CANDIDATE:
			self.candidate()

	# =============================================================================
	# Utility Functions here
	# =============================================================================
	def broadcast(self, message_parts):
		message = TSPMessage(**message_parts)
		message_as_bytes = message.create_message()

		# Broadcasts message to all nodes
		pass

	def get_local_clock_time(self):
		# Return the local clock time by using the local clock utility
		pass

	def set_clock(self, second_adjustments, microsecond_adjustments):
		# Fix clock by applying second_adjustments and microsecond_adjustments
		pass

	def __listen_for_broadcasts(self, signal: Signal, wait_time: int):
		pass

	# =============================================================================
	# State Functions here
	# =============================================================================
	def start(self) -> None:
		pass
		# StartUp:
		# Randomly assign R, where RESYNC_RATE < R < 2 * RESYNC_RATE
		# Broadcast Masterreq to inform Master that a new Slave exists
		# Starts timer startup_timer
		# If startup_timer expires, move to NoMaster state
		# If Masterack received, move to Consistency state

	def no_master(self) -> None:
		pass
		# NoMaster:
		# Start no_master_timer
		# If no_master_timer expires, move to Master state and broadcast Masterup message
		# If receive MasterUp, MasterReq, or Election message, move to Slave state

	def candidate(self) -> None:
		pass
		# Candidate:
		# Start candidate_timer
		# If timer expires, move to Master state and broadcast Masterup signal
		# If receives Election message, reply with Refuse message
		# If received Accept message, reply with Ack message

	def master(self) -> None:
		pass
		# Master:
		# Start master_sync_timer
		# When master_timer expires, broadcasts Clockreq message to all slaves in its list of names
		# When Clockresp is received from all slaves in list, computes adjustments and sends SyncReq to all slaves
		# When Masterreq received, records slave name in its list of names, send Masterack back to slave
		# If master receives Conflict message from a slave after sending a Masterack, it moves to the Conflict State and broadcasts Resolve message
		# If master receives Resolve message from another node, it replies to sender with Masterack
		# If receive Quit message from a node, move to Slave state and respond with Ack message

	def consistency(self) -> None:
		pass

		# Consistency:
		# Starts consistency_timer
		# If constency_timer expires, moves to Slave state
		# If receives Masterack from another node, it sends a Conflict message to the first master node and immediately moves to Slave state of the second master. 
		# This is a way of allowing a slave to fix a situation where two machines have decided they are masters

	def conflict(self) -> None:
		pass

		# Conflict:
		# Broadcast “Resolve” message
		# Starts conflict_timer
		# If conflict_timer expires, broadcast Masterup message and move to Master state
		# If receives Masterack from a node in response to Resolve message, send back a Quit message

	def slave(self) -> None:
		pass

		# Slave:
		# Start election_timer (timer counts up to value R determined in startup state)
		# If election_timer expires, move to Election state and broadcast Election message
		# If receives Masterup message, replies with Slaveup message
		# If receives Clockreq message, replies with Clockresp message
		# If receives SyncReq message, replies with SyncResp message
		# If receives Election message, reply with Accept message and move to Accept state

	def accept(self) -> None:
		pass

		# Accept:
		# Start accept_timer
		# If accept_timer expires, move back to Slave state
		# If receive Masterup message, reply with Slaveup message
		# If receive Election message, reply with Refuse message

def main():
	TimeDaemon().run()

if __name__ == "__main__":
	main()
