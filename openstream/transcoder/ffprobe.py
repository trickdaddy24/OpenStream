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


# Browser-compatible codec sets
_BROWSER_VIDEO_CODECS = {"h264", "avc1"}
_BROWSER_AUDIO_CODECS = {"aac", "mp3"}
_BROWSER_CONTAINERS = {"mov,mp4,m4a,3gp,3g2,mj2", "mp4", "m4v", "mov"}


def get_playback_decision(probe: dict | None) -> str:
    """Determine the optimal playback strategy for a media file.

    Mimics Plex's playback hierarchy — picks the lightest processing path:

    1. **direct_play** — file is already browser-ready (MP4 + H.264 + AAC/MP3).
       Zero CPU cost; served as a static file with Range/seek support.

    2. **direct_stream** — video AND audio codecs are browser-compatible but the
       container is wrong (e.g. MKV with H.264 + AAC).  FFmpeg remuxes to HLS
       with ``-c:v copy -c:a copy`` — near-zero CPU, no quality loss.

    3. **audio_transcode** — video codec is browser-compatible (H.264) but audio
       is not (DTS, TrueHD, AC3, FLAC, etc.).  FFmpeg copies the video stream
       and only transcodes the audio to AAC — very light CPU usage.

    4. **full_transcode** — video codec requires re-encoding (HEVC, VP9, MPEG-2,
       AV1, etc.).  Full HLS transcode with quality presets.

    Returns:
        One of ``"direct_play"``, ``"direct_stream"``, ``"audio_transcode"``,
        or ``"full_transcode"``.
    """
    if not probe:
        return "full_transcode"

    container = probe.get("container", "")
    video_codec = probe.get("video_codec", "")
    audio_codec = probe.get("audio_codec", "")

    container_ok = container in _BROWSER_CONTAINERS
    video_ok = video_codec in _BROWSER_VIDEO_CODECS
    audio_ok = audio_codec in _BROWSER_AUDIO_CODECS

    if container_ok and video_ok and audio_ok:
        return "direct_play"

    if video_ok and audio_ok:
        # Right codecs, wrong container (e.g. MKV with H.264 + AAC)
        return "direct_stream"

    if video_ok and not audio_ok:
        # Video is fine, audio needs transcoding (DTS, AC3, FLAC, etc.)
        return "audio_transcode"

    # Video needs re-encoding (HEVC, VP9, MPEG-2, etc.)
    return "full_transcode"
