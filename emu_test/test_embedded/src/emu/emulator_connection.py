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

"""A Connection to the emulator telnet console.
"""




import socket
import signal
import time
import datetime
import logging
from threading import Thread


class EmulatorConnection(object):
    """Connects to the emulator telnet console.

  It will authenticate immediately.
  """

    def __init__(self, transport, callback):
        self.callback = callback
        self.start = time.time()
        self.transport = transport
        self.connected = False
        self.fstmsg = ""

    def is_connected(self):
        return self.connected

    def auth(self, fname):
        logging.info("Authenticating using %s", fname)
        with open(fname[1:-1], "r") as authfile:
            token = authfile.read()
            msg = "auth {}".format(token).strip()
            self.connected = True
            self.send(msg)

    def data_received(self, data):
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
        total = time.time() - self.start
        logging.error(
            "The emulator is gone, we were alive for: %d seconds (%s)!",
            total,
            str(datetime.timedelta(seconds=total)),
        )
        self.connected = False

    def reader(self):
        data = self.transport.recv(4096)
        try:
            while data:
                self.data_received(data)
                data = self.transport.recv(4096)
        except:
            self.connection_lost()

    def send(self, msg):
        """Sends plain text to the emulator"""
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
        self.transport.close()


    @staticmethod
    def connect(port, callback=None):
        """Connects to the telnet console on the given port and authenticates.

    Args:
      port:     The port to which to connect to the emulator.
      callback: Function to be called when the telnet console has data

    Returns:
      Thread that is running the event loop
    """
        sock = socket.create_connection(("localhost", port))
        connection = EmulatorConnection(sock, callback)
        t = Thread(target=connection.reader)
        t.start()
        signal.signal(signal.SIGINT, lambda: connection.stop())
        return connection
