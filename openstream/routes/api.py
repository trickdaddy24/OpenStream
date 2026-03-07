"""REST API endpoints — libraries, items, scan, search, watch history."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from openstream.database import get_db
from openstream.models import Library, MediaItem, MediaFile, WatchHistory
from openstream.routes.auth import get_current_user
from openstream.scanner.tasks import run_library_scan, progress_queues

logger = logging.getLogger("openstream.routes.api")

router = APIRouter(tags=["api"])


# ---------- Pydantic schemas ----------

class LibraryCreate(BaseModel):
    name: str
    path: str
    lib_type: str = "movie"  # "movie" | "tv"


class WatchHistoryUpdate(BaseModel):
    media_item_id: int
    episode_id: int | None = None
    position_secs: int = 0
    completed: bool = False


# ---------- Library endpoints ----------

@router.get("/libraries")
async def list_libraries(db: Session = Depends(get_db)):
    libs = db.query(Library).all()
    return [
        {
            "id": lib.id,
            "name": lib.name,
            "path": lib.path,
            "lib_type": lib.lib_type,
            "scan_status": lib.scan_status,
            "item_count": lib.item_count,
            "last_scanned": str(lib.last_scanned) if lib.last_scanned else None,
        }
        for lib in libs
    ]


@router.post("/libraries", status_code=201)
async def add_library(data: LibraryCreate, db: Session = Depends(get_db)):
    existing = db.query(Library).filter_by(path=data.path).first()
    if existing:
        raise HTTPException(400, "Library path already exists")

    lib = Library(name=data.name, path=data.path, lib_type=data.lib_type)
    db.add(lib)
    db.commit()
    db.refresh(lib)
    return {"id": lib.id, "name": lib.name}


@router.delete("/libraries/{library_id}")
async def delete_library(library_id: int, db: Session = Depends(get_db)):
    lib = db.query(Library).get(library_id)
    if not lib:
        raise HTTPException(404, "Library not found")
    db.delete(lib)
    db.commit()
    return {"ok": True}


# ---------- Scan ----------

@router.post("/libraries/{library_id}/scan", status_code=202)
async def trigger_scan(
    library_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    lib = db.query(Library).get(library_id)
    if not lib:
        raise HTTPException(404, "Library not found")
    if lib.scan_status == "scanning":
        raise HTTPException(409, "Scan already in progress")

    # Run scan in background
    background_tasks.add_task(_run_scan_wrapper, library_id)
    return {"status": "scan_started", "library_id": library_id}


async def _run_scan_wrapper(library_id: int):
    """Wrapper that creates its own DB session for the background task."""
    from openstream.database import SessionLocal
    db = SessionLocal()
    try:
        await run_library_scan(library_id, db)
    finally:
        db.close()


@router.get("/scan-progress/{library_id}")
async def scan_progress(library_id: int):
    """SSE endpoint for live scan progress."""
    queue = progress_queues.get(library_id)

    async def event_stream():
        if not queue:
            yield f"data: {json.dumps({'event': 'no_scan'})}\n\n"
            return
        while True:
            try:
                data = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("event") in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'event': 'heartbeat'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ---------- Items ----------

@router.get("/libraries/{library_id}/items")
async def list_items(
    library_id: int,
    sort: str = "title",
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(MediaItem).filter_by(library_id=library_id)

    if sort == "year":
        q = q.order_by(MediaItem.year.desc())
    elif sort == "rating":
        q = q.order_by(MediaItem.rating.desc())
    elif sort == "added":
        q = q.order_by(MediaItem.added_at.desc())
    else:
        q = q.order_by(MediaItem.sort_title)

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "year": item.year,
                "media_type": item.media_type,
                "rating": item.rating,
                "poster_path": item.poster_path,
                "genres": item.genres,
            }
            for item in items
        ],
    }


@router.get("/items/recent")
async def recent_items(limit: int = 20, db: Session = Depends(get_db)):
    items = (
        db.query(MediaItem)
        .order_by(MediaItem.added_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": item.id,
            "title": item.title,
            "year": item.year,
            "media_type": item.media_type,
            "poster_path": item.poster_path,
        }
        for item in items
    ]


@router.get("/items/search")
async def search_items(q: str, db: Session = Depends(get_db)):
    if len(q) < 2:
        return []
    items = (
        db.query(MediaItem)
        .filter(MediaItem.title.ilike(f"%{q}%"))
        .limit(30)
        .all()
    )
    return [
        {
            "id": item.id,
            "title": item.title,
            "year": item.year,
            "media_type": item.media_type,
            "poster_path": item.poster_path,
        }
        for item in items
    ]


@router.get("/items/{item_id}")
async def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MediaItem).get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    files = db.query(MediaFile).filter_by(media_item_id=item_id).all()
    return {
        "id": item.id,
        "title": item.title,
        "year": item.year,
        "overview": item.overview,
        "tagline": item.tagline,
        "rating": item.rating,
        "runtime_mins": item.runtime_mins,
        "genres": item.genres,
        "poster_path": item.poster_path,
        "backdrop_path": item.backdrop_path,
        "media_type": item.media_type,
        "tmdb_id": item.tmdb_id,
        "files": [
            {
                "id": f.id,
                "file_path": f.file_path,
                "video_codec": f.video_codec,
                "audio_codec": f.audio_codec,
                "resolution": f.resolution,
                "duration_secs": f.duration_secs,
                "file_size": f.file_size,
            }
            for f in files
        ],
    }


# ---------- Watch History ----------

@router.post("/watch-history")
async def update_watch_history(
    data: WatchHistoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(401, "Not authenticated")

    # Upsert watch history
    existing = (
        db.query(WatchHistory)
        .filter_by(
            user_id=user.id,
            media_item_id=data.media_item_id,
            episode_id=data.episode_id,
        )
        .first()
    )
    if existing:
        existing.position_secs = data.position_secs
        existing.completed = data.completed
    else:
        wh = WatchHistory(
            user_id=user.id,
            media_item_id=data.media_item_id,
            episode_id=data.episode_id,
            position_secs=data.position_secs,
            completed=data.completed,
        )
        db.add(wh)
    db.commit()
    return {"ok": True}
