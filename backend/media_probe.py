"""
media_probe.py - Deep Media & Color Science Inspector
Scans WebM and any media file via ffprobe, extracting comprehensive video,
audio, container, and color science properties (color primaries, transfer, matrix, range).
"""

import json
import os
import shutil
import subprocess
from typing import Any, Dict, Optional


def find_binary(binary_name: str) -> str:
    """Find the path of a binary (ffprobe, ffmpeg) on the system PATH."""
    path = shutil.which(binary_name)
    if path:
        return path
    # Common OS fallback paths (Windows, macOS Homebrew, Linux)
    common_paths = [
        rf"C:\ffmpeg\bin\{binary_name}.exe",
        rf"C:\Program Files\ffmpeg\bin\{binary_name}.exe",
        f"/opt/homebrew/bin/{binary_name}",  # macOS Apple Silicon (M1/M2/M3/M4)
        f"/usr/local/bin/{binary_name}",     # macOS Intel / Homebrew
        f"/usr/bin/{binary_name}",           # Linux / Ubuntu
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return binary_name


def format_duration(seconds: float) -> str:
    """Format duration in seconds into HH:MM:SS or MM:SS."""
    if seconds <= 0:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    millis = int((seconds - int(seconds)) * 100)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}.{millis:02d}"
    return f"{m:02d}:{s:02d}.{millis:02d}"


def format_bytes(bytes_count: int) -> str:
    """Format bytes count into human-readable string (KB, MB, GB)."""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        return f"{bytes_count / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_count / (1024 * 1024 * 1024):.2f} GB"


def parse_fraction(frac_str: Optional[str]) -> float:
    """Parse fraction string like '30/1' or '60000/1001' into float."""
    if not frac_str or frac_str == "0/0":
        return 0.0
    try:
        if "/" in frac_str:
            num, den = frac_str.split("/")
            den_f = float(den)
            return round(float(num) / den_f, 2) if den_f != 0 else 0.0
        return round(float(frac_str), 2)
    except Exception:
        return 0.0


