"""
gui_app.py - GLV PS5 Media Converter & Audio Extractor
A standalone, high-performance desktop application engineered specifically for PS5 gamers
and video editors. Converts PS5 WebM gameplay into NLE-compatible Apple ProRes 422 MOV,
Calibrated MP4 (zero washout), or studio-grade audio masters (24-bit PCM WAV, MP3, AAC, FLAC, Opus).
Built using standard Python Tkinter/TTK for 100% universal compatibility across all macOS and Windows versions.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, Optional

# --- Platform Detection & System Fonts ---

IS_MAC = sys.platform == "darwin"
FONT_UI = "Helvetica Neue" if IS_MAC else "Segoe UI"
FONT_MONO = "Menlo" if IS_MAC else "Consolas"


# --- FFmpeg & Binary Resolution ---

def find_binary(binary_name: str) -> str:
    """Locate binary next to executable, in _MEIPASS, or on system PATH (cross-platform)."""
    exe_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]))
    ext = ".exe" if sys.platform.startswith("win") else ""
    local_path = os.path.join(exe_dir, f"{binary_name}{ext}")
    if os.path.exists(local_path):
        return local_path

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass_path = os.path.join(sys._MEIPASS, f"{binary_name}{ext}")
        if os.path.exists(meipass_path):
            return meipass_path

    p = shutil.which(binary_name)
    if p:
        return p

    common = [
        rf"C:\ffmpeg\bin\{binary_name}.exe",
        rf"C:\Program Files\ffmpeg\bin\{binary_name}.exe",
        f"/opt/homebrew/bin/{binary_name}",  # Apple Silicon Mac Homebrew
        f"/usr/local/bin/{binary_name}",     # Intel Mac Homebrew
        f"/usr/bin/{binary_name}",           # Linux
    ]
    for c in common:
        if os.path.exists(c):
            return c
    return binary_name


def format_duration(seconds: float) -> str:
    """Format seconds into MM:SS.ms or HH:MM:SS."""
    if seconds <= 0:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    millis = int((seconds - int(seconds)) * 100)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}.{millis:02d}"
    return f"{m:02d}:{s:02d}.{millis:02d}"


def format_bytes(bytes_count: int) -> str:
    """Format bytes count into human-readable string."""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"


def probe_webm(file_path: str) -> Dict[str, Any]:
    """Scan WebM file with ffprobe and extract deep audio & video properties."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    cmd = [
        find_binary("ffprobe"),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        startupinfo=startupinfo,
        check=True,
    )
    raw = json.loads(res.stdout)

    fmt = raw.get("format", {})
    streams = raw.get("streams", [])

    duration_sec = float(fmt.get("duration", 0.0))
    file_size = int(fmt.get("size", os.path.getsize(file_path)))

    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    # Audio details
    audio_info = {
        "codec": "N/A",
        "sample_rate": 0,
        "channels": 0,
        "channel_label": "Stereo",
        "bitrate_kbps": 0,
        "sample_fmt": "fltp",
    }
    if a_stream:
        sample_rate = int(a_stream.get("sample_rate", 0))
        channels = int(a_stream.get("channels", 2))
        chan_lbl = "Stereo (2.0)"
        if channels == 1:
            chan_lbl = "Mono (1.0)"
        elif channels == 6:
            chan_lbl = "5.1 Surround"
        elif channels > 2:
            chan_lbl = f"{channels} Channels"

        bitrate = int(a_stream.get("bit_rate", 0))
        if bitrate == 0 and fmt.get("bit_rate"):
            bitrate = int(int(fmt["bit_rate"]) * 0.15)

        audio_info = {
            "codec": a_stream.get("codec_name", "unknown").upper(),
            "sample_rate": sample_rate,
            "channels": channels,
            "channel_label": chan_lbl,
            "bitrate_kbps": round(bitrate / 1000) if bitrate else 160,
            "sample_fmt": a_stream.get("sample_fmt", "fltp"),
        }

    # Video summary
    video_info = None
    if v_stream:
        video_info = {
            "codec": v_stream.get("codec_name", "unknown").upper(),
            "width": int(v_stream.get("width", 0)),
            "height": int(v_stream.get("height", 0)),
            "color_range": v_stream.get("color_range", "unknown"),
            "color_space": v_stream.get("color_space", "unknown"),
        }

    return {
        "file_path": os.path.abspath(file_path),
        "file_name": os.path.basename(file_path),
        "file_dir": os.path.dirname(os.path.abspath(file_path)),
        "file_size": file_size,
        "file_size_formatted": format_bytes(file_size),
        "duration_sec": duration_sec,
        "duration_formatted": format_duration(duration_sec),
        "audio": audio_info,
        "video": video_info,
    }


