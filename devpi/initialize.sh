#!/bin/sh

## Load virtual env if needed
PYTHON=python3
$PYTHON -m venv .venv
source .venv/bin/activate
DEVPI_DIR=$(dirname $0)
DEVPI_DIR=$(cd $DEVPI_DIR; pwd)

echo "Using $DEVPI_DIR, $PY_INC"
SERVERDIR=$DEVPI_DIR/server
pip3 install --index-url repo/simple wheel setuptools

pip3 -v install devpi-server
devpi-init --serverdir $SERVERDIR --root-passwd "@verys@f3pa@ssw0rd"
devpi-server --serverdir $SERVERDIR
devpi user -c packages email=adt-infra@google.com password=packages
DEVPI_PID=$!


terminate_devpi() {
    echo "KILLING $DEVPI_PID"
    kill -9 $DEVPI_PID
}

trap "terminate_devpi" EXIT QUIT INT HUP
