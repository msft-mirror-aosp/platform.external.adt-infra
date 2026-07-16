#!/bin/bash
set -e

usage() {
  echo "Usage: $0 <sponge_id_or_directory>"
  exit 1
}

if [ -z "$1" ]; then
  echo "Error: No sponge ID or directory specified."
  usage
fi

SPONGE_DIR="$1"

# If the specified argument is a directory in current working directory or absolute path
if [ ! -d "$SPONGE_DIR" ] && [ -d "$(pwd)/$SPONGE_DIR" ]; then
  SPONGE_DIR="$(pwd)/$SPONGE_DIR"
fi

if [ ! -d "$SPONGE_DIR" ]; then
  echo "Error: Directory '$SPONGE_DIR' does not exist."
  usage
fi

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
python3 "${SCRIPT_DIR}/parse_results.py" "$SPONGE_DIR"
