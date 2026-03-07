"""Streaming routes — direct play and HLS transcoding."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from openstream.database import get_db
from openstream.models import MediaFile
from openstream.routes.auth import get_current_user
from openstream.transcoder.session import (
    start_session, stop_session, get_session,
    get_playlist_path, get_segment_path,
)

logger = logging.getLogger("openstream.routes.stream")

router = APIRouter(tags=["stream"])

CHUNK_SIZE = 1024 * 1024  # 1 MB


class TranscodeRequest(BaseModel):
    file_id: int
    profile: str = "720p"
    start_time: int = 0


# ---------- Direct Play ----------

@router.get("/direct/{file_id}")
async def direct_play(file_id: int, request: Request, db: Session = Depends(get_db)):
    """Serve a video file directly with Range header support."""
    media_file = db.query(MediaFile).get(file_id)
    if not media_file:
        raise HTTPException(404, "File not found")

    file_path = media_file.file_path
    if not os.path.isfile(file_path):
        raise HTTPException(404, "File not found on disk")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    if range_header:
        # Parse Range: bytes=start-end
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        length = end - start + 1

        def _iter_file():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        content_type = _guess_content_type(file_path)
        return StreamingResponse(
            _iter_file(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Type": content_type,
            },
        )

    # No range — serve full file
    return FileResponse(
        file_path,
        media_type=_guess_content_type(file_path),
        headers={"Accept-Ranges": "bytes"},
    )


# ---------- HLS Transcoding ----------

@router.post("/transcode")
async def start_transcode(
    data: TranscodeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Start a new HLS transcode session."""
    user = get_current_user(request, db)
    session_id = start_session(
        db=db,
        media_file_id=data.file_id,
        profile_name=data.profile,
        start_time=data.start_time,
        user_id=user.id if user else None,
    )
    if not session_id:
        raise HTTPException(503, "Could not start transcode session")
    return {"session_id": session_id}


@router.get("/hls/{session_id}/playlist.m3u8")
async def hls_playlist(session_id: str, db: Session = Depends(get_db)):
    """Serve the HLS playlist for a transcode session."""
    ts = get_session(db, session_id)
    if not ts:
        raise HTTPException(404, "Session not found")

    playlist = get_playlist_path(session_id)

    # Wait briefly for FFmpeg to produce the first playlist
    import asyncio
    for _ in range(20):  # Up to 10 seconds
        if playlist.exists() and playlist.stat().st_size > 0:
            break
        await asyncio.sleep(0.5)

    if not playlist.exists():
        raise HTTPException(503, "Playlist not ready yet")

    return FileResponse(
        str(playlist),
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/hls/{session_id}/{segment}")
async def hls_segment(session_id: str, segment: str, db: Session = Depends(get_db)):
    """Serve an individual HLS segment (.ts file).

    With ``-hls_flags temp_file`` FFmpeg writes to a ``.tmp`` file
    first and atomically renames when the segment is complete, so
    existence == fully written.
    """
    ts = get_session(db, session_id)
    if not ts:
        raise HTTPException(404, "Session not found")

    seg_path = get_segment_path(session_id, segment)

    # Wait for FFmpeg to finish writing the segment.
    import asyncio
    for _ in range(30):  # Up to 15 seconds (covers a full segment encode)
        if seg_path.exists():
            break
        await asyncio.sleep(0.5)

    if not seg_path.exists():
        raise HTTPException(404, "Segment not found")

    return FileResponse(str(seg_path), media_type="video/mp2t")


@router.post("/stop/{session_id}")
async def stop_transcode(session_id: str, db: Session = Depends(get_db)):
    """Stop a transcode session and clean up."""
    stop_session(db, session_id)
    return {"ok": True}


# ---------- Helpers ----------

def _guess_content_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".ts": "video/mp2t",
    }.get(ext, "application/octet-stream")
