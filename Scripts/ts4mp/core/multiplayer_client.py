import socket
import threading

import ts4mp
from ts4mp.debug.log import ts4mp_log
from ts4mp.core.mp_essential import outgoing_lock, outgoing_commands
from ts4mp.core.networking import generic_send_loop, generic_listen_loop, socket_lock
from ts4mp.configs.server_config import HOST, PORT
from ts4mp.core.mp_essential import incoming_lock


class Client:
    def __init__(self):
        with socket_lock:
            self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serversocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.host = HOST
        self.port = PORT
        self.alive = True
        # self.host = "192.168.1.23"
        # self.port = 9999
        self.connected = False

    def listen(self):
        threading.Thread(target=self.listen_loop, args=[]).start()

    def send(self):
        threading.Thread(target=self.send_loop, args=[]).start()

    def send_loop(self):
        while self.alive:
            try:
                ts4mp_log("locks", "acquiring socket lock")

                with socket_lock:
                    self.serversocket.connect((self.host, self.port))
                ts4mp_log("locks", "releasing socket lock")

                self.connected = True
            except:
                # server isn't online
                pass

            while self.alive:
                try:
                    ts4mp_log("locks", "acquiring outgoing lock")

                    with outgoing_lock:
                        for data in outgoing_commands:
                            generic_send_loop(data, self.serversocket)
                            outgoing_commands.remove(data)
                    ts4mp_log("locks", "releasing outgoing lock")

                except OSError as e:
                    ts4mp_log("locks", "acquiring incoming and outgoing lock")

                    outgoing_lock.acquire()
                    incoming_lock.acquire()

                    self.__init__()

                    outgoing_lock.release()
                    incoming_lock.release()

                    ts4mp_log("locks", "releasing incoming and outgoing lock")

                    ts4mp_log("network", "Network disconnect")

                    break

            # time.sleep(1)

    def listen_loop(self):
        while self.alive:

            serversocket = self.serversocket
            size = None
            data = b''

            while self.alive:
                try:
                    if self.connected:
                        new_command, data, size = generic_listen_loop(serversocket, data, size)
                        if new_command is not None:
                            with incoming_lock:
                                ts4mp.core.mp_essential.incoming_commands.append(new_command)
                    # time.sleep(1)
                except OSError as e:
                    outgoing_lock.acquire()
                    incoming_lock.acquire()

                    self.__init__()

                    outgoing_lock.release()
                    incoming_lock.release()

                    ts4mp_log("network", "Network disconnect")

                    break

    def kill(self):
        self.alive = False
