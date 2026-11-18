@echo off
title Build GLV PS5 Audio Extractor Single-File EXE
cd /d "%~dp0"
echo ========================================================
echo   Building GLV PS5 Audio Extractor Single-File EXE...
echo ========================================================
python -m PyInstaller --noconfirm --onefile --windowed --name "GLV_PS5_Audio_Extractor" gui_app.py
echo.
echo Copying to project root...
copy /Y "dist\GLV_PS5_Audio_Extractor.exe" "GLV_PS5_Audio_Extractor.exe"
echo.
echo Build Complete!
echo Standalone EXE: GLV_PS5_Audio_Extractor.exe (No _internal folder required!)
pause