# --- Conversion / Extraction Engine Worker ---

class MediaProcessWorker(threading.Thread):
    """Executes FFmpeg video conversion or audio extraction with microsecond telemetry."""

    def __init__(
        self,
        input_file: str,
        output_format: str,
        sample_rate: str,
        output_dir: str,
        total_duration: float,
        on_progress,
        on_done,
    ):
        super().__init__(daemon=True)
        self.input_file = input_file
        self.output_format = output_format
        self.sample_rate = sample_rate
        self.output_dir = output_dir
        self.total_duration = total_duration
        self.on_progress = on_progress
        self.on_done = on_done
        self.process: Optional[subprocess.Popen] = None
        self.cancelled = False
        self.output_file = ""

    def run(self):
        start_time = time.time()
        base_name = os.path.splitext(os.path.basename(self.input_file))[0]
        ffmpeg_bin = find_binary("ffmpeg")

        ext = ".wav"
        codec_args = []
        is_video = False

        # 1. Video + Audio Profiles (NLE Calibrated)
        if "Apple ProRes 422 MOV" in self.output_format:
            ext = "_PS5_ProRes422.mov"
            is_video = True
            codec_args = [
                "-c:v", "prores_ks",
                "-profile:v", "3",
                "-vendor", "apl0",
                "-pix_fmt", "yuv422p10le",
                "-color_range", "tv",
                "-colorspace", "bt709",
                "-color_primaries", "bt709",
                "-color_trc", "bt709",
                "-c:a", "pcm_s24le",
            ]
        elif "Calibrated MP4 (H.264" in self.output_format:
            ext = "_PS5_Calibrated.mp4"
            is_video = True
            codec_args = [
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "17",
                "-pix_fmt", "yuv420p",
                "-vf", "scale=in_range=auto:out_range=limited:flags=lanczos+accurate_rnd",
                "-color_range", "tv",
                "-colorspace", "bt709",
                "-color_primaries", "bt709",
                "-color_trc", "bt709",
                "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0",
                "-c:a", "aac",
                "-b:a", "256k",
                "-movflags", "+faststart",
            ]
        elif "Calibrated MP4 (HEVC" in self.output_format:
            ext = "_PS5_HDR_HEVC.mp4"
            is_video = True
            codec_args = [
                "-c:v", "libx265",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p10le",
                "-vf", "scale=in_range=auto:out_range=limited:flags=lanczos+accurate_rnd",
                "-color_range", "tv",
                "-colorspace", "bt2020nc",
                "-color_primaries", "bt2020",
                "-color_trc", "smpte2084",
                "-bsf:v", "hevc_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0",
                "-c:a", "aac",
                "-b:a", "256k",
                "-movflags", "+faststart",
            ]
        # 2. Audio Only Profiles
        elif "WAV (24-bit Studio PCM)" in self.output_format:
            ext = "_PS5_Audio_24bit.wav"
            codec_args = ["-vn", "-c:a", "pcm_s24le"]
        elif "WAV (16-bit Lossless PCM)" in self.output_format:
            ext = "_PS5_Audio_16bit.wav"
            codec_args = ["-vn", "-c:a", "pcm_s16le"]
        elif "MP3 (320 kbps Audiophile)" in self.output_format:
            ext = "_PS5_Audio_320k.mp3"
            codec_args = ["-vn", "-c:a", "libmp3lame", "-b:a", "320k", "-q:a", "0"]
        elif "AAC / M4A (256 kbps Studio)" in self.output_format:
            ext = "_PS5_Audio_256k.m4a"
            codec_args = ["-vn", "-c:a", "aac", "-b:a", "256k"]
        elif "FLAC (Lossless Compressed)" in self.output_format:
            ext = "_PS5_Audio.flac"
            codec_args = ["-vn", "-c:a", "flac", "-compression_level", "8"]
        elif "Opus (Stream Copy)" in self.output_format:
            ext = "_PS5_Audio_Original.opus"
            codec_args = ["-vn", "-c:a", "copy"]
        else:
            ext = "_PS5_Audio.wav"
            codec_args = ["-vn", "-c:a", "pcm_s24le"]

        self.output_file = os.path.join(self.output_dir, f"{base_name}{ext}")

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", self.input_file,
        ]
        cmd.extend(codec_args)

        if self.sample_rate and self.sample_rate != "Original" and "-c:a copy" not in " ".join(codec_args) and not is_video:
            cmd.extend(["-ar", self.sample_rate])

        cmd.extend([
            "-progress", "pipe:1",
            "-nostats",
            self.output_file,
        ])

        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
            )

            out_time_us = 0
            speed_val = "1.0x"
            action_verb = "Converting" if is_video else "Extracting"

            while True:
                if self.cancelled:
                    if self.process:
                        self.process.terminate()
                    self.on_done(False, "Cancelled by user", self.output_file, 0.0)
                    return

                line = self.process.stdout.readline()
                if not line:
                    if self.process.poll() is not None:
                        break
                    continue

                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k == "out_time_us":
                        try:
                            out_time_us = int(v)
                            cur_sec = out_time_us / 1_000_000.0
                            pct = min(cur_sec / self.total_duration, 1.0) if self.total_duration > 0 else 0.5
                            self.on_progress(pct, cur_sec, speed_val, action_verb)
                        except ValueError:
                            pass
                    elif k == "speed":
                        speed_val = v
                    elif k == "progress" and v == "end":
                        self.on_progress(1.0, self.total_duration, speed_val, action_verb)

            ret = self.process.wait()
            elapsed = time.time() - start_time

            if ret == 0:
                self.on_done(True, "Process completed successfully!", self.output_file, elapsed)
            else:
                stderr_data = self.process.stderr.read() if self.process.stderr else "Unknown error"
                self.on_done(False, f"FFmpeg error (code {ret}):\n{stderr_data[:400]}", self.output_file, elapsed)

        except Exception as e:
            self.on_done(False, str(e), self.output_file, 0.0)


