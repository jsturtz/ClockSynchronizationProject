import threading
from time import sleep
import sys
import multiprocessing

# We can create our own custom event classes like this
class MyCustomEvent(threading.Event):
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
class MyThread(StoppableThread):

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

# Then, we can define a task we want a thread to perform while waiting for the event to be triggered
def master_ack_handler(event, timeout):
    print("Waiting for event...")
    event_set = event.wait(timeout)
    if event_set:
        print("Event was triggered!")
    else:
        print("Timeout, exiting")
    sys.exit()

# Then, we can define a task we want a thread to perform while waiting for the event to be triggered
def listening_for_master_ack(handler_event: MyCustomEvent):

    while True:
        signal = "MasterAcks"
        if signal == "MasterAck":
            handler_event.set()
            break
    sys.exit()

if __name__ == "__main__":

    # # Create our event object to be shared across processes
    # e = multiprocessing.Event()

    # # The first thread will wait for the event to be set to do something if set before timeout expires
    # w1 = multiprocessing.Process(name='WaitingForMasterAck', 
    #                              target=master_ack_handler,
    #                              kwargs={"event": e, "timeout": 10})
    # w1.start()

    # # The second thread will trigger the event, e, if MasterAck heard from stdin
    # w2 = multiprocessing.Process(name='ListeningForMasterAck', 
    #                              target=listening_for_master_ack,
    #                              kwargs={"handler_event": e})
    # w2.start()

    # # Wait for w1 to finish, which is guaranteed to exit
    # w1.join()

    # # When w1 is done, kill w2
    # w2.terminate()

    e = multiprocessing.Event()

    # Create thread of execution, waiting for ten seconds for the e.set() to be called
    thread_to_handle_signal = MyThread(name="Waiting-For-Master-Ack", target=master_ack_handler, kwargs={"event": e, "timeout": 10})

    # listen for signals while thread1 is alive. If right signal shows up before thread1 terminates, call e.set()
    thread2 = MyThread(name="Listening-for-Master-Ack", target=listening_for_master_ack, kwargs={"handler_event": e})
    thread2.start()

    # thread2.stop_when_thread_ends(thread1)

# import multiprocessing
# import time

# def wait_for_event(e):
#     """Wait for the event to be set before doing anything"""
#     print 'wait_for_event: starting'
#     e.wait()
#     print 'wait_for_event: e.is_set()->', e.is_set()

# def wait_for_event_timeout(e, t):
#     """Wait t seconds and then timeout"""
#     print 'wait_for_event_timeout: starting'
#     e.wait(t)
#     print 'wait_for_event_timeout: e.is_set()->', e.is_set()


# if __name__ == '__main__':
#     e = multiprocessing.Event()
#     w1 = multiprocessing.Process(name='block', 
#                                  target=wait_for_event,
#                                  args=(e,))
#     w1.start()

#     w2 = multiprocessing.Process(name='non-block', 
#                                  target=wait_for_event_timeout, 
#                                  args=(e, 2))
#     w2.start()

#     print 'main: waiting before calling Event.set()'
#     time.sleep(3)
#     e.set()
#     print 'main: event is set'