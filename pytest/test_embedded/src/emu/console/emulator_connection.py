#!/usr/bin/env python
#
# Copyright 2018 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import datetime
import logging
import signal
import socket
import time
from threading import Thread


class EmulatorConnection(object):
    """Connects to the emulator telnet console.

    It will authenticate immediately.
    """

    def __init__(self, transport, callback, port):
        self.callback = callback
        self.start = time.time()
        self.transport = transport
        self.connected = False
        self.fstmsg = ""
        self.port = port

    def is_connected(self):
        """True if connected

        Returns:
            Bool: True if connected
        """
        return self.connected

    def auth(self, fname):
        """Authenticates the user by sending the token in fname

        Args:
            fname (str): Path to the file containing the token.
        """
        logging.info("Authenticating using %s", fname)
        with open(fname[1:-1], "r") as authfile:
            token = authfile.read()
            msg = "auth {}".format(token).strip()
            self.connected = True
            self.send(msg)

    def _data_received(self, data):
        """Called whenever data has been read from the telnet console

        It will:
           - Authorize if needed.
           - Invoke the callback with the received data.

        Args:
            data (bytes): Data received from the socket
        """
        msg = data.decode()
        logging.info("Recv: %s", msg)
        # send the auth token if needed
        if self.fstmsg is not None:
            self.fstmsg += msg
            if (
                "OK" in self.fstmsg
                and "Android Console: you can find your <auth_token> in" in self.fstmsg
            ):
                lines = [x.strip() for x in self.fstmsg.split("\n")]
                fname = lines[lines.index("OK") - 1]
                self.fstmsg = None
                self.auth(fname)

        # do something with the received data
        if self.callback:
            self.callback(msg)

    def connection_lost(self):
        """Called whenever the socket connection is dropped.
        """
        total = time.time() - self.start
        logging.error(
            "The emulator is gone, we were alive for: %d seconds (%s)!",
            total,
            str(datetime.timedelta(seconds=total)),
        )
        self.connected = False

    def reader(self):
        """Reader thread that received bytest from the emulator and passes it
           on the receiver function.
        """
        data = self.transport.recv(4096)
        try:
            while data:
                self._data_received(data)
                data = self.transport.recv(4096)
        except:
            self.connection_lost()

    def send(self, msg):
        """Sends plain text to the emulator

        Args:
            msg (str): The ASCII msg to send over the telnet consle

        Returns:
            Bool: True if the connection is still open.
        """
        if self.connected:
            logging.info("Sending %s", msg)
            try:
                self.transport.sendall("{}\n".format(msg).encode())
            except:
                # Likely got disconnected.
                return False
        else:
            logging.info("Dropping %s", msg)
        return self.connected

    def stop(self):
        """Closes the transport, and stops the reader thread."""
        self.transport.close()

    @staticmethod
    def connect(port, callback=None):
        """Connects to the telnet console on the given port and authenticates.

        Args:
            port (int): The port to which to connect to the emulator.
            callback (_type_, optional): Function to be called when the telnet console has data. Defaults to None.

        Returns:
            Thread:  Thread that is running the event loop
        """
        sock = socket.create_connection(("localhost", port))
        connection = EmulatorConnection(sock, callback, port)
        t = Thread(target=connection.reader)
        t.start()
        signal.signal(signal.SIGINT, lambda: connection.stop())
        return connection
