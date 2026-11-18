#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================"
echo "  GLV PS5 Audio Extractor - macOS Launcher"
echo "========================================================"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

PYTHON_BIN=""
for p in "/opt/homebrew/bin/python3" "/usr/local/bin/python3" "$(which python3 2>/dev/null)" "/usr/bin/python3"; do
    if [ -n "$p" ] && [ -x "$p" ]; then
        PYTHON_BIN="$p"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "Python 3 is required but was not found."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Using Python: $($PYTHON_BIN --version) at $PYTHON_BIN"
echo "Starting GLV PS5 Audio Extractor..."
exec "$PYTHON_BIN" gui_app.py
