# OpenStream

A self-hosted Python media server that scans local video libraries, fetches metadata and artwork from TMDB, and streams content to any browser — with on-the-fly FFmpeg transcoding when needed.

**Current version:** `v0.1.5`

---

## Overview

OpenStream is a lightweight alternative to Plex and Jellyfin built entirely in Python. It runs as a single FastAPI web application backed by SQLite, with a dark-themed server-rendered UI. Point it at your movie or TV show folders and it will:

- **Scan & identify** media files by parsing filenames and directory structure
- **Fetch metadata** (titles, descriptions, ratings, genres, artwork) from [TMDB](https://www.themoviedb.org/)
- **Serve a web UI** where you browse poster grids, view details, and search
- **Play video** directly in the browser for compatible formats (H.264 + AAC in MP4)
- **Transcode anything else** to HLS on-the-fly via FFmpeg so MKV, HEVC, DTS, etc. all play seamlessly
- **Track watch history** with per-user resume support

No external database server required — everything runs from a single directory.

---

## Features

- **Media Scanner** — recursive folder scanning with smart filename parsing (`Movie (2024).mkv`, `Show.S01E05.mkv`)
- **TMDB Integration** — automatic metadata, poster, and backdrop downloads
- **Direct Play** — zero-overhead streaming for browser-native formats with full seek support
- **HLS Transcoding** — FFmpeg-powered live transcoding with 1080p / 720p / 480p quality presets
- **Dark-Themed UI** — responsive poster grid, detail pages, search, sidebar navigation
- **Multi-User Auth** — session-based login with bcrypt password hashing
- **Watch History** — tracks playback position for resume, marks items as watched
- **TV Show Support** — season/episode organization with per-episode metadata
- **Live Scan Progress** — Server-Sent Events for real-time scan status
- **REST API** — full JSON API for libraries, items, search, and streaming

---

## Project Structure

```
MediaServer/
├── openstream/                      # Main Python package
│   ├── __init__.py                  # Package version
│   ├── app.py                       # FastAPI app factory, lifespan, middleware
│   ├── config.py                    # Settings via pydantic-settings (.env)
│   ├── database.py                  # SQLite engine, session management
│   ├── models.py                    # SQLAlchemy ORM (8 tables)
│   ├── scanner/                     # Media scanning subsystem
│   │   ├── filesystem.py            #   Directory walking, filename parsing
│   │   ├── metadata.py              #   TMDB async API client
│   │   ├── thumbnails.py            #   FFmpeg thumbnail extraction
│   │   └── tasks.py                 #   Background scan orchestrator + SSE
│   ├── transcoder/                  # Transcoding subsystem
│   │   ├── ffprobe.py               #   Media file analysis (codecs, resolution)
│   │   ├── hls.py                   #   HLS command builder, m3u8 generation
│   │   ├── profiles.py              #   Quality presets (1080p/720p/480p)
│   │   └── session.py               #   Transcode session lifecycle manager
│   ├── routes/                      # FastAPI route modules
│   │   ├── api.py                   #   REST API (libraries, items, search, history)
│   │   ├── auth.py                  #   Login / logout (session cookies)
│   │   ├── pages.py                 #   Server-rendered HTML pages
│   │   └── stream.py                #   Direct play + HLS streaming endpoints
│   ├── templates/                   # Jinja2 HTML templates
│   │   ├── base.html                #   Layout shell (nav, sidebar, content)
│   │   ├── home.html                #   Dashboard (recent, library cards)
│   │   ├── library.html             #   Poster grid with sort controls
│   │   ├── detail.html              #   Movie/show detail + play button
│   │   ├── player.html              #   Video.js + HLS.js player
│   │   ├── settings.html            #   Library management + scan controls
│   │   ├── login.html               #   Login form
│   │   ├── scan_progress.html       #   Live scan progress via SSE
│   │   └── partials/                #   Reusable template fragments
│   │       ├── _media_card.html     #     Poster card component
│   │       └── _nav.html            #     Navigation bar
│   └── static/                      # Static assets
│       ├── css/style.css            #   Dark theme stylesheet
│       ├── js/app.js                #   Global JS (search dropdown)
│       ├── js/player.js             #   Video.js + HLS.js init, position tracking
│       ├── js/scan.js               #   SSE scan progress listener
│       └── img/placeholder.svg      #   Default poster placeholder
├── data/                            # Runtime data (gitignored)
│   ├── openstream.db                #   SQLite database
│   ├── cache/sessions/              #   HLS transcode segments (ephemeral)
│   ├── metadata/                    #   Downloaded TMDB images
│   │   ├── posters/                 #     Movie/show poster artwork
│   │   └── backdrops/               #     Backdrop images
│   └── thumbnails/                  #   FFmpeg-extracted video thumbnails
├── pyproject.toml                   # Build config + dependencies
├── Dockerfile                       # Multi-stage Docker build
├── docker-compose.yml               # One-command deployment
├── .env.example                     # Environment variable template
├── .gitignore
├── CLAUDE.md                        # AI assistant project instructions
└── README.md                        # This file
```

---

## Prerequisites

### Windows

1. **Python 3.11+**
   ```powershell
   # Download from https://www.python.org/downloads/
   # Or via winget:
   winget install Python.Python.3.12
   ```

2. **FFmpeg + FFprobe**
   ```powershell
   # Option A: winget
   winget install Gyan.FFmpeg

   # Option B: scoop
   scoop install ffmpeg

   # Option C: Manual — download from https://ffmpeg.org/download.html
   # Extract and add the bin/ folder to your PATH
   ```

3. **Verify**
   ```powershell
   python --version    # Python 3.11+
   ffmpeg -version     # ffmpeg 5+
   ffprobe -version    # should match ffmpeg
   ```

### Ubuntu / Linux

1. **Python 3.11+**
   ```bash
   # Ubuntu 22.04+
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv

   # If you need 3.11+ on older Ubuntu:
   sudo add-apt-repository ppa:deadsnakes/ppa
   sudo apt install -y python3.12 python3.12-venv python3.12-dev
   ```

2. **FFmpeg + FFprobe**
   ```bash
   sudo apt install -y ffmpeg
   ```

3. **Build dependencies** (needed for bcrypt)
   ```bash
   sudo apt install -y build-essential libffi-dev
   ```

4. **Verify**
   ```bash
   python3 --version   # Python 3.11+
   ffmpeg -version      # ffmpeg 5+
   ffprobe -version
   ```

### macOS

1. **Python 3.11+**
   ```bash
   # Homebrew (recommended)
   brew install python@3.12

   # Or download from https://www.python.org/downloads/
   ```

2. **FFmpeg + FFprobe**
   ```bash
   brew install ffmpeg
   ```

3. **Verify**
   ```bash
   python3 --version   # Python 3.11+
   ffmpeg -version      # ffmpeg 5+
   ffprobe -version
   ```

---

## Quick Start

### From Source (all platforms)

```bash
# Clone
git clone https://github.com/trickdaddy24/OpenStream.git
cd OpenStream

# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env — add your TMDB API key (get one free at https://www.themoviedb.org/settings/api)

# Run
uvicorn openstream.app:app --reload
```

Open **http://localhost:8000** and log in with `admin` / `admin`.

### With Docker

```bash
git clone https://github.com/trickdaddy24/OpenStream.git
cd OpenStream

cp .env.example .env
# Edit .env — add your TMDB API key

docker compose up -d
```

Open **http://localhost:8000**. Your media folder is mounted at `/media` inside the container.

---

## Configuration

All settings are controlled via environment variables or a `.env` file in the project root. Every variable uses the `OPENSTREAM_` prefix.

### Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENSTREAM_TMDB_API_KEY` | *(empty)* | **Required.** Your TMDB API key for metadata fetching. Get one free at [themoviedb.org](https://www.themoviedb.org/settings/api). |
| `OPENSTREAM_SECRET_KEY` | `change-me-in-production` | Secret key for signing session cookies. **Change this** in production. |
| `OPENSTREAM_HOST` | `0.0.0.0` | Host to bind the server to. |
| `OPENSTREAM_PORT` | `8000` | Port to listen on. |
| `OPENSTREAM_DEBUG` | `false` | Enable debug mode (verbose SQL logging, auto-reload). |
| `OPENSTREAM_FFMPEG_PATH` | `ffmpeg` | Path to the FFmpeg binary. Set full path if not on `PATH`. |
| `OPENSTREAM_FFPROBE_PATH` | `ffprobe` | Path to the FFprobe binary. Set full path if not on `PATH`. |
| `OPENSTREAM_MAX_TRANSCODE_SESSIONS` | `3` | Maximum concurrent transcode sessions. Raise if your CPU allows. |
| `OPENSTREAM_LOG_MAX_BYTES` | `5242880` | Max size of each log file in bytes (default 5 MB). |
| `OPENSTREAM_LOG_BACKUP_COUNT` | `3` | Number of rotated log file backups to keep. |

### Example `.env`

```env
OPENSTREAM_TMDB_API_KEY=abc123def456
OPENSTREAM_SECRET_KEY=my-super-secret-random-string
OPENSTREAM_HOST=0.0.0.0
OPENSTREAM_PORT=8000
OPENSTREAM_DEBUG=true
OPENSTREAM_FFMPEG_PATH=ffmpeg
OPENSTREAM_FFPROBE_PATH=ffprobe
OPENSTREAM_MAX_TRANSCODE_SESSIONS=3
```

### Data Directory

All runtime data is stored in the `data/` directory (auto-created on first run, gitignored):

| Path | Purpose |
|------|---------|
| `data/openstream.db` | SQLite database (libraries, items, users, history) |
| `data/cache/sessions/` | Temporary HLS transcode segments (cleaned up automatically) |
| `data/metadata/posters/` | Downloaded TMDB poster images |
| `data/metadata/backdrops/` | Downloaded TMDB backdrop images |
| `data/thumbnails/` | FFmpeg-extracted video thumbnails |
| `data/logs/openstream.log` | Application log file (rotating, 5 MB max) |

---

## Docker Setup

### Dockerfile

The included multi-stage `Dockerfile` builds a lean production image (~200 MB) with Python 3.12, FFmpeg, and all dependencies pre-installed.

### docker-compose.yml

The `docker-compose.yml` provides a one-command deployment:

```yaml
# Mount your media folder(s) by editing the volumes section:
volumes:
  - ./data:/app/data           # persistent DB + metadata
  - /path/to/movies:/media     # your media library
```

### Docker Commands

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f openstream

# Stop
docker compose down

# Rebuild after code changes
docker compose up -d --build
```

### Docker Environment Variables

Pass configuration via the `environment` section in `docker-compose.yml` or a mounted `.env` file. The `OPENSTREAM_FFMPEG_PATH` and `OPENSTREAM_FFPROBE_PATH` are pre-set in the Docker image.

---

## Usage

1. **Login** — Open http://localhost:8000. Default credentials: `admin` / `admin`
2. **Add a Library** — Go to **Settings**, enter a name, folder path, and type (Movies or TV Shows), then click **Add**
3. **Scan** — Click **Scan** next to the library. Metadata and artwork are fetched from TMDB automatically. Progress is shown in real-time.
4. **Browse** — Click a library in the sidebar to see a poster grid. Sort by title, year, rating, or date added.
5. **Play** — Click a movie or episode, then click **Play**. Compatible files play directly; others are transcoded via FFmpeg.
6. **Search** — Use the search bar in the navbar to find any title across all libraries.

---

## API Reference

All API endpoints return JSON and are prefixed with `/api`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/libraries` | List all libraries |
| `POST` | `/api/libraries` | Add a library `{name, path, lib_type}` |
| `DELETE` | `/api/libraries/{id}` | Delete a library |
| `POST` | `/api/libraries/{id}/scan` | Trigger a background scan |
| `GET` | `/api/libraries/{id}/items` | List items (paginated, sortable) |
| `GET` | `/api/items/{id}` | Item detail with files |
| `GET` | `/api/items/recent` | Recently added (limit=20) |
| `GET` | `/api/items/search?q=` | Full-text title search |
| `POST` | `/api/watch-history` | Save playback position |
| `GET` | `/api/scan-progress/{id}` | SSE scan progress stream |

### Streaming Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stream/direct/{file_id}` | Direct play with Range support |
| `POST` | `/stream/transcode` | Start HLS transcode `{file_id, profile}` |
| `GET` | `/stream/hls/{session}/playlist.m3u8` | HLS playlist |
| `GET` | `/stream/hls/{session}/{segment}.ts` | HLS segment |
| `POST` | `/stream/stop/{session}` | Stop transcode session |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Templates | Jinja2 (server-rendered) |
| Database | SQLite via SQLAlchemy ORM |
| Metadata | TMDB API via httpx (async) |
| Transcoding | FFmpeg subprocess (HLS output) |
| Player | Video.js + HLS.js |
| Auth | bcrypt + itsdangerous session cookies |
| Styling | Custom CSS (dark theme, CSS Grid) |

---

## Version History

| Version | Date | Note |
|---------|------|------|
| v0.1.5 | 2026-03-07 | Add rotating log file, log viewer in settings, and log API endpoints |
| v0.1.4 | 2026-03-07 | Fix video player — resolve double init, HLS.js integration, and autoplay issues |
| v0.1.3 | 2026-03-07 | Add password complexity validation, strength meter, and change password UI |
| v0.1.2 | 2026-03-07 | Add self-update system with GitHub release checking and auto-update |
| v0.1.1 | 2026-03-07 | Fix double poster path in image URLs and missing Jinja2 split filter |
| v0.1.0 | 2026-03-07 | Initial release — media scanning, browsing, direct play, transcoding |
