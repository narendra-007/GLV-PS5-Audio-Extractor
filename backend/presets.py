"""
presets.py - Preset Definitions, Format Specifications & Hardware Detection
Defines high-speed and visually lossless profiles for Video + Audio and Audio-Only conversions.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, List


def detect_hardware_encoders() -> Dict[str, Any]:
    """
    Query ffmpeg to detect which hardware acceleration engines are compiled and available.
    Supports NVIDIA NVENC, Intel QSV, AMD AMF, and Windows MediaFoundation.
    """
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    nvenc_available = False
    qsv_available = False
    amf_available = False
    mf_available = False
    vt_available = False
    active_gpu_name = "CPU Multi-Core"

    # Check for NVIDIA GPU via nvidia-smi
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            res = subprocess.run(
                [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                active_gpu_name = res.stdout.strip().split("\n")[0]
                nvenc_available = True
        except Exception:
            pass

    # Query ffmpeg encoders
    try:
        proc = subprocess.run(
            [ffmpeg_bin, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        out = proc.stdout
        if "h264_nvenc" in out and nvenc_available:
            nvenc_available = True
        elif "h264_nvenc" in out and not nvenc_available:
            # NVENC compiled, check if card handles it
            nvenc_available = True
        if "h264_qsv" in out:
            qsv_available = True
        if "h264_amf" in out:
            amf_available = True
        if "h264_mf" in out:
            mf_available = True
        if "h264_videotoolbox" in out:
            vt_available = True
            active_gpu_name = "Apple Silicon VideoToolbox"
    except Exception:
        pass

    best_hw = "cpu"
    if vt_available:
        best_hw = "videotoolbox"
    elif nvenc_available:
        best_hw = "nvenc"
    elif qsv_available:
        best_hw = "qsv"
    elif amf_available:
        best_hw = "amf"
    elif mf_available:
        best_hw = "mf"

    return {
        "best_hardware": best_hw,
        "nvenc": nvenc_available,
        "videotoolbox": vt_available,
        "qsv": qsv_available,
        "amf": amf_available,
        "mf": mf_available,
        "gpu_name": active_gpu_name,
    }


# Video + Audio Container & Codec Presets
VIDEO_FORMATS = [
    {
        "id": "mp4-h264",
        "name": "MP4 (H.264 / AVC)",
        "ext": "mp4",
        "badge": "Universal Compatible",
        "description": "Maximum compatibility for mobile, web, smart TVs, and editing suites.",
        "icon": "film",
        "default_vcodec": "libx264",
        "nvenc_vcodec": "h264_nvenc",
        "default_acodec": "aac",
        "default_abitrate": "256k",
        "supports_hw": True,
        "supports_remux": False,
    },
    {
        "id": "mp4-hevc",
        "name": "MP4 (H.265 / HEVC)",
        "ext": "mp4",
        "badge": "Ultra High Efficiency",
        "description": "50% smaller file size with equivalent or superior quality. Great for 4K/HDR.",
        "icon": "zap",
        "default_vcodec": "libx265",
        "nvenc_vcodec": "hevc_nvenc",
        "default_acodec": "aac",
        "default_abitrate": "256k",
        "supports_hw": True,
        "supports_remux": False,
    },
    {
        "id": "mkv-remux",
        "name": "MKV (Lossless Remux / Master)",
        "ext": "mkv",
        "badge": "⚡ 1000x Speed (0% Loss)",
        "description": "Direct stream copy of WebM VP9/Opus without re-encoding! Zero quality or color loss.",
        "icon": "copy",
        "default_vcodec": "copy",
        "nvenc_vcodec": "copy",
        "default_acodec": "copy",
        "default_abitrate": "copy",
        "supports_hw": False,
        "supports_remux": True,
    },
    {
        "id": "mov-prores",
        "name": "MOV (Apple ProRes / QuickTime)",
        "ext": "mov",
        "badge": "Editor Master",
        "description": "High-bitrate intra-frame codec ideal for Premiere Pro, DaVinci Resolve, and Final Cut.",
        "icon": "monitor",
        "default_vcodec": "prores_ks",
        "nvenc_vcodec": "h264_nvenc",
        "default_acodec": "pcm_s16le",
        "default_abitrate": None,
        "supports_hw": False,
        "supports_remux": False,
    },
    {
        "id": "mp4-av1",
        "name": "MP4 (AV1 Next-Gen)",
        "ext": "mp4",
        "badge": "Next-Gen Open Standard",
        "description": "State-of-the-art open royalty-free video standard with superior compression.",
        "icon": "cpu",
        "default_vcodec": "libsvtav1",
        "nvenc_vcodec": "av1_nvenc",
        "default_acodec": "aac",
        "default_abitrate": "256k",
        "supports_hw": True,
        "supports_remux": False,
    },
    {
        "id": "webm-vp9",
        "name": "WebM (VP9 / Opus)",
        "ext": "webm",
        "badge": "Web Optimized",
        "description": "Google WebM format optimized for browser playback and HTML5 video.",
        "icon": "globe",
        "default_vcodec": "libvpx-vp9",
        "nvenc_vcodec": None,
        "default_acodec": "libopus",
        "default_abitrate": "160k",
        "supports_hw": False,
        "supports_remux": True,
    },
    {
        "id": "gif-animated",
        "name": "GIF (Animated)",
        "ext": "gif",
        "badge": "Social & Memes",
        "description": "High-framerate animated GIF using two-pass color palette generation.",
        "icon": "image",
        "default_vcodec": "gif",
        "nvenc_vcodec": None,
        "default_acodec": None,
        "default_abitrate": None,
        "supports_hw": False,
        "supports_remux": False,
    },
    {
        "id": "avi-legacy",
        "name": "AVI (Xvid Legacy)",
        "ext": "avi",
        "badge": "Legacy Player",
        "description": "Classic AVI container for vintage multimedia players and hardware.",
        "icon": "archive",
        "default_vcodec": "libxvid",
        "nvenc_vcodec": None,
        "default_acodec": "libmp3lame",
        "default_abitrate": "192k",
        "supports_hw": False,
        "supports_remux": False,
    },
]

# Audio-Only Presets
AUDIO_FORMATS = [
    {
        "id": "mp3",
        "name": "MP3 (MPEG Audio)",
        "ext": "mp3",
        "badge": "Universal Audio",
        "description": "Highest compatibility with any car stereo, phone, speaker, or legacy device.",
        "icon": "music",
        "acodec": "libmp3lame",
        "default_bitrate": "320k",
        "bitrate_options": ["320k", "256k", "192k", "128k"],
        "is_lossless": False,
    },
    {
        "id": "m4a-aac",
        "name": "M4A / AAC (Apple Audio)",
        "ext": "m4a",
        "badge": "High Fidelity",
        "description": "Crystal clear audio encoding preferred on Apple devices, Android, and YouTube.",
        "icon": "disc",
        "acodec": "aac",
        "default_bitrate": "256k",
        "bitrate_options": ["320k", "256k", "192k", "128k"],
        "is_lossless": False,
    },
    {
        "id": "wav",
        "name": "WAV (Studio PCM)",
        "ext": "wav",
        "badge": "Uncompressed Lossless",
        "description": "Pure bit-for-bit uncompressed audio waveform. Zero loss, ideal for sound design.",
        "icon": "activity",
        "acodec": "pcm_s16le",
        "default_bitrate": "lossless",
        "bitrate_options": ["16-bit PCM", "24-bit Studio PCM"],
        "is_lossless": True,
    },
    {
        "id": "flac",
        "name": "FLAC (Lossless Compressed)",
        "ext": "flac",
        "badge": "Audiophile Master",
        "description": "Mathematically lossless compression that reduces file size by 40-50% with zero quality loss.",
        "icon": "award",
        "acodec": "flac",
        "default_bitrate": "lossless",
        "bitrate_options": ["Level 5 (Balanced)", "Level 8 (Maximum Compression)"],
        "is_lossless": True,
    },
    {
        "id": "opus",
        "name": "Opus Audio",
        "ext": "opus",
        "badge": "Modern Voice & Music",
        "description": "State-of-the-art interactive audio codec with unmatched clarity at any bitrate.",
        "icon": "radio",
        "acodec": "libopus",
        "default_bitrate": "192k",
        "bitrate_options": ["256k", "192k", "160k", "128k"],
        "is_lossless": False,
    },
    {
        "id": "ogg",
        "name": "OGG Vorbis",
        "ext": "ogg",
        "badge": "Open Source",
        "description": "High performance open-standard audio container widely used in games and open web.",
        "icon": "volume-2",
        "acodec": "libvorbis",
        "default_bitrate": "192k",
        "bitrate_options": ["320k (Q10)", "256k (Q8)", "192k (Q6)", "128k (Q4)"],
        "is_lossless": False,
    },
]

# Quality Presets
QUALITY_PRESETS = [
    {
        "id": "visually_lossless",
        "name": "Visually Lossless (CRF 17)",
        "crf": 17,
        "nvenc_cq": 18,
        "description": "Indistinguishable from source with pristine color preservation and high compression.",
        "recommended": True,
    },
    {
        "id": "master_studio",
        "name": "Master Quality (CRF 14)",
        "crf": 14,
        "nvenc_cq": 15,
        "description": "Extremely high fidelity for archiving and professional editing masters.",
        "recommended": False,
    },
    {
        "id": "balanced",
        "name": "Balanced (CRF 22)",
        "crf": 22,
        "nvenc_cq": 23,
        "description": "Superb quality with compact file sizes for sharing on Discord, Telegram, or Web.",
        "recommended": False,
    },
    {
        "id": "compact",
        "name": "Compact Size (CRF 28)",
        "crf": 28,
        "nvenc_cq": 29,
        "description": "Highly compressed for email attachments and bandwidth-constrained devices.",
        "recommended": False,
    },
    {
        "id": "exact_lossless",
        "name": "Mathematical Lossless (CRF 0)",
        "crf": 0,
        "nvenc_cq": 0,
        "description": "100% mathematically zero compression artifacts (larger file size).",
        "recommended": False,
    },
]
