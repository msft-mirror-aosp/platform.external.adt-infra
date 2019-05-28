FROM debian:stretch-slim
LABEL maintainer="{{user}}" \
      com.google.android.emulator.build-date="{{date}}" \
      com.google.android.emulator.description="Pixel 2 Emulator, running API {{api}}" \
      com.google.android.emulator.version="{{tag}}-{{api}}-{{abi}}/{{emu_build_id}}"

# Install all the required emulator dependencies.
# You can get these by running ./android/scripts/unix/run_tests.sh --verbose --verbose --debs | grep apt | sort -u
# pulse audio is needed due to some webrtc dependencies.
RUN apt-get update && apt-get install -y \
# Needed for install / debug
    curl unzip procps bash \
# Emulator & video bridge dependencies
    libc6 libdbus-1-3 libfontconfig1 libgcc1 \
    libpulse0 libtinfo5 libx11-6 libxcb1 libxdamage1 \
    libxext6 libxfixes3 zlib1g libgl1 pulseaudio socat

# Next we get an android image ready
# We explicitly curl the image from a public site to make sure we
# don't accidentally publish internal testing images.
# Now we configure the user account under which we will be running the emulator
RUN mkdir -p /android/sdk/platforms && \
    mkdir -p /android/sdk/platform-tools && \
    mkdir -p /android/sdk/system-images && \
    mkdir -p /android-home && \
    curl {{url}} -o sysimg.zip && \
    unzip -u -o sysimg.zip -d /android/sdk/system-images/android && \
    rm sysimg.zip && \
    gpasswd -a root audio


COPY distribution /android/sdk
COPY platform-tools /android/sdk/platform-tools
COPY avd /android-home
COPY default.pa /etc/pulse/default.pa

# Create an initial snapshot so we will boot fast next time around.
# Doesn't work due to not being able run privileged container
# see: https://github.com/moby/moby/issues/1916
# RUN cd /android/sdk && emulator/emulator @Pixel2 -verbose -quit-after-boot 300


# Open up adb & grpc port
EXPOSE 5555
EXPOSE 5556
ENV ANDROID_SDK_ROOT /android/sdk
ENV ANDROID_AVD_HOME /android-home
WORKDIR /android/sdk

# Note, we will not be using gpu acceleration, nor will the emulator be visible.
# You will need to make use of the grpc snapshot/webrtc functionality to actually interact with
# the emulator.
CMD ["/android/sdk/launch-emulator.sh"]
