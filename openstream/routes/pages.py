"""Server-rendered HTML page routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from openstream.database import get_db
from openstream.models import Library, MediaItem, MediaFile, Season, Episode
from openstream.routes.auth import get_current_user

router = APIRouter(tags=["pages"])


def _templates():
    from openstream.app import templates
    return templates


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
    })
