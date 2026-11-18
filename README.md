# 🎮 GLV PS5 Media Converter & Audio Extractor

[![Platform](https://img.shields.io/badge/Platform-macOS%20Web%20%7C%20Windows-blue?style=flat-square&logo=apple&logoColor=white)](https://github.com/narendra-007/GLV-PS5-Audio-Extractor)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![NLE Ready](https://img.shields.io/badge/NLE-DaVinci%20%7C%20Premiere%20%7C%20Final%20Cut-06b6d4?style=flat-square)](#)

A dedicated, high-performance media suite engineered specifically for **PS5 gamers, streamers, and video editors**. Converts PS5 WebM gameplay clips into **NLE-compatible Apple ProRes 422 MOV**, **Calibrated MP4 (Anti-Washout)**, or **Lossless Studio Audio Masters (24-bit PCM WAV, MP3, AAC, FLAC, Opus)**.

---

## 💡 The Problem: Why Video Editors Reject PS5 WebM & Wash Out Colors

### 1. Most Editing Software Does NOT Support WebM
Many creators assume they can drop PS5 `.webm` clips directly into their video editor timeline. In reality:
* **Apple Final Cut Pro:** Completely rejects `.webm` files (unsupported container and codec).
* **Adobe Premiere Pro:** Rejects `.webm` natively (requires third-party plugins that frequently crash).
* **DaVinci Resolve:** Incomplete WebM support — often fails to decode Opus audio tracks or causes offline frame errors.
* **CapCut:** Throws unsupported format import errors on `.webm`.

### 2. Conventional Converters Cause "Washed Out" Colors
When creators try converting WebM to MP4 with basic converters (like HandBrake or default FFmpeg settings), footage looks faded and gray because:
* **Color Matrix Stripping:** PS5 BT.709 / BT.2020 metadata tags are dropped.
* **Full vs. Limited Range Mismatch:** Video levels shift from Full (`0-255`) to Limited (`16-235`), destroying black levels.

---

## ✅ The GLV Anti-Washout Solution

GLV Media Converter solves both problems by providing calibrated export pipelines tailored specifically for video editors:

| Target Profile | Best For | Benefits |
| :--- | :--- | :--- |
| 🎬 **Apple ProRes 422 MOV** | **Final Cut Pro, Premiere Pro, DaVinci Resolve** | **10-bit studio master**, zero color washout, ultra-smooth timeline scrubbing, no proxy generation needed. |
| 🎬 **Calibrated MP4 (H.264)** | **Universal Sharing, YouTube, CapCut** | Injects exact VUI color tags (`bt709`, `tv` range) so colors remain 100% punchy and accurate. |
| 🎬 **Calibrated MP4 (HEVC / HDR)** | **PS5 4K HDR Gameplay** | Preserves 10-bit HDR Rec.2020 color metadata. |
| 🎵 **WAV (24-bit Studio PCM)** | **Professional Audio Mixing** | Uncompressed master audio track. |
| 🎵 **Opus (Stream Copy)** | **Bit-for-Bit Extraction** | Instant copy in under 1 second without re-encoding. |

---

## 🌐 macOS Web App Edition (Recommended for Mac)

Runs locally in Safari / Chrome with zero installation and zero GUI bugs.

### ✨ Features:
- **Native macOS File Chooser:** Click **"Choose File on Mac"** to pick files directly via native Finder sheets (`osascript`).
- **Drag & Drop:** Drop any PS5 `.webm` file directly into your browser window.
- **In-Browser Audio/Video Player:** Preview converted video and audio directly inside the web interface.
- **Reveal in Finder:** One-click button to open the converted file in macOS Finder.

### 🚀 How to Run on macOS:
1. Download **`GLV_PS5_Audio_Extractor_Web_macOS.zip`** (or clone the repository).
2. **Double-click `run_web_mac.command`** in Finder *(or run `python3 web_app.py` in Terminal)*.
3. Safari / Chrome opens automatically to `http://127.0.0.1:5050`.

---

## 💻 Windows Standalone Executable

Download the pre-compiled, single-file executable:
* **[GLV_PS5_Audio_Extractor.exe](https://github.com/narendra-007/GLV-PS5-Audio-Extractor/releases/latest)** (12 MB, no install required).

Just double-click to run!

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
