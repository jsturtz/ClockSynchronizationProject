import os
from multiprocessing import Process
import time
import sys

def main():
    def print_after_time(t, multiplier):
        os.environ["FAKETIME"] = f'+0s x{multiplier}'
        time.sleep(t)
        return

    if len(sys.argv) != 3:
        raise Exception("Wrong number of args!")

    t, m = sys.argv[1:]
    t = int(t)

    p = Process(target=print_after_time, args=(t, m))
    p.start()

    start_time = time.time()
    p.join()
    time_diff = int(time.time() - start_time)

    print(f"{t} seconds on {m} multiplier took {time_diff} seconds")

if __name__ == '__main__':
    main()
