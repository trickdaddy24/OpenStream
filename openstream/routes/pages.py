"""Server-rendered HTML page routes."""

import platform
import sys

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from openstream.config import settings
from openstream.database import get_db
from openstream.models import Library, MediaItem, MediaFile, Season, Episode, User
from openstream.routes.auth import get_current_user
from openstream.updater import get_cached_update_info, detect_install_mode

router = APIRouter(tags=["pages"])


def _templates():
    from openstream.app import templates
    return templates


def _update_context() -> dict:
    """Return update-related template variables."""
    info = get_cached_update_info()
    if info and info.get("update_available"):
        return {
            "update_available": True,
            "update_remote_version": info["remote_version"],
            "update_current_version": info["current_version"],
        }
    return {"update_available": False}


@router.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    """Dashboard — recently added items."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    libraries = db.query(Library).all()
    recent = (
        db.query(MediaItem)
        .order_by(MediaItem.added_at.desc())
        .limit(20)
        .all()
    )
    return _templates().TemplateResponse("home.html", {
        "request": request,
        "user": user,
        "libraries": libraries,
        "recent_items": recent,
        **_update_context(),
    })


@router.get("/login")
async def login_page(request: Request):
    """Login form."""
    return _templates().TemplateResponse("login.html", {
        "request": request,
        "error": None,
    })


@router.get("/library/{library_id}")
async def library_page(
    request: Request,
    library_id: int,
    sort: str = "title",
    db: Session = Depends(get_db),
):
    """Browse items in a library."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    library = db.query(Library).get(library_id)
    if not library:
        return RedirectResponse("/")

    q = db.query(MediaItem).filter_by(library_id=library_id)
    if sort == "year":
        q = q.order_by(MediaItem.year.desc())
    elif sort == "rating":
        q = q.order_by(MediaItem.rating.desc())
    elif sort == "added":
        q = q.order_by(MediaItem.added_at.desc())
    else:
        q = q.order_by(MediaItem.sort_title)

    items = q.all()
    libraries = db.query(Library).all()

    return _templates().TemplateResponse("library.html", {
        "request": request,
        "user": user,
        "library": library,
        "libraries": libraries,
        "items": items,
        "current_sort": sort,
        **_update_context(),
    })


@router.get("/item/{item_id}")
async def detail_page(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
):
    """Movie or show detail page."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    item = db.query(MediaItem).get(item_id)
    if not item:
        return RedirectResponse("/")

    files = db.query(MediaFile).filter_by(media_item_id=item_id).all()
    seasons = db.query(Season).filter_by(show_id=item_id).order_by(Season.season_number).all()
    libraries = db.query(Library).all()

    # Load episodes for each season
    season_episodes = {}
    for s in seasons:
        episodes = (
            db.query(Episode)
            .filter_by(season_id=s.id)
            .order_by(Episode.episode_number)
            .all()
        )
        season_episodes[s.id] = episodes

    return _templates().TemplateResponse("detail.html", {
        "request": request,
        "user": user,
        "item": item,
        "files": files,
        "seasons": seasons,
        "season_episodes": season_episodes,
        "libraries": libraries,
        **_update_context(),
    })


@router.get("/play/{file_id}")
async def player_page(
    request: Request,
    file_id: int,
    db: Session = Depends(get_db),
):
    """Video player page."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    media_file = db.query(MediaFile).get(file_id)
    if not media_file:
        return RedirectResponse("/")

    item = db.query(MediaItem).get(media_file.media_item_id)
    libraries = db.query(Library).all()

    # Check if direct play is possible
    from openstream.transcoder.ffprobe import can_direct_play, probe_file
    probe = probe_file(media_file.file_path)
    direct = can_direct_play(probe)

    return _templates().TemplateResponse("player.html", {
        "request": request,
        "user": user,
        "file": media_file,
        "item": item,
        "direct_play": direct,
        "libraries": libraries,
        **_update_context(),
    })


@router.get("/settings")
async def settings_page(request: Request, db: Session = Depends(get_db)):
    """Settings — manage libraries, users."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    libraries = db.query(Library).all()
    return _templates().TemplateResponse("settings.html", {
        "request": request,
        "user": user,
        "libraries": libraries,
        "current_version": settings.app_version,
        "install_mode": detect_install_mode(),
        **_update_context(),
    })


@router.get("/about")
async def about_page(request: Request, db: Session = Depends(get_db)):
    """About page — version, tech stack, system info."""
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login")

    libraries = db.query(Library).all()
    library_count = len(libraries)
    total_items = db.query(func.count(MediaItem.id)).scalar() or 0
    user_count = db.query(func.count(User.id)).scalar() or 0

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    platform_info = f"{platform.system()} {platform.release()}"

    return _templates().TemplateResponse("about.html", {
        "request": request,
        "user": user,
        "libraries": libraries,
        "version": settings.app_version,
        "install_mode": detect_install_mode(),
        "python_version": python_version,
        "platform_info": platform_info,
        "db_path": str(settings.db_path),
        "library_count": library_count,
        "total_items": total_items,
        "user_count": user_count,
        **_update_context(),
    })
