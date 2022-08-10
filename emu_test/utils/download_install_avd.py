"""This script downloads the AVD for API27 and extract the contents.

The script is meant to bypass the SDK manager by directly downloading and extracting the system image.
"""

import requests
import sys
import zipfile
import os

api = sys.argv[1]
tag = sys.argv[2]
abi = sys.argv[3]
BUILD_VERSION = 'r11'
url = 'https://dl.google.com/android/repository/sys-img/' + tag + '/' + abi + '-' + api + '_r11.zip'
filename = url.rsplit('/', 1)[1]
android_root = os.environ['ANDROID_HOME']

if len(filename) > 0:
    r = requests.get(url, allow_redirects=True)
    assert r.headers.get('content-type') == 'application/zip'
    open(filename, 'wb').write(r.content)

    filepath = os.path.join(filename)
    filedest = os.path.join(api, tag)

    with zipfile.ZipFile(filepath, 'r') as zip_ref:
        zip_ref.extractall(filedest)
