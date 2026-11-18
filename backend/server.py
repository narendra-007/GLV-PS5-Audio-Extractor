"""
server.py - Async Web & WebSocket API Server for GLV Convertor
Provides REST endpoints, native Windows file dialogs, and real-time WebSocket progress.
"""

import asyncio
import json
import os
import subprocess
import threading
import uuid
from typing import Any, Dict, Set

from aiohttp import WSMsgType, web

from .converter import ConversionJob
from .media_probe import probe_file
from .presets import (
    AUDIO_FORMATS,
    QUALITY_PRESETS,
    VIDEO_FORMATS,
    detect_hardware_encoders,
)

# Active conversion jobs and connected WebSocket clients
active_jobs: Dict[str, ConversionJob] = {}
latest_job_states: Dict[str, Dict[str, Any]] = {}
ws_clients: Set[web.WebSocketResponse] = set()


def run_file_dialog(file_types: list, title: str = "Select WebM or Video File") -> str:
    """Run native file picker dialog (Tkinter with AppleScript fallback on macOS)."""
    result = [""]

    def _open():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askopenfilename(
                title=title,
                filetypes=file_types,
            )
            root.destroy()
            if selected:
                result[0] = os.path.normpath(selected)
        except Exception:
            pass

    t = threading.Thread(target=_open)
    t.start()
    t.join(timeout=60)

    # Native macOS AppleScript fallback if Tkinter is not installed or headless
    if not result[0] and sys.platform == "darwin":
        try:
            script = f'POSIX path of (choose file with prompt "{title}")'
            proc = subprocess.run(["osascript", "-e", script], stdout=subprocess.PIPE, text=True, check=False)
            if proc.returncode == 0 and proc.stdout.strip():
                result[0] = os.path.normpath(proc.stdout.strip())
        except Exception:
            pass

    return result[0]


def run_folder_dialog(title: str = "Select Destination Folder") -> str:
    """Run native folder picker dialog (Tkinter with AppleScript fallback on macOS)."""
    result = [""]

    def _open():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askdirectory(title=title)
            root.destroy()
            if selected:
                result[0] = os.path.normpath(selected)
        except Exception:
            pass

    t = threading.Thread(target=_open)
    t.start()
    t.join(timeout=60)

    # Native macOS AppleScript fallback
    if not result[0] and sys.platform == "darwin":
        try:
            script = f'POSIX path of (choose folder with prompt "{title}")'
            proc = subprocess.run(["osascript", "-e", script], stdout=subprocess.PIPE, text=True, check=False)
            if proc.returncode == 0 and proc.stdout.strip():
                result[0] = os.path.normpath(proc.stdout.strip())
        except Exception:
            pass

    return result[0]


async def broadcast_ws(message: Dict[str, Any]):
    """Broadcast JSON message to all connected WebSocket clients."""
    if not ws_clients:
        return
    text = json.dumps(message)
    dead_clients = set()
    for ws in list(ws_clients):
        if ws.closed:
            dead_clients.add(ws)
        else:
            try:
                await ws.send_str(text)
            except Exception:
                dead_clients.add(ws)
    for ws in dead_clients:
        ws_clients.discard(ws)


def on_progress_callback(data: Dict[str, Any]):
    """Called by ConversionJob thread; dispatches update to asyncio event loop."""
    job_id = data.get("job_id", "")
    if job_id:
        latest_job_states[job_id] = data

    loop = getattr(on_progress_callback, "_loop", None)
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(
            broadcast_ws({"type": "progress", "data": data}),
            loop,
        )


# --- REST Handlers ---

async def handle_index(request: web.Request) -> web.FileResponse:
    """Serve the single page application HTML."""
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    index_file = os.path.join(frontend_dir, "index.html")
    return web.FileResponse(index_file)


async def handle_system_info(request: web.Request) -> web.Response:
    """Return hardware encoder support, GPU information, and presets."""
    hw = detect_hardware_encoders()
    return web.json_response({
        "status": "ok",
        "hardware": hw,
        "video_formats": VIDEO_FORMATS,
        "audio_formats": AUDIO_FORMATS,
        "quality_presets": QUALITY_PRESETS,
    })


async def handle_probe(request: web.Request) -> web.Response:
    """Deep inspect the specified file path."""
    try:
        body = await request.json()
        file_path = body.get("file_path", "").strip()
        if not file_path or not os.path.exists(file_path):
            return web.json_response({"status": "error", "message": "File does not exist."}, status=400)

        metadata = probe_file(file_path)
        return web.json_response({"status": "ok", "metadata": metadata})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def handle_pick_file(request: web.Request) -> web.Response:
    """Trigger native Windows file dialog."""
    filetypes = [
        ("WebM & Media Files (*.webm;*.mp4;*.mkv;*.mov;*.flv;*.avi;*.opus;*.ogg)", "*.webm;*.mp4;*.mkv;*.mov;*.flv;*.avi;*.opus;*.ogg"),
        ("WebM Video Files (*.webm)", "*.webm"),
        ("All Video Files (*.mp4;*.mkv;*.mov;*.avi;*.flv;*.wmv;*.ts)", "*.mp4;*.mkv;*.mov;*.avi;*.flv;*.wmv;*.ts"),
        ("All Audio Files (*.opus;*.ogg;*.mp3;*.m4a;*.wav;*.flac)", "*.opus;*.ogg;*.mp3;*.m4a;*.wav;*.flac"),
        ("All Files (*.*)", "*.*"),
    ]
    file_path = await asyncio.to_thread(run_file_dialog, filetypes, "Select WebM or Media File")
    if file_path:
        try:
            metadata = probe_file(file_path)
            return web.json_response({"status": "ok", "file_path": file_path, "metadata": metadata})
        except Exception as e:
            return web.json_response({"status": "ok", "file_path": file_path, "error": str(e)})
    return web.json_response({"status": "cancelled", "file_path": ""})


