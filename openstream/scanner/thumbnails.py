"""FFmpeg-based thumbnail extraction from video files."""

import logging
import subprocess
from pathlib import Path

from openstream.config import settings

logger = logging.getLogger("openstream.scanner.thumbnails")


def extract_thumbnail(
    file_path: str, output_path: str, timestamp: str = "00:05:00"
) -> bool:
    """Extract a single thumbnail frame from a video.

    Args:
        file_path: Path to the video file.
        output_path: Where to save the thumbnail (JPEG).
        timestamp: Time offset to capture (HH:MM:SS).

    Returns:
        True on success.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        settings.ffmpeg_path,
        "-ss", timestamp,
        "-i", file_path,
        "-vframes", "1",
        "-q:v", "5",
        "-y",
        output_path,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=30, check=False,
        )
        if result.returncode == 0 and Path(output_path).exists():
            return True
        logger.warning("Thumbnail extraction failed: %s", result.stderr[:200])
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Thumbnail extraction timed out for %s", file_path)
        return False
    except FileNotFoundError:
        logger.error("FFmpeg not found at %s", settings.ffmpeg_path)
        return False
