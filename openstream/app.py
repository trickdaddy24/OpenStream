"""FastAPI application factory and entry point."""

import logging
import logging.handlers
from contextlib import asynccontextmanager
from pathlib import Path

import bcrypt
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from openstream.config import settings
from openstream.database import init_db, SessionLocal
from openstream.models import User

logger = logging.getLogger("openstream")

BASE_DIR = Path(__file__).parent


def _ensure_dirs():
    """Create runtime data directories."""
    for d in [
        settings.data_dir,
        settings.cache_dir,
        settings.metadata_dir / "posters",
        settings.metadata_dir / "backdrops",
        settings.thumbnail_dir,
        settings.log_dir,
    ]:
        d.mkdir(parents=True, exist_ok=True)


def _ensure_admin():
    """Create a default admin user if none exists."""
    db = SessionLocal()
    try:
        if db.query(User).first() is None:
            hashed = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()
            db.add(User(username="admin", password_hash=hashed, is_admin=True))
            db.commit()
            logger.info("Created default admin user (admin / admin)")
    finally:
        db.close()


async def _startup_update_check():
    """Run update check in background after startup."""
    import asyncio
    await asyncio.sleep(2)  # Let the server finish starting first
    try:
        from openstream.updater import check_for_update
        info = await check_for_update()
        if info.get("update_available"):
            logger.info(
                "Update available: %s -> %s  (%s)",
                info["current_version"], info["remote_version"], info["release_url"],
            )
    except Exception:
        pass  # Never let update check crash the app


def _setup_logging():
    """Configure logging with rotating file handler + console output."""
    log_level = logging.DEBUG if settings.debug else logging.INFO
    log_format = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root openstream logger — all submodules inherit
    root = logging.getLogger("openstream")
    root.setLevel(log_level)

    # Avoid adding duplicate handlers on reload
    if root.handlers:
        return

    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Console handler (stdout)
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # Rotating file handler → data/logs/openstream.log
    log_file = settings.log_dir / "openstream.log"
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as e:
        root.warning("Could not open log file %s: %s", log_file, e)

    # Also capture uvicorn access logs to the same file
    for uv_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(uv_name)
        uv_logger.handlers = []  # remove default handlers
        uv_logger.addHandler(console)
        try:
            uv_logger.addHandler(file_handler)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    import asyncio

    _ensure_dirs()
    _setup_logging()
    logger.info("OpenStream %s starting up", settings.app_version)
    logger.info("Log file: %s", settings.log_dir / "openstream.log")
    init_db()
    _ensure_admin()

    # Background update check (non-blocking, silent on failure)
    asyncio.create_task(_startup_update_check())

    yield
    logger.info("OpenStream shutting down")


app = FastAPI(title="OpenStream", version=settings.app_version, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Static file mounts
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Only mount data dirs if they exist (they're created at startup)
data_metadata = Path(settings.metadata_dir)
data_thumbs = Path(settings.thumbnail_dir)
if data_metadata.exists():
    app.mount("/media-images", StaticFiles(directory=str(data_metadata)), name="media_images")
if data_thumbs.exists():
    app.mount("/thumbnails", StaticFiles(directory=str(data_thumbs)), name="thumbnails")

# Jinja2 templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _basename(value: str) -> str:
    """Jinja2 filter: extract filename from a path."""
    return Path(value).name if value else ""


def _media_url(value: str) -> str:
    """Jinja2 filter: convert a DB path like 'data/metadata/posters/123.jpg' to '/media-images/posters/123.jpg'."""
    if not value:
        return ""
    # Normalise slashes and strip the data/metadata prefix
    clean = str(value).replace("\\", "/")
    prefix = str(settings.metadata_dir).replace("\\", "/")
    if clean.startswith(prefix):
        clean = clean[len(prefix):]
    # Also handle relative 'data/metadata/' prefix
    for p in ("data/metadata/", "data\\metadata\\"):
        if clean.startswith(p):
            clean = clean[len(p):]
    clean = clean.lstrip("/")
    return f"/media-images/{clean}"


templates.env.filters["basename"] = _basename
templates.env.filters["media_url"] = _media_url

# Import and include routers
from openstream.routes import pages, api, stream, auth  # noqa: E402

app.include_router(pages.router)
app.include_router(api.router, prefix="/api")
app.include_router(stream.router, prefix="/stream")
app.include_router(auth.router, prefix="/auth")


def run():
    """Entry point for the `openstream` console script."""
    import uvicorn

    uvicorn.run(
        "openstream.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
