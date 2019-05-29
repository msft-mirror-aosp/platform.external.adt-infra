docker run -e "ADBKEY=$(cat ~/.android/adbkey)" --privileged  --publish 5556:5556/tcp --publish 5554:5554/tcp $1
