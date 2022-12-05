# Copyright 2020 The Android Open Source Project
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
import io
import logging
import re
import time
from queue import Queue
from threading import Thread

import google.protobuf.text_format
import grpc
from PIL import Image as PillowImage
from aemu.proto.emulator_controller_pb2 import Image, ImageFormat


def proto_to_pillow(image: Image) -> PillowImage:
    """Converts an emulator protobuf image to a Pillow Image

    Args:
        image (Image): An image obtained from the screenShot api.

    Returns:
        PillowImage: A Pillow Image
    """
    EMU_TO_PIL_IMAGE_FORMATS = {
        ImageFormat.RGB888: "RGB",
        ImageFormat.RGBA8888: "RGBA",
        ImageFormat.PNG: "PNG",
    }

    if image.format.format == ImageFormat.PNG:
        return PillowImage.open(io.BytesIO(image.image))
    return PillowImage.frombytes(
        EMU_TO_PIL_IMAGE_FORMATS[image.format.format],
        (image.format.width, image.format.height),
        image.image,
    )


def fmt_proto(msg):
    """Formats a protobuf message as a single line."""
    return google.protobuf.text_format.MessageToString(msg, as_one_line=True)


def time_to_str(epoch_in_seconds):
    """Formats an epoch time in seconds into a human readable string."""
    s, ms = divmod(epoch_in_seconds * 1000, 1000)
    return "{}.{:03d}".format(
        time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(epoch_in_seconds)), int(ms)
    )


def wait_for_regex(stream, regex, max_wait):
    """Waits for the given regex to appear on the logcat stream, or until max_wait time has passed.

    Returns the match, or None in case of timeout.
    """
    compiled = re.compile(regex)
    timeout_after = time.time() + max_wait
    for line in iter(stream.get, None):

        if timeout_after < time.time():
            logging.warning("Timed out while waiting for %s", regex)
            return None

        m = compiled.match(line)
        if m:
            return m


class StreamingCall(object):
    """A streaming call that receives data on a separate thread.

    All the received messages will be placed in a queue that is returned
    upon entering, tests can examine the queue to make sure it is behaving as expected.

    The call will automatically be cancelled upon exit. Use it
    as follows:

    with StreamingCall(emu.streamXXX(xx)) as stream:
        stream.get()
    """

    __FINISHED_SENTINEL__ = {"Finished": True}

    def __init__(self, stream_call):
        self._queue = Queue()
        self._stream_call = stream_call

    def _observe_call(self):
        received = 0
        try:
            for val in self._stream_call:
                self._queue.put(val)
                received = received + 1
        except grpc.RpcError as e:
            # We expect to be cancelled by either the client or server.
            logging.info(
                "Completed observation: %s, %s, received: %d messages",
                e.code(),
                e.details(),
                received,
            )
        self._queue.put(self.__FINISHED_SENTINEL__)

    def __iter__(self):
        return self

    def __next__(self):
        result = self._queue.get()
        if result != self.__FINISHED_SENTINEL__:
            return result
        else:
            raise StopIteration

    def __enter__(self):
        Thread(target=self._observe_call).start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # We left scope, cancel from the client side.
        self._stream_call.cancel()
