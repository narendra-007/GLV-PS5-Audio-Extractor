#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================"
echo "  Building GLV PS5 Audio Extractor Standalone Mac App"
echo "========================================================"

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is not installed. Please install Python 3."
    exit 1
fi

echo "Using Python: $(python3 --version) at $(which python3)"
echo "Installing PyInstaller..."
python3 -m pip install --quiet pyinstaller

echo "Compiling native standalone macOS .app bundle..."
python3 -m PyInstaller \
    --noconfirm \
    --windowed \
    --onedir \
    --name "GLV_PS5_Audio_Extractor" \
    gui_app.py

echo ""
echo "========================================================"
echo "  Build Complete!"
echo "  App Location: dist/GLV_PS5_Audio_Extractor.app"
echo "========================================================"
echo "Launching app now..."
open "dist/GLV_PS5_Audio_Extractor.app" 2>/dev/null || true
