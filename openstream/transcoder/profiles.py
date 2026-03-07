"""Transcoding presets for different quality levels.

All full-transcode presets use 'ultrafast' for real-time transcoding of
heavy sources (HEVC, DTS, 4K) — quality is still fine at the target
bitrate, and encoding stays ahead of playback.

The ``remux`` and ``audio_transcode`` profiles use ``-c:v copy`` so the
video stream is passed through untouched (near-zero CPU).
"""

PROFILES = {
    # ---------- Full transcode (re-encode video + audio) ----------
    "1080p": {
        "video_codec": "libx264",
        "video_bitrate": "4000k",
        "max_rate": "5000k",
        "buf_size": "10000k",
        "resolution": "1920:1080",
        "audio_codec": "aac",
        "audio_bitrate": "192k",
        "audio_channels": "2",
        "preset": "ultrafast",
    },
    "720p": {
        "video_codec": "libx264",
        "video_bitrate": "2500k",
        "max_rate": "3500k",
        "buf_size": "7000k",
        "resolution": "1280:720",
        "audio_codec": "aac",
        "audio_bitrate": "128k",
        "audio_channels": "2",
        "preset": "ultrafast",
    },
    "480p": {
        "video_codec": "libx264",
        "video_bitrate": "1000k",
        "max_rate": "1500k",
        "buf_size": "3000k",
        "resolution": "854:480",
        "audio_codec": "aac",
        "audio_bitrate": "96k",
        "audio_channels": "2",
        "preset": "ultrafast",
    },
    "original": {
        "video_codec": "copy",
        "audio_codec": "aac",
        "audio_bitrate": "192k",
        "audio_channels": "2",
    },

    # ---------- Direct Stream — container remux only (copy both) ----------
    "remux": {
        "video_codec": "copy",
        "audio_codec": "copy",
    },

    # ---------- Audio-only transcode (copy video, encode audio) ----------
    "audio_transcode": {
        "video_codec": "copy",
        "audio_codec": "aac",
        "audio_bitrate": "192k",
        "audio_channels": "2",
    },
}


def get_profile(name: str) -> dict:
    """Get a transcoding profile by name, defaulting to 720p."""
    return PROFILES.get(name, PROFILES["720p"])
