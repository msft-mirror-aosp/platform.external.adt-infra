#!/bin/bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/pass_audio_hifi_ultrasound_speaker_test.py" "$@"
