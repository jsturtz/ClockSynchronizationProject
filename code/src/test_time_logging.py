import threading
import multiprocessing
import os
import time
import socket


with open("logfile.csv", "w+") as f:
    f.truncate()

time_logging_port = 1002
my_ip_address = socket.gethostbyname(socket.gethostname())

time_logging_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
time_logging_sock.bind((my_ip_address, time_logging_port))
time_logging_sock.listen()

def recv_from_client(conn, ip_address):
    while True:
        their_time = conn.recv(1024).decode("utf-8")
        real_time = time.time()
        if not their_time:
            break
        with open("logfile.csv", 'a+') as f:
            print(f"Writing this line to the file: {ip_address},{real_time},{their_time}")
            f.write(f"{ip_address},{real_time},{their_time}\n")

# Accept connections from clients
while True:
    conn, addr = time_logging_sock.accept()
    print(f"Accepting connection from {addr[0]}")
    # Pass the work of communicating with that client off to a separate thread
    thread = threading.Thread(target=recv_from_client, args=(conn, addr[0]), daemon=True)
    thread.start()

# def main():
#     os.environ["FAKETIME"] = '+0s x2'

#     def log_time_diffs():

#         while True:
#             time.sleep(2)
#             def get_real_time(shared_dict):
#                 os.environ.pop("FAKETIME")
#                 shared_dict["real_time"] = time.time()

#             shared_dict = multiprocessing.Manager().dict()
#             real_time_process = multiprocessing.Process(target=get_real_time, args=(shared_dict,), daemon=True)
#             real_time_process.start()
#             real_time_process.join()
#             print("FAKETIME: %s" % os.environ["FAKETIME"])
#             real_time = shared_dict["real_time"]
#             fake_time = time.time()

#             print(f"Writing this: {real_time},{fake_time}\n")
#             # with open("logfile.csv", "a+") as f:
#             #     f.write(f"{real_time},{fake_time}\n")

#     log_time_diff_thread = threading.Thread(target=log_time_diffs, daemon=True)
#     log_time_diff_thread.start()
#     log_time_diff_thread.join()

# if __name__ == '__main__':
#     main()

# time.sleep(300)
# import threading
# import multiprocessing
# import os
# import time
# import socket

# with open("logfile.csv", "w+") as f:
#     f.truncate()

# time_logging_port = 1002
# my_ip_address = socket.gethostbyname(socket.gethostname())

# time_logging_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# time_logging_sock.bind((my_ip_address, time_logging_port))
# time_logging_sock.listen()

# def recv_from_client(conn, ip_address):
#     while True:
#         their_time = conn.recv(1024).decode("utf-8")
#         real_time = time.time()
#         if not their_time:
#             break
#         with open("logfile.csv", 'a+') as f:
#             print(f"Writing this line to the file: {ip_address},{real_time},{their_time}")
#             f.write(f"{ip_address},{real_time},{their_time}\n")

# # Accept connections from clients
# while True:
#     conn, addr = time_logging_sock.accept()
#     print(f"Accepting connection from {addr[0]}")
#     # Pass the work of communicating with that client off to a separate thread
#     thread = threading.Thread(target=recv_from_client, args=(conn, addr[0]), daemon=True)
#     thread.start()

