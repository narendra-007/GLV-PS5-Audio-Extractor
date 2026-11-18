# 🎮 GLV PS5 Audio Extractor

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-blue?style=flat-square&logo=apple&logoColor=white)](https://github.com/narendra-007/GLV-PS5-Audio-Extractor)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Zero Quality Loss](https://img.shields.io/badge/Audio-Lossless%20%26%20Stream%20Copy-06b6d4?style=flat-square)](#)

A dedicated, standalone desktop application engineered specifically for **PS5 gamers, streamers, and video editors** to extract pristine audio from PS5 WebM gameplay clips with zero quality loss and no video color degradation.

---

## 💡 The Problem: Why PS5 WebM Conversion Looks "Washed Out"

When recording 1080p or 4K HDR/SDR gameplay on the PlayStation 5, Sony saves video files in the **WebM container** using VP9 or AV1 video with Opus audio. 

Most conventional converters convert the entire WebM video into MP4. During this conversion:
1. **Color Primaries & Matrix Coefficients Get Stripped:** The PS5's specific color tags (BT.709 / BT.2020 HDR) are often misinterpreted or flattened.
2. **Full vs. Limited Range Mismatch:** Video pixel levels shift from PC Full Range (`0-255`) to Limited Range (`16-235`), making blacks look gray and colors appear washed out.

### ✅ The Professional Solution
**Do not convert the video.** Instead:
1. Use **GLV PS5 Audio Extractor** to extract the pristine master audio in under a second.
2. Place your original PS5 WebM video directly onto your editor timeline (DaVinci Resolve, Premiere Pro, Final Cut Pro, CapCut).
3. Place the extracted studio audio track underneath it.
4. Export your final edit directly from your NLE — preserving **100% of your PS5's original color science and acoustic fidelity**.

---

## ✨ Key Features

- **⚡ Instant Opus Stream Copy:** Extracts original Opus/AAC audio bit-for-bit in under 1 second without re-encoding.
- **🎧 Studio-Grade Master Exports:**
  - `WAV (24-bit Studio PCM)` — Uncompressed 24-bit audio master for professional mixing.
  - `WAV (16-bit Lossless PCM)` — Standard CD-quality lossless audio.
  - `FLAC (Lossless Compressed)` — Bit-perfect, reduced storage footprint.
  - `MP3 (320 kbps Audiophile)` — Universal high-bitrate compatibility.
  - `AAC / M4A (256 kbps Studio)` — Optimized for Apple ecosystem & YouTube.
- **🔍 Deep WebM Inspector:** Instant FFprobe analysis detailing Audio Codec, Sample Rate, Channels (Stereo/5.1), Bitrate, Duration, and File Size.
- **📊 Real-Time Microsecond Telemetry:** Live progress bar, timestamp tracker, and encoding speed multipliers (e.g. `24.5x`).
- **🖥️ 100% Universal Native GUI:** Built with native Tkinter/TTK — runs instantaneously on both Windows and macOS without external GUI dependencies or blank-screen rendering bugs.
- **🚀 One-Click Standalone EXE:** Single-file Windows binary with no installer, DLLs, or Python setup required.

---

## 📥 Download Pre-Built Binaries

| Operating System | Download | Instructions |
| :--- | :--- | :--- |
| **Windows 10 / 11** | [**GLV_PS5_Audio_Extractor.exe**](GLV_PS5_Audio_Extractor.exe) | Single-file executable. Just double-click to run. |
| **macOS (Apple Silicon & Intel)** | [**GLV_PS5_Audio_Extractor_macOS.zip**](GLV_PS5_Audio_Extractor_macOS.zip) | Extract zip and double-click `run.command` or `GLV_PS5_Audio_Extractor.app`. |

---

## 🛠️ Running from Source

### Prerequisites
- Python 3.8 or newer
- FFmpeg installed and available on system PATH (or in `/opt/homebrew/bin` on Mac)

### Windows
```bash
git clone https://github.com/narendra-007/GLV-PS5-Audio-Extractor.git
cd GLV-PS5-Audio-Extractor
python gui_app.py
```

### macOS / Linux
```bash
git clone https://github.com/narendra-007/GLV-PS5-Audio-Extractor.git
cd GLV-PS5-Audio-Extractor
python3 gui_app.py
```

---

## 🔨 Building Standalone Executables

### Windows (Single-File `.exe`)
```cmd
build_exe.bat
```
*Compiles a single standalone executable `GLV_PS5_Audio_Extractor.exe` using PyInstaller.*

### macOS (Native `.app` Bundle)
```bash
bash build_mac_app.sh
```
*Compiles `dist/GLV_PS5_Audio_Extractor.app` and launches it automatically.*

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
