#!/bin/sh
# This configures the devpi server to use accept uploads from this shell.
pip install devpi-client twine
devpi use http://localhost:3141
devpi login root --password "@verys@f3pa@ssw0rd"
devpi user -c packages email=adt-infra@google.com password=packages
devpi index -c packages/stable bases=root/pypi volatile=False
devpi index -c packages/staging bases=packages/stable volatile=True

