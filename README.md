# 🎮 GLV PS5 Audio Extractor

[![Platform](https://img.shields.io/badge/Platform-macOS%20Web%20%7C%20Windows-blue?style=flat-square&logo=apple&logoColor=white)](https://github.com/narendra-007/GLV-PS5-Audio-Extractor)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Zero Quality Loss](https://img.shields.io/badge/Audio-Lossless%20%26%20Stream%20Copy-06b6d4?style=flat-square)](#)

A dedicated, high-performance audio extraction suite engineered specifically for **PS5 gamers, streamers, and video editors** to extract pristine master audio from PS5 WebM gameplay clips with zero quality loss and no video color degradation.

Available as:
1. 🌐 **Web App Edition (macOS & Cross-Platform)** — Runs locally in Safari / Chrome with zero installation and zero GUI bugs.
2. 💻 **Windows Standalone EXE** — Portable, single-file 12 MB executable.

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

## 🌐 macOS Web App Edition (Recommended for Mac)

Runs as a local web app with zero dependencies. Runs instantly on Safari, Chrome, Edge, and Firefox.

### ✨ Web App Highlights:
- **Zero GUI or Display Bugs:** Completely immune to macOS Tkinter / CustomTkinter blank-screen glitches.
- **Native macOS File Chooser:** Click "Choose File on Mac" to pick files via native Finder sheets (`osascript`).
- **Drag & Drop:** Drag any PS5 `.webm` file directly into your browser window.
- **In-Browser Audio Player:** Listen and verify your extracted audio directly inside the web app.
- **Reveal in Finder:** One-click button to highlight the extracted file in Finder.

### 🚀 How to Run on macOS:
1. Clone or download this repository.
2. Double-click **`run_web_mac.command`** in Finder.
   *(Or run `python3 web_app.py` in Terminal).*
3. Your default browser will automatically open to `http://127.0.0.1:5050`.

---

## 💻 Windows Standalone EXE

Download the pre-compiled, single-file executable:
* **[GLV_PS5_Audio_Extractor.exe](https://github.com/narendra-007/GLV-PS5-Audio-Extractor/releases/latest)** (12 MB, no install required).

Just double-click to run!

---

## 🎧 Supported Audio Formats

- **Opus (Stream Copy)** — Instant bit-for-bit extraction in under 1 second without re-encoding.
- **WAV (24-bit Studio PCM)** — Master studio audio for DaVinci Resolve, Premiere Pro, and Final Cut Pro.
- **WAV (16-bit Lossless PCM)** — Standard CD quality.
- **FLAC (Lossless Compressed)** — Bit-perfect, reduced storage footprint.
- **MP3 (320 kbps Audiophile)** — Maximum compatibility.
- **AAC / M4A (256 kbps Studio)** — Apple and YouTube standard.

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
