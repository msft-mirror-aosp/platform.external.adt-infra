# Container scripts for external releases

This is a set of minimal scripts to run the emulator in a container for various
systems such as Docker, for external consumption. Acloud is not used; only the
emulator and system image zip files are needed.

We do similar things as the internal facing scripts, but is meant for external
release.  When the container images are built, they can be separately pushed to
some location such as docker hub or even dl.google.com.

# Docker

    python emu_docker.py <emulator-zip> <system-image-zip> <docker-repo> [docker-src-dir (getcwd()/src by default)]

This places all the right elements to run a docker image, but does not build,
run or publish yet.  Uses a similar Dockerfile with a Pixel 2 AVD as for the
internal scripts.

TODO: What other container systems can we provide scripts for? e.g., k8s,
gvisor
