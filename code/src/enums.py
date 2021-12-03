
from enum import Enum

# There are a finite number of states, so can just use ENUM to reduce errors
class State(Enum):
	START = 1
	NOLEADER = 2
	LEADER = 3
	FOLLOWER = 4
	CONSISTENCY = 5
	CONFLICT = 6
	ACCEPT = 7
	CANDIDATE = 8

# There are a finite number of signals, so can just use ENUM to reduce errors
class Signal(Enum):
	LEADERREQ = 1
	LEADERACK = 2
	LEADERUP = 3
	ELECTION = 4