# --- UI Custom Modern Button Component ---

class ModernButton(tk.Label):
    """Universal cross-platform modern interactive button widget."""

    def __init__(
        self,
        master,
        text: str,
        command=None,
        bg_color: str = "#6366f1",
        hover_color: str = "#4f46e5",
        text_color: str = "#ffffff",
        font=(FONT_UI, 11, "bold"),
        padx: int = 16,
        pady: int = 8,
        **kwargs,
    ):
        super().__init__(
            master,
            text=text,
            bg=bg_color,
            fg=text_color,
            font=font,
            padx=padx,
            pady=pady,
            cursor="hand2",
            relief="flat",
            **kwargs,
        )
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.disabled_bg = "#1e293b"
        self.disabled_fg = "#64748b"
        self.text_color = text_color
        self._state = "normal"

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, e):
        if self._state == "normal":
            self.configure(bg=self.hover_color)

    def _on_leave(self, e):
        if self._state == "normal":
            self.configure(bg=self.bg_color)

    def _on_click(self, e):
        if self._state == "normal" and self.command:
            self.command()

    def set_state(self, state: str, text: Optional[str] = None):
        self._state = state
        if text is not None:
            self.configure(text=text)
        if state == "disabled":
            self.configure(bg=self.disabled_bg, fg=self.disabled_fg, cursor="arrow")
        else:
            self.configure(bg=self.bg_color, fg=self.text_color, cursor="hand2")


# --- Main Application Window ---

class GLVMediaConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("GLV PS5 Media Converter & Audio Extractor")
        self.geometry("880x750")
        self.minsize(800, 700)
        self.configure(bg="#0b0f19")

        # State
        self.current_meta: Optional[Dict[str, Any]] = None
        self.output_dir: str = ""
        self.worker: Optional[MediaProcessWorker] = None
        self.last_output_file: str = ""

        self._init_theme_styles()
        self._build_ui()

    def _init_theme_styles(self):
        """Configure native TTK widgets for modern dark styling."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Dark.TCombobox",
            fieldbackground="#1e293b",
            background="#334155",
            foreground="#f8fafc",
            arrowcolor="#38bdf8",
            selectbackground="#1e293b",
            selectforeground="#f8fafc",
            padding=5,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", "#1e293b")],
            foreground=[("readonly", "#f8fafc")],
        )

        style.configure(
            "Cyan.Horizontal.TProgressbar",
            troughcolor="#1e293b",
            background="#06b6d4",
            bordercolor="#1e293b",
            lightcolor="#06b6d4",
            darkcolor="#06b6d4",
            thickness=10,
        )

    def _build_ui(self):
        container = tk.Frame(self, bg="#0b0f19")
        container.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Header Bar
        header_frame = tk.Frame(container, bg="#111827", highlightbackground="#1f293d", highlightthickness=1)
        header_frame.pack(fill="x", pady=(0, 10))

        title_lbl = tk.Label(
            header_frame,
            text="🎮 GLV PS5 MEDIA CONVERTER & AUDIO EXTRACTOR",
            font=(FONT_UI, 17, "bold"),
            bg="#111827",
            fg="#f8fafc",
        )
        title_lbl.pack(anchor="w", padx=18, pady=(12, 2))

        sub_lbl = tk.Label(
            header_frame,
            text="Anti-Washout Video Conversion & Lossless Audio Engine for PS5 Clips · Tailored for DaVinci Resolve, Premiere Pro & Final Cut Pro",
            font=(FONT_UI, 11),
            bg="#111827",
            fg="#94a3b8",
        )
        sub_lbl.pack(anchor="w", padx=18, pady=(0, 12))

        # 2. NLE Compatibility & Color Advisory Notice
        notice_frame = tk.Frame(container, bg="#1e1808", highlightbackground="#f59e0b", highlightthickness=1)
        notice_frame.pack(fill="x", pady=(0, 10))

        notice_title = tk.Label(
            notice_frame,
            text="💡 Important NLE Compatibility & Anti-Washout Notice",
            font=(FONT_UI, 12, "bold"),
            bg="#1e1808",
            fg="#fbbf24",
        )
        notice_title.pack(anchor="w", padx=16, pady=(10, 3))

        notice_text = tk.Label(
            notice_frame,
            text=(
                "Most video editors (Premiere Pro, Final Cut Pro, DaVinci Resolve, CapCut) do not natively support WebM files.\n"
                "Converting directly with basic tools causes washed-out colors due to missing color range/matrix tags.\n"
                "• Choose Apple ProRes 422 MOV or Calibrated MP4 for 100% native timeline support with zero color washout.\n"
                "• Choose Studio WAV / MP3 / Opus for pure audio extraction."
            ),
            font=(FONT_UI, 10),
            bg="#1e1808",
            fg="#fef3c7",
            justify="left",
        )
        notice_text.pack(anchor="w", padx=16, pady=(0, 10))

        # 3. File Input Card
        input_card = tk.Frame(container, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        input_card.pack(fill="x", pady=(0, 10))

        tk.Label(
            input_card,
            text="Select PS5 WebM Recording",
            font=(FONT_UI, 13, "bold"),
            bg="#131d31",
            fg="#f1f5f9",
        ).pack(anchor="w", padx=18, pady=(12, 6))

        btn_row = tk.Frame(input_card, bg="#131d31")
        btn_row.pack(fill="x", padx=18, pady=(0, 8))

        self.btn_select_file = ModernButton(
            btn_row,
            text="📂 Browse PS5 WebM File",
            command=self._on_browse_file,
            bg_color="#6366f1",
            hover_color="#4f46e5",
            font=(FONT_UI, 11, "bold"),
            padx=16,
            pady=7,
        )
        self.btn_select_file.pack(side="left")

        self.lbl_selected_file = tk.Label(
            input_card,
            text="No file selected yet. Select a .webm file above.",
            font=(FONT_MONO, 10),
            bg="#131d31",
            fg="#64748b",
            anchor="w",
        )
        self.lbl_selected_file.pack(fill="x", padx=18, pady=(0, 12))

        # 4. Properties Card (Inspector)
        self.spec_card = tk.Frame(container, bg="#10192a", highlightbackground="#06b6d4", highlightthickness=1)
        self.spec_card.pack(fill="x", pady=(0, 10))

        tk.Label(
            self.spec_card,
            text="🎵 Detected Clip Properties (PS5 Master)",
            font=(FONT_UI, 13, "bold"),
            bg="#10192a",
            fg="#38bdf8",
        ).pack(anchor="w", padx=18, pady=(10, 6))

        grid_frame = tk.Frame(self.spec_card, bg="#10192a")
        grid_frame.pack(fill="x", padx=18, pady=(0, 10))

        self.lbl_prop_codec = tk.Label(grid_frame, text="Audio Codec: —", font=(FONT_UI, 11, "bold"), bg="#10192a", fg="#f8fafc")
        self.lbl_prop_codec.grid(row=0, column=0, sticky="w", padx=8, pady=3)

        self.lbl_prop_sample_rate = tk.Label(grid_frame, text="Sample Rate: —", font=(FONT_UI, 11, "bold"), bg="#10192a", fg="#34d399")
        self.lbl_prop_sample_rate.grid(row=0, column=1, sticky="w", padx=30, pady=3)

        self.lbl_prop_channels = tk.Label(grid_frame, text="Channels: —", font=(FONT_UI, 11), bg="#10192a", fg="#94a3b8")
        self.lbl_prop_channels.grid(row=1, column=0, sticky="w", padx=8, pady=3)

        self.lbl_prop_bitrate = tk.Label(grid_frame, text="Bitrate: —", font=(FONT_UI, 11), bg="#10192a", fg="#94a3b8")
        self.lbl_prop_bitrate.grid(row=1, column=1, sticky="w", padx=30, pady=3)

        self.lbl_prop_duration = tk.Label(grid_frame, text="Duration: —", font=(FONT_UI, 11), bg="#10192a", fg="#cbd5e1")
        self.lbl_prop_duration.grid(row=2, column=0, sticky="w", padx=8, pady=3)

        self.lbl_prop_size = tk.Label(grid_frame, text="File Size: —", font=(FONT_UI, 11), bg="#10192a", fg="#cbd5e1")
        self.lbl_prop_size.grid(row=2, column=1, sticky="w", padx=30, pady=3)

        # 5. Output Format & Settings Card
        format_card = tk.Frame(container, bg="#131d31", highlightbackground="#1e293b", highlightthickness=1)
        format_card.pack(fill="x", pady=(0, 10))

        tk.Label(
            format_card,
            text="Conversion / Extraction Settings",
            font=(FONT_UI, 13, "bold"),
            bg="#131d31",
            fg="#f1f5f9",
        ).pack(anchor="w", padx=18, pady=(10, 8))

        # Format option row
        fmt_row = tk.Frame(format_card, bg="#131d31")
        fmt_row.pack(fill="x", padx=18, pady=(0, 8))

        tk.Label(fmt_row, text="Target Format:", font=(FONT_UI, 11), bg="#131d31", fg="#94a3b8", width=16, anchor="w").pack(side="left")
        self.cb_format = ttk.Combobox(
            fmt_row,
            style="Dark.TCombobox",
            state="readonly",
            width=48,
            values=[
                "Apple ProRes 422 MOV (Final Cut Pro, Premiere & DaVinci Master)",
                "Calibrated MP4 (H.264 Universal Anti-Washout)",
                "Calibrated MP4 (HEVC / H.265 HDR/SDR)",
                "WAV (24-bit Studio PCM Uncompressed)",
                "WAV (16-bit Lossless PCM)",
                "MP3 (320 kbps Audiophile)",
                "AAC / M4A (256 kbps Studio)",
                "FLAC (Lossless Compressed)",
                "Opus (Stream Copy — Instant Bit-for-bit)",
            ],
        )
        self.cb_format.set("Apple ProRes 422 MOV (Final Cut Pro, Premiere & DaVinci Master)")
        self.cb_format.pack(side="left", padx=10)

        # Sample rate row
        sr_row = tk.Frame(format_card, bg="#131d31")
        sr_row.pack(fill="x", padx=18, pady=(0, 8))

        tk.Label(sr_row, text="Sample Rate (Audio):", font=(FONT_UI, 11), bg="#131d31", fg="#94a3b8", width=16, anchor="w").pack(side="left")
        self.cb_sample_rate = ttk.Combobox(
            sr_row,
            style="Dark.TCombobox",
            state="readonly",
            width=28,
            values=["Original", "48000", "44100", "96000"],
        )
        self.cb_sample_rate.set("Original")
        self.cb_sample_rate.pack(side="left", padx=10)

        # Destination Folder row
        dest_row = tk.Frame(format_card, bg="#131d31")
        dest_row.pack(fill="x", padx=18, pady=(0, 10))

        tk.Label(dest_row, text="Save Destination:", font=(FONT_UI, 11), bg="#131d31", fg="#94a3b8", width=16, anchor="w").pack(side="left")
        self.lbl_dest_folder = tk.Label(dest_row, text="Same as input file", font=(FONT_MONO, 10), bg="#131d31", fg="#38bdf8")
        self.lbl_dest_folder.pack(side="left", padx=(10, 16))

        self.btn_change_folder = ModernButton(
            dest_row,
            text="Change Folder",
            command=self._on_change_folder,
            bg_color="#1f293d",
            hover_color="#334155",
            font=(FONT_UI, 10),
            padx=10,
            pady=4,
        )
        self.btn_change_folder.pack(side="left")

        # 6. Action Button & Progress Card
        action_frame = tk.Frame(container, bg="#111827", highlightbackground="#1e293b", highlightthickness=1)
        action_frame.pack(fill="x", pady=(0, 10))

        self.btn_process = ModernButton(
            action_frame,
            text="⚡ START CONVERSION / EXTRACTION (ZERO QUALITY LOSS)",
            command=self._on_start_process,
            bg_color="#06b6d4",
            hover_color="#0891b2",
            text_color="#042f2e",
            font=(FONT_UI, 13, "bold"),
            padx=20,
            pady=12,
        )
        self.btn_process.pack(fill="x", padx=18, pady=(14, 10))

        # Progress bar
        self.prog_bar = ttk.Progressbar(action_frame, style="Cyan.Horizontal.TProgressbar", mode="determinate")
        self.prog_bar["value"] = 0
        self.prog_bar.pack(fill="x", padx=18, pady=(0, 8))

        # Status row
        stat_row = tk.Frame(action_frame, bg="#111827")
        stat_row.pack(fill="x", padx=18, pady=(0, 10))

        self.lbl_status = tk.Label(
            stat_row,
            text="Ready. Select a PS5 WebM file to begin.",
            font=(FONT_UI, 11),
            bg="#111827",
            fg="#94a3b8",
        )
        self.lbl_status.pack(side="left")

        self.lbl_speed = tk.Label(
            stat_row,
            text="",
            font=(FONT_MONO, 11, "bold"),
            bg="#111827",
            fg="#38bdf8",
        )
        self.lbl_speed.pack(side="right")

        # Success Action Buttons (initially hidden)
        self.success_row = tk.Frame(action_frame, bg="#111827")
        self.success_row.pack(fill="x", padx=18, pady=(0, 12))

        self.btn_play = ModernButton(
            self.success_row,
            text="▶ Play Output File",
            command=self._on_play_media,
            bg_color="#10b981",
            hover_color="#059669",
            font=(FONT_UI, 11, "bold"),
            padx=14,
            pady=6,
        )
        self.btn_play.pack(side="left", padx=(0, 10))

        open_lbl = "📁 Reveal in Finder" if IS_MAC else "📁 Show in Explorer"
        self.btn_open_folder = ModernButton(
            self.success_row,
            text=open_lbl,
            command=self._on_open_folder,
            bg_color="#1f293d",
            hover_color="#334155",
            font=(FONT_UI, 11),
            padx=14,
            pady=6,
        )
        self.btn_open_folder.pack(side="left")

        self.success_row.pack_forget()

    # --- Event Handlers ---

    def _on_browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select PS5 WebM Recording",
            filetypes=[
                ("WebM Video Files (*.webm)", "*.webm"),
                ("All Media Files (*.webm;*.mp4;*.mkv;*.mov;*.opus)", "*.webm;*.mp4;*.mkv;*.mov;*.opus"),
                ("All Files (*.*)", "*.*"),
            ],
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, path: str):
        try:
            self.lbl_status.configure(text="Scanning WebM media properties...", fg="#38bdf8")
            self.update_idletasks()
            meta = probe_webm(path)
            self.current_meta = meta
            self.output_dir = meta["file_dir"]

            self.lbl_selected_file.configure(text=f"Selected: {meta['file_name']}", fg="#f8fafc")
            self.lbl_dest_folder.configure(text=meta["file_dir"])

            a = meta["audio"]
            self.lbl_prop_codec.configure(text=f"Audio Codec: {a['codec']} (PS5 Master)")
            self.lbl_prop_sample_rate.configure(text=f"Sample Rate: {a['sample_rate']:,} Hz")
            self.lbl_prop_channels.configure(text=f"Channels: {a['channel_label']}")
            self.lbl_prop_bitrate.configure(text=f"Bitrate: {a['bitrate_kbps']} kbps")
            self.lbl_prop_duration.configure(text=f"Duration: {meta['duration_formatted']}")
            self.lbl_prop_size.configure(text=f"File Size: {meta['file_size_formatted']}")

            self.lbl_status.configure(text="Ready! Select target format and click Start Conversion.", fg="#34d399")
            self.prog_bar["value"] = 0
            self.lbl_speed.configure(text="")
            self.success_row.pack_forget()

        except Exception as e:
            messagebox.showerror("Scan Error", f"Failed to inspect file:\n{str(e)}")
            self.lbl_status.configure(text="Error inspecting file.", fg="#f87171")

    def _on_change_folder(self):
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.output_dir = folder
            self.lbl_dest_folder.configure(text=folder)

    def _on_start_process(self):
        if not self.current_meta:
            messagebox.showwarning("No File", "Please select a PS5 WebM file first.")
            return

        if self.worker and self.worker.is_alive():
            messagebox.showinfo("In Progress", "Processing is already running.")
            return

        fmt = self.cb_format.get()
        sr = self.cb_sample_rate.get()
        inp = self.current_meta["file_path"]
        dur = self.current_meta["duration_sec"]

        self.btn_process.set_state("disabled", "⏳ PROCESSING (FAST)...")
        self.lbl_status.configure(text="Processing media stream...", fg="#38bdf8")
        self.prog_bar["value"] = 0
        self.lbl_speed.configure(text="")
        self.success_row.pack_forget()

        self.worker = MediaProcessWorker(
            input_file=inp,
            output_format=fmt,
            sample_rate=sr,
            output_dir=self.output_dir,
            total_duration=dur,
            on_progress=self._on_worker_progress,
            on_done=self._on_worker_done,
        )
        self.worker.start()

    def _on_worker_progress(self, pct: float, cur_sec: float, speed_val: str, action_verb: str):
        self.after(0, self._update_progress_ui, pct, cur_sec, speed_val, action_verb)

    def _update_progress_ui(self, pct: float, cur_sec: float, speed_val: str, action_verb: str):
        self.prog_bar["value"] = pct * 100
        dur = self.current_meta["duration_sec"] if self.current_meta else 0
        cur_fmt = format_duration(cur_sec)
        dur_fmt = format_duration(dur)
        self.lbl_status.configure(
            text=f"{action_verb}: {cur_fmt} / {dur_fmt} ({int(pct * 100)}%)",
            fg="#38bdf8",
        )
        self.lbl_speed.configure(text=f"Speed: {speed_val}")

    def _on_worker_done(self, success: bool, message: str, output_file: str, elapsed: float):
        self.after(0, self._handle_done_ui, success, message, output_file, elapsed)

    def _handle_done_ui(self, success: bool, message: str, output_file: str, elapsed: float):
        self.btn_process.set_state("normal", "⚡ START CONVERSION / EXTRACTION (ZERO QUALITY LOSS)")
        if success:
            self.last_output_file = output_file
            self.prog_bar["value"] = 100
            self.lbl_status.configure(
                text=f"✔ Complete in {elapsed:.2f}s! Saved: {os.path.basename(output_file)}",
                fg="#34d399",
            )
            self.lbl_speed.configure(text="")
            self.success_row.pack(fill="x", padx=18, pady=(0, 12))
        else:
            self.lbl_status.configure(text="Processing failed.", fg="#f87171")
            messagebox.showerror("Error", message)

    def _on_play_media(self):
        if self.last_output_file and os.path.exists(self.last_output_file):
            try:
                norm = os.path.normpath(self.last_output_file)
                if sys.platform.startswith("win"):
                    os.startfile(norm)
                elif sys.platform == "darwin":
                    subprocess.run(["open", norm], check=False)
                else:
                    subprocess.run(["xdg-open", norm], check=False)
            except Exception as e:
                messagebox.showerror("Play Error", str(e))

    def _on_open_folder(self):
        if self.last_output_file and os.path.exists(self.last_output_file):
            try:
                norm = os.path.normpath(self.last_output_file)
                if sys.platform.startswith("win"):
                    subprocess.run(["explorer", f"/select,{norm}"], check=False)
                elif sys.platform == "darwin":
                    subprocess.run(["open", "-R", norm], check=False)
                else:
                    subprocess.run(["xdg-open", os.path.dirname(norm)], check=False)
            except Exception as e:
                messagebox.showerror("Folder Error", str(e))


def main():
    app = GLVMediaConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
