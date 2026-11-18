"""
web_app.py - GLV PS5 Audio Extractor (Web Edition)
A zero-dependency local web application engineered for macOS, Windows, and Linux.
Runs locally in any browser (Safari, Chrome, Firefox) without GUI rendering issues.
"""

import http.server
import json
import os
import re
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
import webbrowser
from typing import Any, Dict, Optional, Tuple

PORT = 5050
HOST = "127.0.0.1"

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
TEMP_UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "glv_uploads")
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

# Active extraction jobs
jobs: Dict[str, Dict[str, Any]] = {}


# --- FFmpeg & Binary Resolution ---

def find_binary(binary_name: str) -> str:
    """Locate binary on system PATH or standard OS directories."""
    ext = ".exe" if sys.platform.startswith("win") else ""
    local_path = os.path.join(BASE_DIR, f"{binary_name}{ext}")
    if os.path.exists(local_path):
        return local_path

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
    if seconds <= 0:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    millis = int((seconds - int(seconds)) * 100)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}.{millis:02d}"
    return f"{m:02d}:{s:02d}.{millis:02d}"


def format_bytes(bytes_count: int) -> str:
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"


def probe_webm(file_path: str) -> Dict[str, Any]:
    """Scan WebM file with ffprobe and extract deep audio properties."""
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

    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    audio_info = {
        "codec": "N/A",
        "sample_rate": 0,
        "channels": 0,
        "channel_label": "Stereo",
        "bitrate_kbps": 0,
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
    }


def pick_native_file() -> str:
    """Prompt native file selection dialog on macOS or Windows."""
    if sys.platform == "darwin":
        script = 'POSIX path of (choose file with prompt "Select PS5 WebM Recording")'
        try:
            proc = subprocess.run(["osascript", "-e", script], stdout=subprocess.PIPE, text=True, check=False)
            path = proc.stdout.strip()
            return path if os.path.exists(path) else ""
        except Exception:
            return ""
    else:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askopenfilename(
                title="Select PS5 WebM Recording",
                filetypes=[("WebM Files (*.webm)", "*.webm"), ("All Files (*.*)", "*.*")],
            )
            root.destroy()
            return selected or ""
        except Exception:
            return ""


def parse_multipart(body_bytes: bytes, boundary: str) -> Tuple[Optional[str], Optional[bytes]]:
    """Parse single file upload from multipart/form-data body."""
    sep = b"--" + boundary.encode("utf-8")
    parts = body_bytes.split(sep)
    for part in parts:
        if b"Content-Disposition" in part and b"filename=" in part:
            header, content = part.split(b"\r\n\r\n", 1)
            if content.endswith(b"\r\n"):
                content = content[:-2]
            header_str = header.decode("utf-8", errors="ignore")
            m = re.search(r'filename="?([^";\r\n]+)"?', header_str)
            fn = m.group(1).strip() if m else "uploaded.webm"
            return fn, content
    return None, None


# --- Extraction Worker Thread ---

def run_extraction_worker(job_id: str, file_path: str, fmt: str, sample_rate: str):
    job = jobs[job_id]
    start_time = time.time()
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = os.path.dirname(file_path)
    ffmpeg_bin = find_binary("ffmpeg")

    ext = ".wav"
    audio_codec_args = []

    if "WAV (24-bit Studio PCM)" in fmt:
        ext = "_PS5_Audio_24bit.wav"
        audio_codec_args = ["-c:a", "pcm_s24le"]
    elif "WAV (16-bit Lossless PCM)" in fmt:
        ext = "_PS5_Audio_16bit.wav"
        audio_codec_args = ["-c:a", "pcm_s16le"]
    elif "MP3 (320 kbps Audiophile)" in fmt:
        ext = "_PS5_Audio_320k.mp3"
        audio_codec_args = ["-c:a", "libmp3lame", "-b:a", "320k", "-q:a", "0"]
    elif "AAC / M4A (256 kbps Studio)" in fmt:
        ext = "_PS5_Audio_256k.m4a"
        audio_codec_args = ["-c:a", "aac", "-b:a", "256k"]
    elif "FLAC (Lossless Compressed)" in fmt:
        ext = "_PS5_Audio.flac"
        audio_codec_args = ["-c:a", "flac", "-compression_level", "8"]
    elif "Opus (Stream Copy)" in fmt:
        ext = "_PS5_Audio_Original.opus"
        audio_codec_args = ["-c:a", "copy"]
    else:
        ext = "_PS5_Audio.wav"
        audio_codec_args = ["-c:a", "pcm_s24le"]

    output_file = os.path.join(output_dir, f"{base_name}{ext}")
    job["output_file"] = output_file
    job["output_filename"] = os.path.basename(output_file)

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", file_path,
        "-vn",
    ]
    cmd.extend(audio_codec_args)

    if sample_rate and sample_rate != "Original" and "-c:a copy" not in " ".join(audio_codec_args):
        cmd.extend(["-ar", sample_rate])

    cmd.extend([
        "-progress", "pipe:1",
        "-nostats",
        output_file,
    ])

    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=startupinfo,
        )

        total_dur = job.get("total_duration", 0.0)
        speed_val = "1.0x"

        while True:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue

            line = line.strip()
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "out_time_us":
                    try:
                        out_us = int(v)
                        cur_sec = out_us / 1_000_000.0
                        pct = min(cur_sec / total_dur, 1.0) if total_dur > 0 else 0.5
                        job["progress"] = pct
                        job["current_sec"] = cur_sec
                        job["status_message"] = f"Extracting: {format_duration(cur_sec)} / {format_duration(total_dur)} ({int(pct*100)}%)"
                    except ValueError:
                        pass
                elif k == "speed":
                    speed_val = v
                    job["speed"] = v
                elif k == "progress" and v == "end":
                    job["progress"] = 1.0

        ret = proc.wait()
        elapsed = time.time() - start_time
        job["elapsed"] = elapsed
        job["done"] = True

        if ret == 0:
            job["success"] = True
            job["status_message"] = f"✔ Extracted successfully in {elapsed:.2f}s!"
        else:
            stderr_out = proc.stderr.read() if proc.stderr else ""
            job["success"] = False
            job["error"] = stderr_out[:300] or f"FFmpeg exited with code {ret}"
    except Exception as e:
        job["done"] = True
        job["success"] = False
        job["error"] = str(e)


