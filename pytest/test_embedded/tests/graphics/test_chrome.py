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
import threading
import socket

import pytest
from aemu.proto.emulator_controller_pb2 import ImageFormat

from emu.timing import eventually, wait_until


def check_server_availability(server_address):
    """Checks if the web server is up and running and has bound to the given port.

    Args:
      server_address: A tuple of (host, port) where the web server is running.

    Returns:
      True if the web server is up and running, False otherwise.
    """

    try:
        s = socket.socket()
        s.connect(server_address)
        s.close()
        return True
    except:
        return False


def find_available_port(start_port=8000, num_ports=100):
    """Find an available port within a specified range.

    This function iterates through a range of ports starting from `start_port` and checks each
    port to determine if it is available for binding. It returns the first available port found
    within the specified range.

    Args:
        start_port (int, optional): The starting port to begin the search (default is 8000).
        num_ports (int, optional): The number of consecutive ports to check (default is 100).

    Returns:
        int or None: The first available port found within the specified range, or None if no
        available port is found.
    """
    for port in range(start_port, start_port + num_ports):
        try:
            # Attempt to create a socket and bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
            return port
        except OSError as _err:
            # Port is already in use, continue to the next one
            continue
    return None


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
    count = 0

    def do_GET(self):
        TemporaryWebServer.count += 1
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
            host, port, server = test_server
            # Access the server using the obtained host and port
            ...
    """
    # First we find an available port in the range 8000-8100 (b/303719691)
    port = find_available_port()
    if port is None:
        raise OSError(
            "Unable to find an available port in the range [8000,8100] for binding the webserver."
        )

    # Start the HTTP server in a separate thread
    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, TemporaryWebServer)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()

    def server_is_available():
        return check_server_availability(("localhost", port))

    # Wait until the web server is up and running.
    assert eventually(server_is_available, timeout=10)

    # Obtain the actual port on which the server is running
    host, port = httpd.server_address

    # Add a finalizer to stop the server when the test is finished
    def cleanup():
        httpd.shutdown()
        thread.join()

    request.addfinalizer(cleanup)

    return host, port


@pytest.fixture
def prepare_chrome(avd):
    """
    Pytest fixture that launches Chrome and configures it
    to skip the welcome page.

    This fixture prepares the Chrome application on an
    Android Virtual Device (AVD) for testing.
    """
    TemporaryWebServer.count = 0
    # Configure to skip welcome page
    avd.adb.shell(
        'echo "chrome --disable-fre --no-default-browser-check --no-first-run --skip_first_run_ui" > /data/local/tmp/chrome-command-line'
    )
    avd.adb.shell("am set-debug-app --persistent com.android.chrome")

    # Start Chrome for the first time
    avd.start_activity(
        "com.android.chrome/com.google.android.apps.chrome.Main", params=None
    )

    # Kill and restart to skip a pop-up
    avd.stop_activity("com.android.chrome")
    avd.start_activity(
        "com.android.chrome/com.google.android.apps.chrome.Main", params=None
    )
    avd.adb.shell(
        f"am start -a android.intent.action.VIEW -d www.google.com com.android.chrome"
    )

    yield

    avd.stop_activity("com.android.chrome")


@pytest.mark.skipos("win", "reason: b/304785674 - test crashes.")
@pytest.mark.graphics
def test_make_sure_webserver_works(test_server):
    """Test function to ensure that the web server is functioning correctly.

    This test function verifies that the server responds with a 200 status code and returns
    the expected content defined in the `TemporaryWebServer` class.
    """
    host, port = test_server
    get_count = TemporaryWebServer.count

    # Access the server using the obtained host and port
    response = http.client.HTTPConnection(host, port)
    response.request("GET", "/")
    result = response.getresponse()

    assert result.status == 200
    assert result.read().decode("utf-8") == TemporaryWebServer.text
    assert TemporaryWebServer.count >= get_count + 1


def request_page_in_chrome(avd, page):
    avd.stop_activity("com.android.chrome")
    avd.start_activity(
        "com.android.chrome/com.google.android.apps.chrome.Main", params=None
    )
    avd.adb.shell(
        f"am start -a android.intent.action.VIEW -d {page} com.android.chrome"
    )


@pytest.mark.e2e
@pytest.mark.timeout(timeout=120, func_only=True)
@pytest.mark.graphics
@pytest.mark.skipos('m1', 'reason: b/311200619')
def test_launch_chrome_google_gets_page(avd, prepare_chrome, test_server):
    _, port = test_server
    chrome_page = f"http://10.0.2.2:{port}/"
    get_count = TemporaryWebServer.count

    request_page_in_chrome(avd, chrome_page)
    assert wait_until(
        lambda: TemporaryWebServer.count > get_count, timeout=5
    ), f"Chrome did not make a get call in a timely fashion {TemporaryWebServer.count} <= {get_count}"


@pytest.mark.e2e
@pytest.mark.timeout(timeout=120, func_only=True)
@pytest.mark.flaky(reruns=1, reruns_delay=5)
@pytest.mark.graphics
@pytest.mark.xpass
def test_launch_chrome_google(prepare_chrome, test_server, avd, get_screenshot):
    """
    This test launches Chrome on an Android device, navigates to  a `blue`
    page served by the test server, captures a screenshot, and verifies
    that at least 40% of the image pixels are blue.

    TODO(jansene): We should not use an external webserver, but instead render
    a local page. This test is really here to validate that gfxstream is sort
    of working as expected.
    """
    _, port = test_server
    chrome_page = f"http://10.0.2.2:{port}/"

    def at_least_40_percent_of_image_is_blue():
        """
        Helper function to check if at least 10% of the image pixels are blue.

        Returns:
            bool: True if at least 10% of the image pixels are blue, False otherwise.
        """
        _, rgb_image = get_screenshot(ImageFormat())
        rgb_image = rgb_image.convert("RGB")

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

    max_retries = 3
    for _ in range(0, max_retries):
        request_page_in_chrome(avd, chrome_page)
        if wait_until(at_least_40_percent_of_image_is_blue, timeout=5):
            return

    assert (
        False
    ), f"Did not see a screenshot with 40%% blue pixels with {max_retries} retries"
