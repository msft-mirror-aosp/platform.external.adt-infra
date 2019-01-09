#!/bin/bash

# start VNC
vncserver

# start git authentication daemon
~/gcompute-tools/git-cookie-authdaemon

# re-mount msvc
sudo umount /mnt/msvc
sudo mount /mnt/msvc
