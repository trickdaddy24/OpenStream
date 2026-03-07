"""Probe media files with FFprobe for codec, resolution, and duration info."""

import json
import logging
import subprocess

from openstream.config import settings

logger = logging.getLogger("openstream.transcoder.ffprobe")


def probe_file(file_path: str) -> dict | None:
    """Run ffprobe on a file and return parsed stream info.

    Returns:
        Dict with keys: container, duration_secs, video_codec, audio_codec,
        resolution, bitrate — or None on failure.
    """
    cmd = [
        settings.ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode != 0:
            logger.warning("ffprobe failed for %s: %s", file_path, result.stderr[:200])
            return None

        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning("ffprobe error for %s: %s", file_path, e)
        return None

    fmt = data.get("format", {})
    streams = data.get("streams", [])

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)
    duration = float(fmt.get("duration", 0))
    bitrate = int(fmt.get("bit_rate", 0)) // 1000 if fmt.get("bit_rate") else None

    sub_langs = []
    for s in subtitle_streams:
        lang = s.get("tags", {}).get("language", "und")
        sub_langs.append(lang)

    return {
        "container": fmt.get("format_name", "").split(",")[0],
        "duration_secs": int(duration),
        "video_codec": video_stream.get("codec_name"),
        "video_profile": video_stream.get("profile"),
        "resolution": f"{width}x{height}" if width and height else None,
        "bitrate": bitrate,
        "audio_codec": audio_stream.get("codec_name"),
        "audio_channels": audio_stream.get("channels"),
        "subtitle_langs": sub_langs,
    }


def can_direct_play(probe: dict | None) -> bool:
    """Check if a file can be played directly in most browsers.

    Direct play requires: H.264 video + AAC/MP3 audio in MP4/M4V container.
    """
    if not probe:
        return False

    container_ok = probe.get("container") in ("mov,mp4,m4a,3gp,3g2,mj2", "mp4", "m4v", "mov")
    video_ok = probe.get("video_codec") in ("h264", "avc1")
    audio_ok = probe.get("audio_codec") in ("aac", "mp3")

    return container_ok and video_ok and audio_ok
