#!/bin/bash
set -e

CLIENT_NAME="download"
LAUNCH_DIR=$(pwd)

usage() {
  echo "Usage: $0 [-r|--recreate] <sponge_id>"
  echo "  -r, --recreate  Delete the download client and recreate it with the same name"
  exit 1
}

RECREATE=false
SPONGE_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -r|--recreate)
      RECREATE=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      if [ -z "$SPONGE_ID" ]; then
        SPONGE_ID="$1"
      else
        echo "Error: Unexpected argument '$1'"
        usage
      fi
      shift
      ;;
  esac
done

if [ -z "$SPONGE_ID" ]; then
  echo "Error: Missing sponge_id argument."
  usage
fi

if [ "$RECREATE" = true ]; then
  echo "Recreate option specified. Checking if client '$CLIENT_NAME' exists..."
  full_name=$(g4 clients | grep -E "^Client [^:]+:${CLIENT_NAME}:[0-9]+:citc" | head -n1 | cut -d' ' -f2 || true)
  if [ -n "$full_name" ]; then
    echo "Deleting existing client: $full_name"
    P4CLIENT="$full_name" p4 g4d -d >/dev/null
    echo "Waiting for client directory to be unmounted and removed..."
    USER_NAME="${USER:-$(whoami)}"
    for i in {1..30}; do
      if [ ! -d "/google/src/cloud/${USER_NAME}/${CLIENT_NAME}" ]; then
        echo "Client directory successfully unmounted and removed."
        break
      fi
      sleep 1
    done
  else
    echo "Client '$CLIENT_NAME' does not exist, nothing to delete."
  fi
fi

# Verify client existence and validity
client_exists=true
if [ "$RECREATE" = true ]; then
  client_exists=false
else
  if ! p4 g4d "$CLIENT_NAME" >/dev/null 2>&1; then
    client_exists=false
  else
    client_dir=$(p4 g4d "$CLIENT_NAME" 2>/dev/null || true)
    if [ -z "$client_dir" ] || [ ! -d "$client_dir" ] || ! (cd "$client_dir" && g4 info >/dev/null 2>&1); then
      client_exists=false
    fi
  fi
fi

if [ "$client_exists" = false ]; then
  echo "Client '$CLIENT_NAME' does not exist or is invalid. Creating it..."
  p4 g4d -f "$CLIENT_NAME" >/dev/null
fi

client_dir=$(p4 g4d "$CLIENT_NAME" 2>/dev/null || true)
if [ -z "$client_dir" ]; then
  echo "Error: Failed to locate or create CitC client '$CLIENT_NAME'."
  exit 1
fi

OUTPUT_DIR="${LAUNCH_DIR}/${SPONGE_ID}"
echo "Creating output directory: $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

echo "Changing directory to client workspace: $client_dir"
cd "$client_dir"

echo "Running download command for sponge ID $SPONGE_ID..."
blaze run //experimental/users/kmagic/android/spongequery:download -- \
  --invocation_id "$SPONGE_ID" \
  --output_dir "$OUTPUT_DIR"
