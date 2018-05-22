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

            while self.alive:
                try:
                    ts4mp_log("locks", "acquiring outgoing lock")

                    with outgoing_lock:
                        for data in outgoing_commands:
                            generic_send_loop(data, self.serversocket)
                            outgoing_commands.remove(data)
                    ts4mp_log("locks", "releasing outgoing lock")

                except OSError as e:
                    break

            # time.sleep(1)

    def listen_loop(self):
        while self.alive:
            while not self.connected:
                try:
                    ts4mp_log("client", "attempting to connect to server")
                    self.serversocket.connect((self.host, self.port))
                    ts4mp_log("client", "connected to server")

                    self.connected = True
                except:
                    # server isn't online
                    pass

            serversocket = self.serversocket
            size = None
            data = b''

            while self.alive:
                ts4mp_log("client", "Attempting to listen...")
                try:
                    if self.connected:
                        ts4mp_log("client", "Client is connected")

                        new_command, data, size = generic_listen_loop(serversocket, data, size)
                        if new_command is not None:
                            ts4mp_log("client", "New command received")

                            with incoming_lock:
                                ts4mp.core.mp_essential.incoming_commands.append(new_command)
                    else:
                        ts4mp_log("client", "Client is not connected")

                    # time.sleep(1)
                except OSError as e:
                    self.__init__()

                    ts4mp_log("network", "Network disconnect")

                    break

    def kill(self):
        self.alive = False
