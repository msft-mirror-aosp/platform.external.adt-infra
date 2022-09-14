pip install devpi_server devpi-client --index-url repo/simple

devpi-init --serverdir %cd%/server --root-passwd "@verys@f3pa@ssw0rd"
start "devpi" devpi-server --serverdir %cd%/server

timeout /T 5
devpi use http://localhost:3141
devpi login root --password "@verys@f3pa@ssw0rd"
devpi user -c packages email=adt-infra@google.com password=packages
devpi index -c packages/stable bases=root/pypi volatile=False
devpi index -c packages/staging bases=packages/stable volatile=True
