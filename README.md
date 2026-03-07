# OpenStream

A Python media server with web UI, TMDB metadata, and FFmpeg transcoding.

**Current version:** `v0.1.0`

## Features

- Scan local media folders and auto-fetch metadata from TMDB
- Browse your library with poster artwork in a dark-themed web UI
- Direct-play browser-compatible files (H.264/AAC MP4)
- Transcode any format to HLS via FFmpeg for universal playback
- Multi-user support with watch history and resume

## Requirements

- Python 3.11+
- FFmpeg + FFprobe on PATH
- TMDB API key (free at https://www.themoviedb.org/settings/api)

## Quick Start

```bash
# Clone and install
git clone <repo-url> MediaServer
cd MediaServer
pip install -e .

# Configure
cp .env.example .env
# Edit .env — add your TMDB API key

# Run
uvicorn openstream.app:app --reload
# Open http://localhost:8000
```

## Usage

1. Open http://localhost:8000 and log in (default: admin / admin)
2. Go to Settings and add a media library folder
3. Click Scan — metadata and artwork are fetched automatically
4. Browse your library and click Play

## Version History

| Version | Date | Note |
|---------|------|------|
| v0.1.0 | 2026-03-06 | Initial release — media scanning, browsing, direct play, transcoding |
