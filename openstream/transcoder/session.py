"""Manage active FFmpeg transcode sessions."""

import logging
import shutil
import signal
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from openstream.config import settings
from openstream.models import TranscodeSession, MediaFile
from openstream.transcoder.hls import build_ffmpeg_command

logger = logging.getLogger("openstream.transcoder.session")

# In-memory map of session_id -> subprocess.Popen
_processes: dict[str, subprocess.Popen] = {}


def start_session(
    db: Session,
    media_file_id: int,
    profile_name: str = "720p",
    start_time: int = 0,
    user_id: int | None = None,
) -> str | None:
    """Start a new transcode session.

    Returns:
        Session ID string, or None on failure.
    """
    media_file = db.query(MediaFile).get(media_file_id)
    if not media_file:
        logger.error("MediaFile %d not found", media_file_id)
        return None

    # Check max sessions
    active = db.query(TranscodeSession).filter_by(status="active").count()
    if active >= settings.max_transcode_sessions:
        logger.warning("Max transcode sessions (%d) reached", settings.max_transcode_sessions)
        return None

    session_id = str(uuid.uuid4())
    output_dir = str(settings.cache_dir / session_id)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    cmd = build_ffmpeg_command(
        input_path=media_file.file_path,
        output_dir=output_dir,
        profile_name=profile_name,
        start_time=start_time,
    )

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        logger.error("FFmpeg not found at %s", settings.ffmpeg_path)
        shutil.rmtree(output_dir, ignore_errors=True)
        return None

    _processes[session_id] = proc

    ts = TranscodeSession(
        id=session_id,
        media_file_id=media_file_id,
        user_id=user_id,
        profile=profile_name,
        status="active",
        pid=proc.pid,
        output_dir=output_dir,
    )
    db.add(ts)
    db.commit()

    logger.info("Started transcode session %s (PID %d) for file %d at %s",
                session_id, proc.pid, media_file_id, profile_name)
    return session_id


def stop_session(db: Session, session_id: str):
    """Stop a transcode session — kill FFmpeg and clean up."""
    proc = _processes.pop(session_id, None)
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            proc.kill()

    ts = db.query(TranscodeSession).get(session_id)
    if ts:
        # Clean up segment files
        if ts.output_dir:
            shutil.rmtree(ts.output_dir, ignore_errors=True)
        db.delete(ts)
        db.commit()

    logger.info("Stopped transcode session %s", session_id)


def get_session(db: Session, session_id: str) -> TranscodeSession | None:
    """Look up an active transcode session."""
    return db.query(TranscodeSession).get(session_id)


def get_playlist_path(session_id: str) -> Path:
    """Return path to the HLS playlist for a session."""
    return settings.cache_dir / session_id / "playlist.m3u8"


def get_segment_path(session_id: str, segment_name: str) -> Path:
    """Return path to a specific HLS segment."""
    return settings.cache_dir / session_id / segment_name


def cleanup_stale_sessions(db: Session):
    """Kill orphaned FFmpeg processes and clean up on startup."""
    sessions = db.query(TranscodeSession).all()
    for ts in sessions:
        proc = _processes.pop(ts.id, None)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except (subprocess.TimeoutExpired, OSError):
                proc.kill()
        if ts.output_dir:
            shutil.rmtree(ts.output_dir, ignore_errors=True)
        db.delete(ts)
    db.commit()
    logger.info("Cleaned up %d stale transcode sessions", len(sessions))
