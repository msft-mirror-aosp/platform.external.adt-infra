docker run -e "ADBKEY=$(cat ~/.android/adbkey)" --privileged  --publish 5556:5556/tcp --publish 5555:5555/tcp $1