def probe_file(file_path: str) -> Dict[str, Any]:
    """
    Perform a deep scan on the file using ffprobe.
    Returns structured metadata including video, audio, container,
    and color preservation recommendations.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ffprobe_cmd = [
        find_binary("ffprobe"),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-show_error",
        file_path,
    ]

    try:
        result = subprocess.run(
            ffprobe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        raw_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFprobe failed to inspect file: {e.stderr or str(e)}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON returned by ffprobe: {str(e)}")

    format_info = raw_data.get("format", {})
    streams = raw_data.get("streams", [])

    file_size_bytes = int(format_info.get("size", os.path.getsize(file_path)))
    duration_sec = float(format_info.get("duration", 0.0))
    overall_bitrate = int(format_info.get("bit_rate", 0))

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    video_meta: Optional[Dict[str, Any]] = None
    if video_streams:
        v = video_streams[0]
        width = int(v.get("width", 0))
        height = int(v.get("height", 0))
        fps = parse_fraction(v.get("avg_frame_rate")) or parse_fraction(v.get("r_frame_rate"))
        pix_fmt = v.get("pix_fmt", "unknown")

        # Color science attributes
        color_space = v.get("color_space", "unknown")
        color_primaries = v.get("color_primaries", "unknown")
        color_trc = v.get("color_trc", "unknown")
        color_range = v.get("color_range", "unknown")
        chroma_location = v.get("chroma_location", "unspecified")

        # Derive resolution tag
        res_label = "Custom"
        if width >= 3800 and height >= 2100:
            res_label = "4K UHD"
        elif width >= 2500 and height >= 1400:
            res_label = "1440p QHD"
        elif width >= 1900 and height >= 1050:
            res_label = "1080p FHD"
        elif width >= 1260 and height >= 700:
            res_label = "720p HD"
        elif width > 0 and height > 0:
            res_label = f"{width}x{height}"

        # Detect bit depth
        bit_depth = 8
        if "10" in pix_fmt:
            bit_depth = 10
        elif "12" in pix_fmt:
            bit_depth = 12

        # Check HDR status
        is_hdr = (
            color_trc in ["smpte2084", "arib-std-b67"] or
            color_primaries == "bt2020" or
            bit_depth > 8
        )

        # Check alpha channel (transparent WebM)
        has_alpha = "yuva" in pix_fmt or "rgba" in pix_fmt or "gbra" in pix_fmt

        v_bitrate = int(v.get("bit_rate", 0))
        if v_bitrate == 0 and overall_bitrate > 0:
            v_bitrate = int(overall_bitrate * 0.85)

        video_meta = {
            "index": v.get("index", 0),
            "codec": v.get("codec_name", "unknown").upper(),
            "codec_long_name": v.get("codec_long_name", ""),
            "profile": v.get("profile", "Main"),
            "width": width,
            "height": height,
            "resolution_label": res_label,
            "aspect_ratio": v.get("display_aspect_ratio", f"{width}:{height}" if width and height else "N/A"),
            "fps": fps,
            "bitrate_kbps": round(v_bitrate / 1000) if v_bitrate else None,
            "pix_fmt": pix_fmt,
            "bit_depth": bit_depth,
            "color_space": color_space,
            "color_primaries": color_primaries,
            "color_trc": color_trc,
            "color_range": color_range,
            "chroma_location": chroma_location,
            "is_hdr": is_hdr,
            "has_alpha": has_alpha,
            "frames": int(v.get("nb_frames", 0)) if v.get("nb_frames") else None,
        }

    audio_meta: Optional[Dict[str, Any]] = None
    if audio_streams:
        a = audio_streams[0]
        sample_rate = int(a.get("sample_rate", 0))
        channels = int(a.get("channels", 0))
        channel_layout = a.get("channel_layout", "stereo" if channels == 2 else "mono" if channels == 1 else f"{channels}ch")
        
        # Audio human label
        chan_label = "Stereo (2.0)"
        if channels == 1:
            chan_label = "Mono (1.0)"
        elif channels == 6:
            chan_label = "5.1 Surround"
        elif channels == 8:
            chan_label = "7.1 Surround"
        elif channels > 2:
            chan_label = f"{channels} Channels"

        a_bitrate = int(a.get("bit_rate", 0))
        if a_bitrate == 0 and overall_bitrate > 0:
            a_bitrate = int(overall_bitrate * 0.15)

        audio_meta = {
            "index": a.get("index", 1),
            "codec": a.get("codec_name", "unknown").upper(),
            "codec_long_name": a.get("codec_long_name", ""),
            "sample_rate_hz": sample_rate,
            "sample_rate_khz": round(sample_rate / 1000, 1) if sample_rate else None,
            "channels": channels,
            "channel_layout": channel_layout,
            "channel_label": chan_label,
            "bitrate_kbps": round(a_bitrate / 1000) if a_bitrate else None,
            "sample_fmt": a.get("sample_fmt", "fltp"),
            "bits_per_sample": a.get("bits_per_sample", 0),
        }

    # Generate smart tips and color analysis
    recommendations = []
    if video_meta:
        codec = video_meta["codec"]
        if codec in ["VP9", "VP8", "AV1"]:
            recommendations.append(
                "Source is WebM format. When converting to MP4, standard players require H.264/AAC with explicit BT.709 color tagging to preserve accurate color saturation and prevent gamma shifts."
            )
        if video_meta["color_range"] == "pc":
            recommendations.append(
                "Full Range (PC: 0-255) detected. Color matrix tags will be locked to prevent crushed blacks or blown-out highlights."
            )
        if video_meta["is_hdr"]:
            recommendations.append(
                "HDR / 10-bit color detected. High dynamic range transfer curves will be preserved."
            )
        if video_meta["has_alpha"]:
            recommendations.append(
                "Alpha transparency channel detected in video stream."
            )

    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1].lower().replace(".", "")

    return {
        "file_path": os.path.abspath(file_path),
        "file_name": filename,
        "file_dir": os.path.dirname(os.path.abspath(file_path)),
        "file_ext": file_ext,
        "file_size_bytes": file_size_bytes,
        "file_size_formatted": format_bytes(file_size_bytes),
        "duration_sec": duration_sec,
        "duration_formatted": format_duration(duration_sec),
        "overall_bitrate_kbps": round(overall_bitrate / 1000) if overall_bitrate else None,
        "format_name": format_info.get("format_name", ""),
        "format_long_name": format_info.get("format_long_name", ""),
        "stream_count": len(streams),
        "has_video": video_meta is not None,
        "has_audio": audio_meta is not None,
        "video": video_meta,
        "audio": audio_meta,
        "recommendations": recommendations,
        "raw_streams": streams,
    }


if __name__ == "__main__":
    import sys
    test_file = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Narandra\.gemini\antigravity\scratch\sample_test\sample_video.webm"
    if os.path.exists(test_file):
        data = probe_file(test_file)
        print(json.dumps(data, indent=2))
    else:
        print(f"Usage: python media_probe.py <file>")