# --- HTTP Request Handler ---

class AppRequestHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def send_json(self, data: Dict[str, Any], status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            index_path = os.path.join(WEB_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")

        elif path == "/api/progress":
            qs = urllib.parse.parse_qs(parsed.query)
            job_id = qs.get("id", [""])[0]
            if job_id in jobs:
                self.send_json(jobs[job_id])
            else:
                self.send_json({"error": "Job not found"}, status=404)

        elif path == "/api/download":
            qs = urllib.parse.parse_qs(parsed.query)
            target_file = qs.get("file", [""])[0]
            if target_file and os.path.exists(target_file):
                filename = os.path.basename(target_file)
                file_size = os.path.getsize(target_file)

                ct = "audio/wav"
                if target_file.endswith(".mp3"):
                    ct = "audio/mpeg"
                elif target_file.endswith(".m4a") or target_file.endswith(".aac"):
                    ct = "audio/mp4"
                elif target_file.endswith(".flac"):
                    ct = "audio/flac"
                elif target_file.endswith(".opus"):
                    ct = "audio/opus"

                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(target_file, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/select-file":
            selected = pick_native_file()
            if selected and os.path.exists(selected):
                try:
                    meta = probe_webm(selected)
                    self.send_json(meta)
                except Exception as e:
                    self.send_json({"error": str(e)}, status=400)
            else:
                self.send_json({"cancelled": True})

        elif path == "/api/probe":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            data = json.loads(body.decode("utf-8"))
            file_path = data.get("file_path", "")
            try:
                meta = probe_webm(file_path)
                self.send_json(meta)
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)

        elif path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            content_len = int(self.headers.get("Content-Length", 0))
            if "multipart/form-data" in content_type and "boundary=" in content_type:
                boundary = content_type.split("boundary=")[1].strip()
                body = self.rfile.read(content_len)
                fn, file_bytes = parse_multipart(body, boundary)
                if fn and file_bytes:
                    save_path = os.path.join(TEMP_UPLOAD_DIR, fn)
                    with open(save_path, "wb") as f:
                        f.write(file_bytes)
                    try:
                        meta = probe_webm(save_path)
                        self.send_json(meta)
                        return
                    except Exception as e:
                        self.send_json({"error": str(e)}, status=400)
                        return
            self.send_json({"error": "No file uploaded or invalid format"}, status=400)

        elif path == "/api/extract":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            data = json.loads(body.decode("utf-8"))

            file_path = data.get("file_path", "")
            fmt = data.get("format", "WAV (24-bit Studio PCM)")
            sr = data.get("sample_rate", "Original")

            if not os.path.exists(file_path):
                self.send_json({"error": "File does not exist"}, status=400)
                return

            try:
                meta = probe_webm(file_path)
                job_id = str(uuid.uuid4())[:8]
                jobs[job_id] = {
                    "job_id": job_id,
                    "file_path": file_path,
                    "total_duration": meta["duration_sec"],
                    "progress": 0.0,
                    "speed": "",
                    "status_message": "Initializing extraction...",
                    "done": False,
                    "success": False,
                    "error": "",
                    "output_file": "",
                    "output_filename": "",
                    "elapsed": 0.0,
                }

                t = threading.Thread(
                    target=run_extraction_worker,
                    args=(job_id, file_path, fmt, sr),
                    daemon=True,
                )
                t.start()

                self.send_json({"job_id": job_id})
            except Exception as e:
                self.send_json({"error": str(e)}, status=500)

        elif path == "/api/reveal":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            data = json.loads(body.decode("utf-8"))
            file_path = data.get("file_path", "")
            if file_path and os.path.exists(file_path):
                norm = os.path.normpath(file_path)
                if sys.platform == "darwin":
                    subprocess.run(["open", "-R", norm], check=False)
                elif sys.platform.startswith("win"):
                    subprocess.run(["explorer", f"/select,{norm}"], check=False)
                else:
                    subprocess.run(["xdg-open", os.path.dirname(norm)], check=False)
                self.send_json({"success": True})
            else:
                self.send_json({"error": "File not found"}, status=404)
        else:
            self.send_error(404, "Not Found")


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def get_free_port(start_port: int = 5050) -> int:
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) != 0:
                return port
    return start_port


def main():
    port = get_free_port(PORT)
    server_url = f"http://{HOST}:{port}"

    print("=========================================================")
    print("  🎮 GLV PS5 Audio Extractor — Web Edition")
    print("=========================================================")
    print(f"  Server running locally at: {server_url}")
    print("  Opening default browser...")
    print("  Press Ctrl+C to stop the server.")
    print("=========================================================")

    threading.Timer(0.8, lambda: webbrowser.open(server_url)).start()

    server = ThreadedHTTPServer((HOST, port), AppRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down GLV server. Goodbye!")
        server.server_close()


if __name__ == "__main__":
    main()
