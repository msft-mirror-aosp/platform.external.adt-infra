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
import socket
import time
from threading import Condition, Thread
from typing import Callable, Optional


class EmulatorConnection:
    """
    Connects to the emulator telnet console and authenticates.

    The class is designed to handle the telnet connection to an emulator, it
    has methods for reading and writing to the connection.
    """

    def __init__(
        self,
        logger: logging.Logger,
        cv: Condition,
        transport: socket.socket,
        callback: Callable,
        port: int,
    ):
        """Initializes the EmulatorConnection object.

        Args:
            logger (logging.Logger): The logger used to write logging information
            cv (Condition): Condition variable to synchronize access to the connection.
            transport (socket.socket): The transport to be used for communication.
            callback (Callable): A callable object to be called whenever data is
                    received from the telnet console.
            port (int): The port to connect to the emulator.
        """
        self.cv = cv
        self.callback = callback
        self.start = time.time()
        self.transport = transport
        self.connected = False
        self.fstmsg = ""
        self.port = port
        self.logger = logger

    def is_connected(self) -> bool:
        """Checks if the connection to the emulator is active.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self.connected

    def auth(self, fname: str):
        """Authenticates to the emulator.

        Sends the authentication token to the emulator.

        Args:
            fname (str): The file path to the file
                containing the authentication token.
        """
        self.logger.info("Authenticating using %s", fname)
        with open(fname[1:-1], "r") as authfile:
            token = authfile.read()
            msg = "auth {}".format(token).strip()
            self._set_connected(True)
            self.send(msg)

    def _set_connected(self, connected: bool):
        """Sets the connection status to the emulator.

        Args:
            connected (bool): True if connected, False otherwise.
        """
        self.logger.debug("_set_connected: %s", connected)
        with self.cv:
            self.connected = connected
            self.logger.info("_set_connected: %s notify listeners", connected)
            self.cv.notify()

    def _data_received(self, data: bytes):
        """Handles the data received from the emulator.

        Sends the authentication token if required and invokes
        the callback with the received data.

        Args:
            data (bytes): Data received from the emulator.
        """
        msg = data.decode()
        self.logger.info("Recv: %s", msg)
        # send the auth token if needed
        if self.fstmsg is not None:
            self.fstmsg += msg
            if "OK" in self.fstmsg:
                if "Android Console: you can find your <auth_token> in" in self.fstmsg:
                    lines = [x.strip() for x in self.fstmsg.split("\n")]
                    fname = lines[lines.index("OK") - 1]
                    self.auth(fname)
                else:
                    self._set_connected(True)
                self.fstmsg = None

        # do something with the received data
        if self.callback:
            self.callback(msg)

    def connection_lost(self):
        """Called whenever the socket connection is dropped."""
        total = time.time() - self.start
        self.logger.error(
            "The emulator is gone, we were alive for: %d seconds (%s)!",
            total,
            str(datetime.timedelta(seconds=total)),
        )
        self._set_connected(False)

    def reader(self):
        """Reader thread that received bytest from the emulator and passes it
        on the receiver function.
        """
        data = self.transport.recv(4096)
        try:
            while data:
                self._data_received(data)
                data = self.transport.recv(4096)
        finally:
            self.connection_lost()

    def send(self, msg):
        """Sends plain text to the emulator

        Args:
            msg (str): The ASCII msg to send over the telnet consle

        Returns:
            Bool: True if the connection is still open.
        """
        if self.connected:
            self.logger.info("Sending %s", msg)
            try:
                self.transport.sendall("{}\n".format(msg).encode())
            except:
                # Likely got disconnected.
                return False
        else:
            self.logger.info("Dropping %s", msg)
            return False

        return self.connected

    def stop(self):
        """Closes the transport, and stops the reader thread."""
        if self.connected:
            self.logger.warning("Closing transport")
            self.transport.close()

    @staticmethod
    def connect(
        port: int,
        emulator_name: Optional[str] = None,
        callback: Optional[Callable] = None,
    ):
        """Connects to the telnet console on the given port and authenticates.

        Args:
            port (int): The port to connect to the emulator.
            emulator_name (str, optional): The name of the emulator. Defaults to "port-{port}".
            callback (callable, optional): Function to be called when the telnet console has data. Defaults to None.

        Returns:
            EmulatorConnection: The actual connection to the emulator
        """

        if not emulator_name:
            emulator_name = f"port-{port}"
        logger = logging.getLogger(f"{emulator_name}-con")

        sock = socket.create_connection(("localhost", port))
        connection = EmulatorConnection(logger, Condition(), sock, callback, port)

        logger.debug("Connecting to console..")
        with connection.cv:
            Thread(target=connection.reader).start()
            connection.cv.wait(5.0)

        logging.info(
            "Connected: %s to emulator on port: %s", connection.is_connected(), port
        )
        return connection
