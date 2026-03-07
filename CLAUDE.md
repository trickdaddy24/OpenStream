# OpenStream — CLAUDE.md

## Project Overview

A Python media server that competes with Plex. Web UI for browsing media libraries with TMDB metadata, poster artwork, and video playback via direct play or FFmpeg HLS transcoding.

**Run with:** `uvicorn openstream.app:app --reload`
**Default login:** admin / admin

---

## Architecture

Multi-module Python package using FastAPI + Jinja2 + SQLite.

### Key Modules

| Module | Purpose |
|---|---|
| `openstream/app.py` | FastAPI factory, lifespan, middleware, static mounts |
| `openstream/config.py` | Settings via pydantic-settings (.env) |
| `openstream/database.py` | SQLite engine, session factory |
| `openstream/models.py` | ORM: Library, MediaItem, MediaFile, Season, Episode, User, WatchHistory, TranscodeSession |
| `openstream/scanner/` | Directory walking, TMDB metadata, FFmpeg thumbnails, background scan |
| `openstream/transcoder/` | FFprobe, HLS generation, transcode profiles, session management |
| `openstream/routes/` | FastAPI routers: pages, api, stream, auth |
| `openstream/templates/` | Jinja2 HTML (dark theme) |
| `openstream/static/` | CSS, JS (Video.js + HLS.js), images |

### Data Files (gitignored)

| Path | Purpose |
|---|---|
| `data/openstream.db` | SQLite database |
| `data/cache/sessions/` | HLS transcode segments (ephemeral) |
| `data/metadata/posters/` | Downloaded TMDB poster images |
| `data/metadata/backdrops/` | Downloaded TMDB backdrop images |
| `data/thumbnails/` | FFmpeg-extracted video thumbnails |

---

## Dependencies

FastAPI, uvicorn, Jinja2, SQLAlchemy, pydantic-settings, httpx, bcrypt, aiofiles, python-multipart, itsdangerous

External: FFmpeg + FFprobe on PATH, TMDB API key in .env

---

## Code Conventions

- Async routes where beneficial (TMDB calls, streaming)
- SQLAlchemy ORM with explicit session management via FastAPI `Depends(get_db)`
- Jinja2 templates extend `base.html`
- CSS custom properties for theming (dark theme default)
- All transcoding via FFmpeg subprocess (not libraries)

**Current version:** `v0.1.7`
