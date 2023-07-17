# Copyright 2023 The Android Open Source Project
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

import http.server
import logging
import threading
import time
from pathlib import Path

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat

from emu.timing import wait_until
from tests.test_utils import proto_to_pillow


class TemporaryWebServer(http.server.SimpleHTTPRequestHandler):
    """
    A custom HTTP request handler that serves a blue-themed HTML page.

    Attributes:
        text (str): The HTML content of the blue-themed page.

    Methods:
        do_GET(self): Handles the GET request and sends the blue-themed HTML page as the response.
    """

    text = """<!DOCTYPE html>
<html>
  <head>
    <title>Blue Page</title>
    <style>
      body {
        background-color: blue;
        color: white;
      }
    </style>
  </head>
  <body>
    <h1>This is a blue page</h1>
    <p>Almose everything on this page is blue!</p>
  </body>
</html>
"""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(self.text.encode("utf-8"))


@pytest.fixture(scope="module")
def test_server(request):
    """
    Pytest fixture that starts an HTTP server on a random port using the TemporaryWebServer handler.

    This fixture is used to provide a running HTTP server for testing purposes. The test server will
    always offer a `blue` page for every get request.

    Args:
        request (pytest.FixtureRequest): The pytest fixture request object.

    Returns:
        Tuple[str, int]: A tuple containing the host and port on which the server is running.

    Example:
        def test_example(test_server):
            host, port = test_server
            # Access the server using the obtained host and port
            ...
    """
    # Start the HTTP server in a separate thread
    server_address = ("", 0)  # Random port
    httpd = http.server.HTTPServer(server_address, TemporaryWebServer)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()

    # Obtain the actual port on which the server is running
    host, port = httpd.server_address

    # Add a finalizer to stop the server when the test is finished
    def cleanup():
        httpd.shutdown()
        thread.join()

    request.addfinalizer(cleanup)

    return host, port


@pytest.fixture
def log_directory(pytestconfig):
    """Get the value of the --log-file option."""
    log_file = pytestconfig.getoption("--log-file")
    if log_file:
        return Path(log_file).parent

    return Path.cwd()


@pytest.fixture
def prepare_chrome(avd):
    """
    Pytest fixture that launches Chrome and configures it
    to skip the welcome page.

    This fixture prepares the Chrome application on an
    Android Virtual Device (AVD) for testing.
    """
    # Configure to skip welcome page
    avd.adb.shell(
        'echo "chrome --disable-fre --no-default-browser-check --no-first-run --skip_first_run_ui" > /data/local/tmp/chrome-command-line'
    )
    avd.adb.shell("am set-debug-app --persistent com.android.chrome")

    # Start Chrome for the first time
    avd.start_activity("com.android.chrome/com.google.android.apps.chrome.Main")

    # Kill and restart to skip a pop-up
    avd.stop_activity("com.android.chrome")
    avd.start_activity("com.android.chrome/com.google.android.apps.chrome.Main")

    yield

    avd.stop_activity("com.android.chrome")


def test_make_sure_webserver_works(test_server):
    """Test function to ensure that the web server is functioning correctly.

    This test function verifies that the server responds with a 200 status code and returns
    the expected content defined in the `TemporaryWebServer` class.
    """
    host, port = test_server

    # Access the server using the obtained host and port
    response = http.client.HTTPConnection(host, port)
    response.request("GET", "/")
    result = response.getresponse()

    assert result.status == 200
    assert result.read().decode("utf-8") == TemporaryWebServer.text


def get_rgb_screenshot(emulator_controller, image_format, image_dir):
    """
    Get an RGB screenshot from the emulator controller and save it to a file.

    This method captures a screenshot using the provided emulator
    controller in the specified image format,
    converts the image to RGB mode, saves the screenshot
    as a JPG to the specified file, and returns the RGB image.

    Args:
        emulator_controller (EmulatorController): An instance of the emulator controller.
        image_format (ImageFormat): The desired format of the screenshot image.
        image_file (Path): The file path to save the screenshot image.

    Returns:
        Image: The RGB image obtained from the screenshot.
    """
    img = proto_to_pillow(emulator_controller.getScreenshot(image_format))

    # Convert image to RGB mode to access individual color channels
    rgb_image = img.convert("RGB")
    image_file = image_dir / f"screenshot-{round(time.time())}.png"
    logging.info(
        "Got %sx%s, saving screenshot to %s",
        img.width,
        img.height,
        image_file.absolute(),
    )
    rgb_image.save(image_file, "PNG")
    return rgb_image


@pytest.mark.e2e
@pytest.mark.timeout(timeout=120, func_only=True)
def test_launch_chrome_google(
    prepare_chrome, test_server, avd, emulator_controller, log_directory
):
    """
    This test launches Chrome on an Android device, navigates to  a `blue`
    page served by the test server, captures a screenshot, and verifies
    that at least 40% of the image pixels are blue.
    """
    _, port = test_server
    chrome_page = f"http://10.0.2.2:{port}/"
    avd.adb.shell(
        f"am start -a android.intent.action.VIEW -d {chrome_page} com.android.chrome"
    )

    def at_least_40_percent_of_image_is_blue():
        """
        Helper function to check if at least 10% of the image pixels are blue.

        Returns:
            bool: True if at least 10% of the image pixels are blue, False otherwise.
        """
        rgb_image = get_rgb_screenshot(
            emulator_controller, ImageFormat(), log_directory
        )

        percent_blue = 40
        blue_count = 0

        # Iterate over each pixel in the image
        for x in range(rgb_image.width):
            for y in range(rgb_image.height):
                # Get the RGB values of the pixel at (x, y)
                r, g, b = rgb_image.getpixel((x, y))

                # Check if the pixel corresponds to the desired shade of blue
                if r == 0 and g == 0 and b == 255:
                    blue_count += 1
        return blue_count > (rgb_image.width * rgb_image.height * percent_blue / 100)

    assert wait_until(
        at_least_40_percent_of_image_is_blue
    ), "Did not see a screenshot with 40%% blue pixels"
