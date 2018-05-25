import socket
import threading

import ts4mp
import ts4mp.core.mp_essential
from ts4mp.debug.log import ts4mp_log
from ts4mp.core.mp_essential import outgoing_lock
from ts4mp.core.mp_essential import incoming_lock
from ts4mp.core.networking import generic_send_loop, generic_listen_loop, socket_lock
from ts4mp.configs.server_config import HOST, PORT

class Server:
    def __init__(self):
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.host = HOST
        self.port = PORT
        self.alive = True
        self.serversocket.bind((self.host, self.port))
        ts4mp_log("locks", "acquiring socket lock")

        with socket_lock:
            self.clientsocket = None
        ts4mp_log("locks", "releasing socket lock")

    def listen(self):
        threading.Thread(target=self.listen_loop, args=[]).start()

    def send(self):
        threading.Thread(target=self.send_loop, args=[]).start()

    def send_loop(self):
        while self.alive:

            with socket_lock:
                if self.clientsocket is not None:
                    with outgoing_lock:
                        try:
                            for data in ts4mp.core.mp_essential.outgoing_commands:
                                generic_send_loop(data, self.clientsocket)
                                ts4mp.core.mp_essential.outgoing_commands.remove(data)
                        except OSError as e:
                            ts4mp_log("network", "{}".format(e))
                            self.__init__()

            # time.sleep(1)

    def listen_loop(self):
        while self.alive:
            ts4mp_log("network", "Listening for clients")

            self.serversocket.listen(5)

            clientsocket, address = self.serversocket.accept()

            ts4mp_log("network", "Client Connect")

            with socket_lock:
                self.clientsocket = clientsocket

            size = None
            data = b''

            while self.alive:
                try:
                    new_command, data, size = generic_listen_loop(clientsocket, data, size)
                    if new_command is not None:
                        with incoming_lock:
                            ts4mp.core.mp_essential.incoming_commands.append(new_command)

                except OSError as e:
                    # ts4mp_log("network", "{}".format(e))
                    break

    def kill(self):
        self.alive = False

