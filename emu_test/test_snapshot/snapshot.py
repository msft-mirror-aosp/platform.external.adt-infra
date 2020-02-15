"""
Contains a SnapshotService that can talk to the emulator snapshot service on the given grpc port.
"""
import logging
import os

import grpc
from google.protobuf import empty_pb2

from emu_test.proto.snapshot_service_pb2 import SnapshotPackage
from emu_test.proto.snapshot_service_pb2_grpc import SnapshotServiceStub
from emu_test.test_snapshot.channel_provider import getEmulatorChannel

_EMPTY_ = empty_pb2.Empty()


class SnapshotService(object):
    """A SnapshotService can be used to manipulate snapshots in the emulator."""

    def __init__(self, port, logger=logging.getLogger()):
        """Connect to the emulator on the given port, and log on the given logger."""
        self.channel = getEmulatorChannel(port)
        self.stub = SnapshotServiceStub(self.channel)
        self.logger = logger

    def _exec_unary_grpc(self, method, req):
        """Executes the given request on the service endpoint with the provided parameter,

        Returns: True on success, or False otherwise.
        """
        self.logger.debug("Executing %s(%s)", method, req)
        method_to_call = getattr(self.stub, method)
        try:
            msg = method_to_call(req)
            self.logger.debug("Response %s", msg)
            if not msg.success:
                self.logger.error("Failed to load snapshot: %s", msg.err)
            return msg.success
        except grpc._channel._Rendezvous as err:
            self.logger.error("Low level grpc error: %s ", err)

        return False

    def pull(self, snap_id, dest):
        """Pulls a snapshot with the given id to the given destination dir as id.tar.gz."""
        fname = os.path.join(dest, snap_id + ".tar.gz")
        self.logger.debug("Pulling %s -> %s", snap_id, fname)
        try:
            it = self.stub.PullSnapshot(SnapshotPackage(snapshot_id=snap_id))
            with open(fname, "wb") as fn:
                for msg in it:
                    if not msg.success:
                        self.logger.error("Failed to pull snapshot: %s", msg.err)
                        return False
                    fn.write(msg.payload)
        except grpc._channel._Rendezvous as err:
            self.logger.error("Low level grpc error: %s ", err)
        self.logger.debug("Response %s", msg)
        return msg and msg.success

    def push(self, src):
        """Pushes a snapshot from the given src (tar.gz) as 'snap_id'.tar.gz
        
        The snap_id.tar.gz should have a snaphost that has the id: snap_id.
        So foo.tar.gz should contain the snapshot named 'foo'.
        """

        def read_in_chunks(file_object, chunk_size=(256 * 1024)):
            """Ye olde python chunk reader.
            """
            while True:
                data = file_object.read(chunk_size)
                if not data:
                    break
                yield data

        def push_snap_iterator(fname):
            """An iterator that returns:

            1. A message containing only the id.
            2. A stream of byte objects from the tar.gz file.
            """
            snap_id = os.path.basename(fname).replace(".tar.gz", "")
            yield SnapshotPackage(snapshot_id=snap_id)
            with open(fname, "rb") as snap:
                for chunk in read_in_chunks(snap):
                    yield SnapshotPackage(payload=chunk)

        return self._exec_unary_grpc("PushSnapshot", push_snap_iterator(src))

    def lists(self):
        """Lists all available snapshots."""
        self.logger.debug("Retrieving snapshots")
        response = self.stub.ListSnapshots(_EMPTY_)
        self.logger.debug("Response %s", response)
        return [f.snapshot_id for f in response.snapshots]

    def load(self, snap_id):
        """Loads a snapshot inside the emulator."""
        return self._exec_unary_grpc("LoadSnapshot", SnapshotPackage(snapshot_id=snap_id))

    def save(self, snap_id):
        """Saves a snapshot inside the emulator."""
        return self._exec_unary_grpc("SaveSnapshot", SnapshotPackage(snapshot_id=snap_id))

    def delete(self, snap_id):
        """Deletes the given snapshot from the emulator."""
        return self._exec_unary_grpc("DeleteSnapshot", SnapshotPackage(snapshot_id=snap_id))
