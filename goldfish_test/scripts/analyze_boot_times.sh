#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

DIR="$1"

if [ ! -d "$DIR" ]; then
    echo "Error: Directory '$DIR' does not exist."
    exit 1
fi

grep -r "Boot completed in" "$DIR" --include="0005.goldfish.stdoutstderr.txt" 2>/dev/null | \
awk -F "Boot completed in " '{print $2}' | \
awk '{print $1}' | \
python3 -c "
import sys, statistics
data = [float(line.strip()) for line in sys.stdin if line.strip()]
if not data:
    print('No boot times found.')
else:
    print(f'Count:   {len(data)}')
    print(f'Min:     {min(data):.2f} ms')
    print(f'Max:     {max(data):.2f} ms')
    print(f'Average: {statistics.mean(data):.2f} ms')
    if len(data) > 1:
        print(f'Std Dev: {statistics.stdev(data):.2f} ms')
    else:
        print('Std Dev: N/A (requires at least 2 data points)')
"