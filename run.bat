@echo off
title GLV PS5 Audio Extractor
cd /d "%~dp0"
if exist "GLV_PS5_Audio_Extractor.exe" (
    start "" "GLV_PS5_Audio_Extractor.exe"
) else if exist "dist\GLV_PS5_Audio_Extractor.exe" (
    start "" "dist\GLV_PS5_Audio_Extractor.exe"
) else (
    python gui_app.py
)
