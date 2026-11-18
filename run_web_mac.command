#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================"
echo "  GLV PS5 Audio Extractor — macOS Web Edition"
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
    echo "Error: Python 3 was not found. Please install Python 3."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Using Python: $($PYTHON_BIN --version)"
echo "Starting local web server & opening your default browser..."
exec "$PYTHON_BIN" web_app.py
