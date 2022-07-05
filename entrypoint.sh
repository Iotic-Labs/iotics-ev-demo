#!/usr/bin/env sh

echo "\n\n--- Starting web UI ---\n\n"

# (just serves filesystem)
python3 -m http.server -d src/js 9090 &
sleep 1

echo "\n\n--- Starting twin_manager.py ---\n\n"

python3 src/twin_manager.py
