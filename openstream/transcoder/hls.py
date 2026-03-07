"""HLS segment generation — builds FFmpeg commands and m3u8 playlists."""

from pathlib import Path

from openstream.config import settings
from openstream.transcoder.profiles import get_profile


def build_ffmpeg_command(
    input_path: str,
    output_dir: str,
    profile_name: str = "720p",
    start_time: int = 0,
) -> list[str]:
    """Build the full FFmpeg command for HLS transcoding.

    Args:
        input_path: Path to the source video file.
        output_dir: Directory for HLS segments and playlist.
        profile_name: Transcoding preset name.
        start_time: Seek position in seconds.

    Returns:
        List of command arguments for subprocess.
    """
    profile = get_profile(profile_name)
    segment_pattern = str(Path(output_dir) / "seg_%04d.ts")
    playlist_path = str(Path(output_dir) / "playlist.m3u8")

    cmd = [
        settings.ffmpeg_path,
        "-hide_banner",
        "-loglevel", "warning",
    ]

    if start_time > 0:
        cmd.extend(["-ss", str(start_time)])

    cmd.extend(["-i", input_path])

    # Map first video and first audio stream
    # The trailing ? on audio makes it optional (no error if audio is missing)
    cmd.extend(["-map", "0:v:0", "-map", "0:a:0?"])

    # Video encoding
    if profile["video_codec"] == "copy":
        cmd.extend(["-c:v", "copy"])
    else:
        cmd.extend([
            "-c:v", profile["video_codec"],
            "-preset", profile.get("preset", "veryfast"),
            "-b:v", profile["video_bitrate"],
            "-maxrate", profile.get("max_rate", profile["video_bitrate"]),
            "-bufsize", profile.get("buf_size", profile["video_bitrate"]),
            "-vf", f"scale={profile['resolution']}:force_original_aspect_ratio=decrease",
        ])

    # Audio encoding
    if profile.get("audio_codec") == "copy":
        cmd.extend(["-c:a", "copy"])
    else:
        cmd.extend([
            "-c:a", profile["audio_codec"],
            "-b:a", profile.get("audio_bitrate", "128k"),
            "-ac", str(profile.get("audio_channels", "2")),
        ])

    # HLS output
    cmd.extend([
        "-f", "hls",
        "-hls_time", str(settings.hls_segment_duration),
        "-hls_init_time", "1",                # Short first segment for fast startup
        "-hls_list_size", "0",
        "-hls_segment_filename", segment_pattern,
        "-hls_flags", "independent_segments+temp_file",  # temp_file = atomic writes
        "-start_number", "0",
        playlist_path,
    ])

    return cmd
