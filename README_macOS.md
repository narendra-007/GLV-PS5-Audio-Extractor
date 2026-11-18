# GLV PS5 Audio Extractor - macOS Edition (Universal Native)

A dedicated, standalone desktop application engineered specifically for PS5 gamers and video editors to extract pristine audio from PS5 WebM gameplay recordings with zero quality loss and no color washout.

---

## 💡 Why the Previous CustomTkinter App Showed Blank on macOS

CustomTkinter has a documented upstream bug (**Issues #1690 and #1934**) on macOS when running on Apple's bundled Python 3.9 (or older Tcl/Tk 8.5/8.6 versions). CustomTkinter canvas drawing fails silently, resulting in an empty, solid dark window where no buttons or text appear.

### ✅ Permanent Solution
We completely rebuilt the GUI engine using **standard, native Python Tkinter / TTK**:
- **100% Native & Universal:** Runs instantly on ANY macOS version (Sonoma, Sequoia, Ventura, Monterey, Big Sur) and ANY Python version.
- **Zero External Dependencies:** No need for `customtkinter` or third-party theme packages.
- **Modern Dark UI:** Retains the exact same dark theme, cyan accents, PS5 advisory notice, and real-time audio progress bar.

---

## 🚀 Quick Launch (Easiest)

### Method 1: Double-Click `run.command` (Instant)
1. Double-click **`run.command`** in Finder.
2. The GUI launches immediately (no installation or building needed!).

---

### Method 2: Compile Standalone `.app`
1. Open Terminal in this folder.
2. Run:
   ```bash
   bash build_mac_app.sh
   ```
3. It will compile and automatically launch **`dist/GLV_PS5_Audio_Extractor.app`** for you!

---

## 🎧 Supported Audio Extraction Formats
- **Copy Stream (Original Opus / AAC)** — Instant, zero re-encoding, pure bit-for-bit extraction.
- **WAV (24-bit Studio PCM)** — Best for Premiere Pro, DaVinci Resolve, Final Cut Pro.
- **WAV (16-bit Lossless PCM)** — Standard CD lossless audio.
- **FLAC (Lossless Compressed)** — Bit-perfect, smaller file size.
- **MP3 (320 kbps Audiophile)** — Maximum compatibility.
- **AAC (256 kbps Studio M4A)** — Apple & YouTube standard.