async def handle_pick_folder(request: web.Request) -> web.Response:
    """Trigger native Windows folder picker dialog."""
    folder = await asyncio.to_thread(run_folder_dialog, "Select Output Destination Folder")
    if folder:
        return web.json_response({"status": "ok", "folder_path": folder})
    return web.json_response({"status": "cancelled", "folder_path": ""})


async def handle_convert(request: web.Request) -> web.Response:
    """Initiate a media conversion job."""
    try:
        options = await request.json()
        input_path = options.get("input_path", "").strip()
        if not input_path or not os.path.exists(input_path):
            return web.json_response({"status": "error", "message": "Input file not found."}, status=400)

        # Compute default output path if not explicitly provided
        output_path = options.get("output_path", "").strip()
        if not output_path:
            out_dir = options.get("output_dir") or os.path.dirname(input_path)
            mode = options.get("mode", "video")
            format_id = options.get("format_id", "mp4-h264")

            base_name = os.path.splitext(os.path.basename(input_path))[0]
            # Determine extension
            ext = "mp4"
            if mode == "audio":
                ext = options.get("audio_format", "mp3").lower()
            else:
                for vf in VIDEO_FORMATS:
                    if vf["id"] == format_id:
                        ext = vf["ext"]
                        break

            output_filename = f"{base_name}_converted.{ext}"
            output_path = os.path.join(out_dir, output_filename)
            options["output_path"] = output_path

        job_id = str(uuid.uuid4())
        job = ConversionJob(job_id, options, progress_callback=on_progress_callback)
        active_jobs[job_id] = job
        job.start()

        return web.json_response({
            "status": "started",
            "job_id": job_id,
            "output_path": output_path,
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def handle_cancel(request: web.Request) -> web.Response:
    """Cancel an active conversion."""
    body = await request.json()
    job_id = body.get("job_id", "")
    job = active_jobs.get(job_id)
    if job:
        job.cancel()
        return web.json_response({"status": "cancelled", "job_id": job_id})
    return web.json_response({"status": "not_found"}, status=404)


async def handle_job_status(request: web.Request) -> web.Response:
    """Get the current progress status of a job (for polling fallback)."""
    job_id = request.query.get("id", "")
    if job_id in latest_job_states:
        return web.json_response({"status": "ok", "data": latest_job_states[job_id]})
    return web.json_response({"status": "not_found"}, status=404)


async def handle_open_file(request: web.Request) -> web.Response:
    """Open the file in the default OS player/application (cross-platform: macOS, Windows, Linux)."""
    body = await request.json()
    path = body.get("path", "")
    if path and os.path.exists(path):
        try:
            norm_path = os.path.normpath(path)
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", norm_path], check=False)
            elif sys.platform.startswith("win"):  # Windows
                os.startfile(norm_path)
            else:  # Linux
                subprocess.run(["xdg-open", norm_path], check=False)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)
    return web.json_response({"status": "error", "message": "File not found"}, status=404)


async def handle_open_folder(request: web.Request) -> web.Response:
    """Open OS file manager with the specific file highlighted (cross-platform: macOS Finder, Windows Explorer, Linux)."""
    body = await request.json()
    path = body.get("path", "")
    if path and os.path.exists(path):
        try:
            norm_path = os.path.normpath(path)
            if sys.platform == "darwin":  # macOS Finder
                subprocess.run(["open", "-R", norm_path], check=False)
            elif sys.platform.startswith("win"):  # Windows Explorer
                subprocess.run(["explorer", f"/select,{norm_path}"], check=False)
            else:  # Linux file manager
                subprocess.run(["xdg-open", os.path.dirname(norm_path)], check=False)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)
    return web.json_response({"status": "error", "message": "Path not found"}, status=404)


# --- WebSocket Handler ---

async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    """Manage WebSocket connections for live 60fps telemetry."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_clients.add(ws)

    # Send current hardware status on connection
    try:
        hw = detect_hardware_encoders()
        await ws.send_str(json.dumps({"type": "init", "hardware": hw}))
    except Exception:
        pass

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                # Can handle client pings if needed
                pass
            elif msg.type == WSMsgType.ERROR:
                pass
    finally:
        ws_clients.discard(ws)

    return ws


def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

    # Routes
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/system-info", handle_system_info)
    app.router.add_post("/api/probe", handle_probe)
    app.router.add_post("/api/pick-file", handle_pick_file)
    app.router.add_post("/api/pick-folder", handle_pick_folder)
    app.router.add_post("/api/convert", handle_convert)
    app.router.add_post("/api/cancel", handle_cancel)
    app.router.add_get("/api/job-status", handle_job_status)
    app.router.add_post("/api/open-file", handle_open_file)
    app.router.add_post("/api/open-folder", handle_open_folder)
    app.router.add_get("/ws/progress", handle_ws)

    # Static assets
    app.router.add_static("/static", frontend_dir, show_index=True)

    return app
