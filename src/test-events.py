import threading
from time import sleep
import sys

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
        signal = input("-->")
        if signal == "MasterAck":
            handler_event.set()
            break
    sys.exit()

if __name__ == "__main__":

    # Create our event object
    e = MyCustomEvent()

    # Create thread of execution, waiting for ten seconds for the e.set() to be called
    thread1 = MyThread(name="Waiting-For-Master-Ack", target=master_ack_handler, kwargs={"event": e, "timeout": 10})
    thread1.start()

    # listen for signals while thread1 is alive. If right signal shows up before thread1 terminates, call e.set()
    thread2 = MyThread(name="Listening-for-Master-Ack", target=listening_for_master_ack, kwargs={"handler_event": e})
    thread2.start()

    thread2.stop_when_thread_ends(thread1)

